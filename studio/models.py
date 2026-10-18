import random
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

WEEKDAY_CHOICES = [
    ("0", _("Mon")), ("1", _("Tue")), ("2", _("Wed")), ("3", _("Thu")), ("4", _("Fri")), ("5", _("Sat")), ("6", _("Sun")),
]


def next_occurrence(weekdays, times, after=None):
    """Next local datetime after `after` that falls on one of `weekdays` (0=Mon) at one of `times`."""
    if not weekdays or not times:
        return None
    after = after or timezone.now()
    local_after = timezone.localtime(after)
    for day_offset in range(0, 8):
        day = local_after.date() + timedelta(days=day_offset)
        if day.weekday() not in weekdays:
            continue
        for t in sorted(times):
            candidate = timezone.make_aware(datetime.combine(day, t))
            if candidate > after:
                return candidate
    return None


def parse_weekdays(value):
    return sorted({int(d) for d in str(value).split(",") if d.strip().isdigit() and 0 <= int(d) <= 6})


def parse_times(value):
    result = []
    for part in str(value).replace(" ", "").split(","):
        if not part:
            continue
        hour, _sep, minute = part.partition(":")
        result.append(time(int(hour), int(minute or 0)))
    return result


def clean_link(link):
    """Instagram turns anything after '#' into a hashtag, so a link's #section part would break it."""
    return (link or "").strip().split("#", 1)[0].strip()


def with_link(caption, link):
    link = clean_link(link)
    if not link:
        return caption
    shown = link.removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
    return f"{caption.rstrip()}\n\n🔗 {shown}" if caption.strip() else f"🔗 {shown}"


def absolute_url(url):
    """File URLs are absolute with cloud storage and site-relative with local storage."""
    return url if url.startswith(("http://", "https://")) else f"{settings.SITE_URL}{url}"


def media_upload_path(instance, filename):
    ext = Path(filename).suffix.lower() or ".bin"
    return f"library/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class InstagramAccount(models.Model):
    """The studio's connected Instagram professional account (only one is used)."""

    ig_user_id = models.CharField(max_length=64)
    username = models.CharField(max_length=150, blank=True)
    account_type = models.CharField(max_length=30, blank=True)
    profile_picture_url = models.URLField(max_length=1000, blank=True)
    access_token = models.TextField()
    token_obtained_at = models.DateTimeField(default=timezone.now)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"@{self.username or self.ig_user_id}"

    @classmethod
    def current(cls):
        return cls.objects.order_by("-updated_at").first()

    @property
    def token_expires_soon(self):
        return bool(self.token_expires_at and self.token_expires_at - timezone.now() < timedelta(days=7))

    @property
    def should_refresh(self):
        """Renew well before expiry; Instagram only renews tokens that are at least a day old."""
        old_enough = timezone.now() - self.token_obtained_at > timedelta(days=1)
        due = not self.token_expires_at or self.token_expires_at - timezone.now() < timedelta(days=30)
        return old_enough and due


class InstagramApp(models.Model):
    """The Meta app's Instagram App ID and secret, entered on the Instagram page (only needed for the
    "Log in with Instagram" button; pasting a token works without them). Falls back to the environment."""

    app_id = models.CharField(max_length=64, blank=True)
    app_secret = models.CharField(max_length=128, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def credentials(cls):
        obj = cls.objects.filter(pk=1).first()
        if obj and obj.app_id and obj.app_secret:
            return obj.app_id, obj.app_secret
        return settings.INSTAGRAM_APP_ID, settings.INSTAGRAM_APP_SECRET


class MediaAsset(models.Model):
    IMAGE = "image"
    VIDEO = "video"
    KIND_CHOICES = [(IMAGE, _("Photo")), (VIDEO, _("Video"))]

    file = models.FileField(upload_to=media_upload_path)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True, help_text=_("Optional caption used when this item is posted from the queue."))
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    in_queue = models.BooleanField(default=False, help_text=_("Include in the automatic content queue."))
    times_used = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or Path(self.file.name).name

    @property
    def is_video(self):
        return self.kind == self.VIDEO

    @property
    def public_url(self):
        return absolute_url(self.file.url)

    @property
    def aspect_ratio(self):
        if self.width and self.height:
            return self.width / self.height
        return None


def music_upload_path(instance, filename):
    ext = Path(filename).suffix.lower() or ".mp3"
    return f"music/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class MusicTrack(models.Model):
    """A song or sound uploaded by the studio, used to turn photos and videos into videos with music."""

    file = models.FileField(upload_to=music_upload_path)
    title = models.CharField(max_length=200, blank=True)
    duration = models.FloatField(null=True, blank=True)  # seconds
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title", "-created_at"]

    def __str__(self):
        return self.title or Path(self.file.name).name

    @property
    def duration_display(self):
        if not self.duration:
            return ""
        seconds = int(round(self.duration))
        return f"{seconds // 60}:{seconds % 60:02d}"


class Post(models.Model):
    FEED = "feed"
    CAROUSEL = "carousel"
    REEL = "reel"
    STORY = "story"
    TYPE_CHOICES = [(FEED, _("Photo post")), (CAROUSEL, _("Carousel")), (REEL, _("Reel")), (STORY, _("Story"))]

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    STATUS_CHOICES = [
        (DRAFT, _("Draft")), (SCHEDULED, _("Scheduled")), (PUBLISHING, _("Publishing")),
        (PUBLISHED, _("Published")), (FAILED, _("Failed")),
    ]

    SOURCE_CHOICES = [("manual", _("Manual")), ("recurring", _("Recurring")), ("queue", _("Queue"))]

    post_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=FEED)
    caption = models.TextField(blank=True)
    link = models.CharField(
        max_length=300, blank=True,
        help_text=_("Added to the end of the caption as text (Instagram never makes caption links clickable)."),
    )
    share_reel_to_feed = models.BooleanField(default=True, help_text=_("Reels only: also show in the main grid."))
    user_tags = models.CharField(max_length=700, blank=True)  # Instagram usernames to tag, space separated
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    ig_media_id = models.CharField(max_length=64, blank=True)
    permalink = models.URLField(blank=True)
    error = models.TextField(blank=True)
    # Progress while publishing (Instagram container ids), so publishing can continue across scheduler runs.
    publish_state = models.JSONField(default=dict, blank=True)
    publish_started_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    recurring_rule = models.ForeignKey("RecurringRule", null=True, blank=True, on_delete=models.SET_NULL)
    media = models.ManyToManyField(MediaAsset, through="PostItem", related_name="posts")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at", "-created_at"]

    def __str__(self):
        first_line = (self.caption or "").strip().splitlines()[0][:50] if self.caption.strip() else ""
        return f"{self.get_post_type_display()}: {first_line or _('(no caption)')}"

    @property
    def ordered_media(self):
        return [item.asset for item in self.items.select_related("asset").order_by("position")]

    @property
    def full_caption(self):
        """The caption as it appears on Instagram, with the link appended."""
        return with_link(self.caption, self.link)

    @property
    def tagged_usernames(self):
        return self.user_tags.split()

    @property
    def is_editable(self):
        return self.status in (self.DRAFT, self.SCHEDULED, self.FAILED)

    def set_media(self, assets):
        self.items.all().delete()
        PostItem.objects.bulk_create(PostItem(post=self, asset=a, position=i) for i, a in enumerate(assets))


class PostItem(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="items")
    asset = models.ForeignKey(MediaAsset, on_delete=models.PROTECT)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]


class RecurringRule(models.Model):
    """Publishes the same kind of post on a weekly pattern, e.g. the class timetable every Monday 09:00."""

    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    post_type = models.CharField(max_length=10, choices=Post.TYPE_CHOICES, default=Post.FEED)
    caption = models.TextField(
        blank=True,
        help_text=_("Placeholders: {date}, {weekday}, {studio}. Ignored when an AI caption is generated."),
    )
    use_ai_caption = models.BooleanField(default=False, help_text=_("Write a fresh caption with AI each time."))
    ai_brief = models.TextField(blank=True, help_text=_("What the AI caption should be about."))
    link = models.CharField(max_length=300, blank=True, help_text=_("Optional link added to the end of the caption."))
    user_tags = models.CharField(max_length=700, blank=True, verbose_name=_("Tag people"))  # usernames, space separated
    media = models.ManyToManyField(MediaAsset, blank=True, related_name="recurring_rules")
    weekdays = models.CharField(max_length=20, default="0", help_text=_("Comma separated, 0=Mon … 6=Sun"))
    times = models.CharField(max_length=100, default="09:00", help_text=_("Comma separated HH:MM, e.g. 09:00,18:30"))
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["next_run_at"]

    def __str__(self):
        return self.name

    def compute_next_run(self, after=None):
        return next_occurrence(parse_weekdays(self.weekdays), parse_times(self.times), after)

    def weekday_labels(self):
        labels = dict(WEEKDAY_CHOICES)
        return ", ".join(str(labels[str(d)]) for d in parse_weekdays(self.weekdays))

    def render_caption(self, when):
        local = timezone.localtime(when)
        return self.caption.format_map(_SafeDict(
            date=local.strftime("%d %B"), weekday=local.strftime("%A"), studio=settings.STUDIO_NAME,
        ))


class QueueSettings(models.Model):
    """Automatic content queue: publishes the next library item marked 'in queue' on a schedule."""

    CAPTION_ASSET = "asset"
    CAPTION_AI = "ai"
    CAPTION_DEFAULT = "default"
    CAPTION_CHOICES = [
        (CAPTION_ASSET, _("Item's own caption, otherwise AI")),
        (CAPTION_AI, _("Always AI")),
        (CAPTION_DEFAULT, _("Item's own caption, otherwise the default caption")),
    ]

    SOURCE_QUEUE = "queue"
    SOURCE_LIBRARY = "library"
    SOURCE_CHOICES = [
        (SOURCE_QUEUE, _("Only items I marked “In queue”")),
        (SOURCE_LIBRARY, _("Anything in the library")),
    ]

    TIMING_FIXED = "fixed"
    TIMING_RANDOM = "random"
    TIMING_CHOICES = [(TIMING_FIXED, _("At fixed times")), (TIMING_RANDOM, _("🎲 At random times, different every day"))]

    active = models.BooleanField(default=False)
    weekdays = models.CharField(max_length=20, default="1,3,5")
    timing_mode = models.CharField(max_length=10, choices=TIMING_CHOICES, default=TIMING_FIXED, verbose_name=_("When"))
    times = models.CharField(max_length=100, default="18:00", blank=True)
    window_start = models.TimeField(default=time(10, 0), verbose_name=_("First post not before"))
    window_end = models.TimeField(default=time(21, 0), verbose_name=_("Last post not after"))
    posts_per_day = models.PositiveSmallIntegerField(default=2, verbose_name=_("Posts per day"))
    # Random mode: the remaining planned times for the current day (ISO strings), first = next_run_at.
    planned_runs = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_QUEUE, verbose_name=_("Post from"))
    random_order = models.BooleanField(default=False, help_text=_("Pick items at random instead of oldest first."))
    link = models.CharField(max_length=300, blank=True, help_text=_("Optional link added to the end of every queue caption."))
    user_tags = models.CharField(max_length=700, blank=True, verbose_name=_("Tag people"))  # usernames, space separated
    as_story = models.BooleanField(default=False, help_text=_("Post queue items as Stories instead of feed posts/Reels."))
    caption_mode = models.CharField(max_length=10, choices=CAPTION_CHOICES, default=CAPTION_ASSET)
    default_caption = models.TextField(blank=True)
    ai_brief = models.TextField(
        blank=True, default="A moment from our dance classes. Invite people to try a class.",
    )
    reuse_items = models.BooleanField(
        default=False, help_text=_("When every item has been posted, start again from the least used."),
    )
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "queue settings"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def compute_next_run(self, after=None):
        return next_occurrence(parse_weekdays(self.weekdays), parse_times(self.times), after)

    def weekday_labels(self):
        labels = dict(WEEKDAY_CHOICES)
        return ", ".join(str(labels[str(d)]) for d in parse_weekdays(self.weekdays))

    def schedule_label(self):
        if self.timing_mode == self.TIMING_RANDOM:
            return _("%(count)s× a day at random times between %(start)s and %(end)s") % {
                "count": self.posts_per_day, "start": f"{self.window_start:%H:%M}", "end": f"{self.window_end:%H:%M}"}
        return self.times

    def planned_times(self):
        return [datetime.fromisoformat(t) for t in self.planned_runs]

    def plan_after(self, after=None):
        """Work out the next run (and, in random mode, the rest of that day's random times).

        Returns (next_run_at, planned_runs) without saving, so callers can store both atomically.
        """
        after = after or timezone.now()
        if self.timing_mode != self.TIMING_RANDOM:
            return self.compute_next_run(after), []
        planned = self.planned_times()
        remaining = [t for t in planned if t > after]
        if not remaining:
            previous = {timezone.localtime(t).strftime("%H:%M") for t in planned}
            if planned:  # today's posts are done: plan from the following day
                next_day = timezone.localtime(max(planned)).date() + timedelta(days=1)
                after = max(after, timezone.make_aware(datetime.combine(next_day, time.min)))
            remaining = self._random_day(after, avoid=previous)
        return (remaining[0] if remaining else None), [t.isoformat() for t in remaining]

    def _random_day(self, after, avoid=()):
        """Random times on the next posting day, one in each equal slice of the window so they're spread out."""
        weekdays = parse_weekdays(self.weekdays)
        local_after = timezone.localtime(after)
        for offset in range(0, 8):
            day = local_after.date() + timedelta(days=offset)
            if day.weekday() not in weekdays:
                continue
            start = timezone.make_aware(datetime.combine(day, self.window_start))
            end = timezone.make_aware(datetime.combine(day, self.window_end))
            start = max(start, after + timedelta(minutes=2))
            minutes = int((end - start).total_seconds() // 60)
            if minutes < 1:
                continue
            count = max(1, min(self.posts_per_day, minutes))
            slot = minutes / count
            times = []
            for i in range(count):
                for _attempt in range(10):  # re-roll if it matches one of the previous day's times
                    t = start + timedelta(minutes=int(slot * i + random.random() * slot))
                    if timezone.localtime(t).strftime("%H:%M") not in avoid:
                        break
                times.append(t.replace(second=0, microsecond=0))
            return sorted(set(times))
        return []

    def candidates(self):
        """Items that can be posted next (least-used first when items may be reused)."""
        items = MediaAsset.objects.all() if self.source == self.SOURCE_LIBRARY else MediaAsset.objects.filter(in_queue=True)
        if not self.reuse_items:
            return items.filter(times_used=0)
        least = items.aggregate(models.Min("times_used"))["times_used__min"]
        return items.filter(times_used=least) if least is not None else items.none()

    def next_asset(self):
        items = self.candidates()
        if self.random_order:
            return items.order_by("?").first()
        return items.order_by("times_used", "last_used_at", "created_at").first()

    def upcoming(self, limit=50):
        """What the queue will post, for display. With random order this is just the pool."""
        items = MediaAsset.objects.all() if self.source == self.SOURCE_LIBRARY else MediaAsset.objects.filter(in_queue=True)
        if not self.reuse_items:
            items = items.filter(times_used=0)
        return items.order_by("times_used", "last_used_at", "created_at")[:limit]


class LinkPage(models.Model):
    """The public "link in bio" page: buttons plus the latest posts that have a link."""

    headline = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=300, blank=True)
    buttons = models.JSONField(default=list, blank=True)  # [{"label": ..., "url": ...}]
    show_posts = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            obj.headline = settings.STUDIO_NAME
            obj.save()
        return obj


def full_url(link):
    link = clean_link(link)
    if not link:
        return ""
    return link if link.startswith(("http://", "https://")) else f"https://{link}"


class MediaStat(models.Model):
    """Results of one Instagram post (any post on the account, not only ones made here)."""

    ig_media_id = models.CharField(max_length=64, unique=True)
    media_type = models.CharField(max_length=30, blank=True)
    product_type = models.CharField(max_length=30, blank=True)
    posted_at = models.DateTimeField(db_index=True)
    permalink = models.URLField(blank=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    saves = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)
    reach = models.PositiveIntegerField(null=True, blank=True)
    views = models.PositiveIntegerField(null=True, blank=True)
    insights_fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-posted_at"]

    @property
    def interactions(self):
        return self.likes + self.comments + (self.saves or 0) + (self.shares or 0)

    @property
    def engagement_rate(self):
        """Interactions per person reached, in percent (None when reach is unknown)."""
        return round(100 * self.interactions / self.reach, 1) if self.reach else None


class StatsState(models.Model):
    """Account-level stats and refresh bookkeeping."""

    followers = models.PositiveIntegerField(null=True, blank=True)
    online_by_hour = models.JSONField(default=list, blank=True)  # 24 numbers, local time, or []
    refreshed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class SchedulerHeartbeat(models.Model):
    """When the scheduler last ran, so the app can warn if automatic publishing has stopped."""

    last_run_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def beat(cls):
        cls.objects.update_or_create(pk=1, defaults={"last_run_at": timezone.now()})

    @classmethod
    def last_run(cls):
        obj = cls.objects.filter(pk=1).first()
        return obj.last_run_at if obj else None


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class Membership(models.Model):
    """Who may use the app. New sign-ups wait (approved=False) until an owner lets them in."""

    OWNER = "owner"
    EDITOR = "editor"
    ROLE_CHOICES = [(OWNER, _("Owner")), (EDITOR, _("Editor"))]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=EDITOR)
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-approved", "role", "user__email"]

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.approved and self.role == self.OWNER

    @classmethod
    def for_user(cls, user):
        """The user's membership, created on first access. Superusers are always approved owners."""
        membership, created = cls.objects.get_or_create(user=user)
        if user.is_superuser and not membership.is_owner:
            membership.role, membership.approved = cls.OWNER, True
            membership.approved_at = membership.approved_at or timezone.now()
            membership.save()
        return membership
