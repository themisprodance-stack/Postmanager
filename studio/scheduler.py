"""Background work: turn recurring rules and the content queue into posts, publish due posts and keep the
Instagram token fresh. Run by `python manage.py run_scheduler`."""

import logging
import time
from datetime import timedelta

from django.db import models
from django.db.models import F
from django.utils import timezone

from . import ai, instagram
from .models import InstagramAccount, Post, QueueSettings, RecurringRule, SchedulerHeartbeat

log = logging.getLogger(__name__)

PUBLISH_TIMEOUT = timedelta(minutes=30)
LOCK_FOR = timedelta(minutes=2)
POLL_SECONDS = 3


def tick(budget_seconds=120):
    """One scheduler pass. Publishing stops starting new steps after `budget_seconds`."""
    SchedulerHeartbeat.beat()
    refresh_token_if_needed()
    run_recurring_rules()
    run_queue()
    summary = publish_due_posts(budget_seconds)
    try:  # results are refreshed a few times a day; never let this break publishing
        from . import stats
        stats.refresh(budget_seconds=10)
    except Exception:
        log.exception("Stats refresh failed")
    return summary


def refresh_token_if_needed():
    account = InstagramAccount.current()
    if account and account.should_refresh:
        try:
            instagram.refresh_token(account)
            log.info("Refreshed Instagram token for %s", account)
        except instagram.InstagramError as exc:
            log.error("Token refresh failed: %s", exc)


def _caption_or_fallback(brief, assets, post_type, fallback):
    try:
        return ai.write_caption(brief, assets, post_type)
    except ai.CaptionError as exc:
        log.warning("AI caption failed, using fallback caption: %s", exc)
        return fallback


def run_recurring_rules():
    now = timezone.now()
    for rule in RecurringRule.objects.filter(active=True, next_run_at__lte=now):
        run_at = rule.next_run_at
        # Claim this run first so a crash can't create duplicates.
        next_run_at, planned_runs = rule.plan_after(max(now, run_at))
        claimed = RecurringRule.objects.filter(pk=rule.pk, next_run_at=run_at).update(
            next_run_at=next_run_at, planned_runs=planned_runs, last_run_at=now,
        )
        if not claimed:
            continue
        if now - run_at > timedelta(hours=6):
            log.warning("Skipping missed run of '%s' at %s", rule, run_at)
            continue
        assets = list(rule.media.order_by("id"))
        caption = rule.render_caption(run_at)
        if rule.use_ai_caption:
            caption = _caption_or_fallback(rule.ai_brief, assets, rule.post_type, caption)
        post = Post.objects.create(
            post_type=rule.post_type, caption=caption, link=rule.link, status=Post.SCHEDULED, scheduled_at=now,
            user_tags="" if rule.post_type == Post.STORY else rule.user_tags,  # Stories can't have tags
            source="recurring", recurring_rule=rule,
        )
        post.set_media(assets)
        log.info("Recurring rule '%s' created post %s", rule, post.pk)


def run_queue():
    queue = QueueSettings.load()
    now = timezone.now()
    if not queue.active or not queue.next_run_at or queue.next_run_at > now:
        return
    run_at = queue.next_run_at
    next_run_at, planned_runs = queue.plan_after(max(now, run_at))
    claimed = QueueSettings.objects.filter(pk=queue.pk, next_run_at=run_at).update(
        next_run_at=next_run_at, planned_runs=planned_runs, last_run_at=now,
    )
    if not claimed or now - run_at > timedelta(hours=6):
        return
    asset = queue.next_asset()
    if not asset:
        log.info("Content queue is empty; nothing to post.")
        return

    if queue.as_story:
        post_type = Post.STORY
    else:
        post_type = Post.REEL if asset.is_video else Post.FEED

    if post_type == Post.STORY:
        caption = ""
    elif queue.caption_mode == QueueSettings.CAPTION_AI:
        caption = _caption_or_fallback(queue.ai_brief, [asset], post_type, asset.caption or queue.default_caption)
    elif asset.caption:
        caption = asset.caption
    elif queue.caption_mode == QueueSettings.CAPTION_ASSET:
        caption = _caption_or_fallback(queue.ai_brief, [asset], post_type, queue.default_caption)
    else:
        caption = queue.default_caption

    post = Post.objects.create(
        post_type=post_type, caption=caption, link="" if post_type == Post.STORY else queue.link,
        user_tags="" if post_type == Post.STORY else queue.user_tags,
        status=Post.SCHEDULED, scheduled_at=now, source="queue",
    )
    post.set_media([asset])
    asset.__class__.objects.filter(pk=asset.pk).update(times_used=F("times_used") + 1, last_used_at=now)
    log.info("Queue created post %s from asset %s", post.pk, asset.pk)


def publish_due_posts(budget_seconds=120):
    """Start due posts and continue ones Instagram is still processing. Returns a small summary."""
    deadline = time.monotonic() + budget_seconds
    now = timezone.now()
    summary = {"published": 0, "failed": 0, "waiting": 0}

    timed_out = Post.objects.filter(status=Post.PUBLISHING, publish_started_at__lt=now - PUBLISH_TIMEOUT)
    summary["failed"] += timed_out.update(
        status=Post.FAILED, error="Instagram took too long to process this post. Check Instagram before retrying.",
    )
    Post.objects.filter(status=Post.SCHEDULED, scheduled_at__lte=now).update(
        status=Post.PUBLISHING, publish_started_at=now, publish_state={}, locked_until=None,
    )

    worked = False
    for post in Post.objects.filter(status=Post.PUBLISHING).order_by("publish_started_at", "pk"):
        if worked and time.monotonic() > deadline:
            break  # the rest continue in the next run
        # Lock the post so overlapping scheduler runs never work on it at the same time.
        lock_now = timezone.now()
        locked = Post.objects.filter(pk=post.pk, status=Post.PUBLISHING).filter(
            models.Q(locked_until__isnull=True) | models.Q(locked_until__lt=lock_now),
        ).update(locked_until=lock_now + LOCK_FOR)
        if not locked:
            continue
        post.refresh_from_db()
        worked = True
        outcome = _advance(post, deadline)
        summary[outcome] += 1
    return summary


def _advance(post, deadline):
    while True:
        try:
            result = instagram.publish_step(post)
        except Exception as exc:  # any failure must leave the post in a visible state
            log.exception("Publishing post %s failed", post.pk)
            Post.objects.filter(pk=post.pk).update(
                status=Post.FAILED, error=str(exc)[:2000], publish_state=post.publish_state, locked_until=None,
            )
            return "failed"
        if result:
            media_id, permalink = result
            Post.objects.filter(pk=post.pk).update(
                status=Post.PUBLISHED, published_at=timezone.now(), ig_media_id=media_id, permalink=permalink,
                error="", publish_state=post.publish_state, locked_until=None,
            )
            log.info("Published post %s as %s", post.pk, media_id)
            return "published"
        Post.objects.filter(pk=post.pk).update(publish_state=post.publish_state)
        if time.monotonic() + POLL_SECONDS > deadline:
            Post.objects.filter(pk=post.pk).update(locked_until=None)
            return "waiting"
        time.sleep(POLL_SECONDS)
