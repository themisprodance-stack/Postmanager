"""Post results and best posting times, from Instagram's insights (needs the instagram_business_manage_insights
permission on the connection key). Refreshed by the scheduler a few times a day and by the Stats page."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

import requests
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy

from .instagram import InstagramError, _api, _check
from .models import InstagramAccount, MediaStat, StatsState

log = logging.getLogger(__name__)

REFRESH_EVERY = timedelta(hours=6)
MEDIA_FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count,thumbnail_url,media_url"
INSIGHT_METRICS = ["reach", "saved", "shares", "views"]
MIN_POSTS_FOR_ADVICE = 5

PERMISSION_HELP = gettext_lazy(
    "Postmanager doesn't have permission to read your post results yet. In your Meta app open Instagram → "
    "Permissions and features, add “instagram_business_manage_insights”, then generate a new access token and "
    "paste it on the Instagram page."
)


class StatsUnavailable(Exception):
    pass


def _get(path, account, **params):
    params["access_token"] = account.access_token
    try:
        return _check(requests.get(_api(path), params=params, timeout=30), friendly=False)
    except InstagramError as exc:
        if exc.code in (10, 200, 3) or "permission" in str(exc).lower():
            raise StatsUnavailable(str(PERMISSION_HELP)) from exc
        raise


def refresh(budget_seconds=25, force=False):
    """Fetch the account's recent posts and their results. Returns the StatsState."""
    state = StatsState.load()
    account = InstagramAccount.current()
    if not account:
        return state
    if not force and state.refreshed_at and timezone.now() - state.refreshed_at < REFRESH_EVERY:
        return state
    deadline = time.monotonic() + budget_seconds
    state.refreshed_at = timezone.now()  # also throttles retries after an error
    try:
        _refresh_media(account, deadline)
        _refresh_account(account, state)
        state.error = ""
    except StatsUnavailable as exc:
        state.error = str(exc)
    except InstagramError as exc:
        log.warning("Stats refresh failed: %s", exc)
        state.error = _("Instagram didn't return results right now: %(error)s") % {"error": exc}
    state.save()
    return state


def _refresh_media(account, deadline):
    data = _get(f"{account.ig_user_id}/media", account, fields=MEDIA_FIELDS, limit=50)
    for item in data.get("data", []):
        MediaStat.objects.update_or_create(ig_media_id=item["id"], defaults={
            "media_type": item.get("media_type", ""),
            "product_type": item.get("media_product_type", ""),
            "posted_at": datetime.fromisoformat(item["timestamp"].replace("+0000", "+00:00")),
            "permalink": item.get("permalink", ""),
            "thumbnail_url": (item.get("thumbnail_url") or item.get("media_url") or "")[:1000],
            "caption": (item.get("caption") or "")[:200],
            "likes": item.get("like_count") or 0,
            "comments": item.get("comments_count") or 0,
        })
    # Then per-post insights, stalest first, within the time budget.
    stale = MediaStat.objects.filter(posted_at__gte=timezone.now() - timedelta(days=120)).order_by(
        "insights_fetched_at", "-posted_at")
    for stat in stale:
        if time.monotonic() > deadline:
            break
        if stat.insights_fetched_at and timezone.now() - stat.insights_fetched_at < REFRESH_EVERY:
            continue
        _refresh_insights(account, stat)


def _refresh_insights(account, stat):
    values = {}
    try:
        data = _get(f"{stat.ig_media_id}/insights", account, metric=",".join(INSIGHT_METRICS))
    except InstagramError:
        # Some post types (e.g. carousels, very old posts) don't support every metric: try the basics.
        try:
            data = _get(f"{stat.ig_media_id}/insights", account, metric="reach,saved")
        except InstagramError:
            data = {"data": []}
    for metric in data.get("data", []):
        value = (metric.get("total_value") or {}).get("value")
        if value is None and metric.get("values"):
            value = metric["values"][0].get("value")
        if isinstance(value, int):
            values[metric.get("name")] = value
    stat.reach = values.get("reach", stat.reach)
    stat.saves = values.get("saved", stat.saves)
    stat.shares = values.get("shares", stat.shares)
    stat.views = values.get("views", stat.views)
    stat.insights_fetched_at = timezone.now()
    stat.save()


def _refresh_account(account, state):
    me = _get("me", account, fields="followers_count")
    state.followers = me.get("followers_count", state.followers)
    # Followers online per hour: only for accounts with 100+ followers, and not always provided.
    try:
        data = _get(f"{account.ig_user_id}/insights", account, metric="online_followers", period="lifetime")
    except (InstagramError, StatsUnavailable):
        return
    totals = [0] * 24
    found = False
    for metric in data.get("data", []):
        for entry in metric.get("values", []):
            by_hour = entry.get("value")
            if isinstance(by_hour, dict):
                for hour, count in by_hour.items():
                    if str(hour).isdigit() and isinstance(count, int):
                        totals[int(hour) % 24] += count
                        found = True
    if found:
        # Instagram reports these hours in Pacific time; shift them to the studio's time zone.
        offset = _hours_from_pacific()
        state.online_by_hour = [totals[(h - offset) % 24] for h in range(24)]


def _hours_from_pacific():
    from zoneinfo import ZoneInfo
    now = timezone.now()
    local = timezone.localtime(now).utcoffset()
    pacific = now.astimezone(ZoneInfo("America/Los_Angeles")).utcoffset()
    return round((local - pacific).total_seconds() / 3600)


# --- Analysis -------------------------------------------------------------------------------------

def summary():
    stats = list(MediaStat.objects.all()[:200])
    with_reach = [s for s in stats if s.reach]
    use_rate = len(with_reach) >= max(3, len(stats) * 0.6)
    scored = [(s, s.engagement_rate if use_rate else s.interactions) for s in (with_reach if use_rate else stats)]

    hours = defaultdict(list)
    days = defaultdict(list)
    for stat, score in scored:
        local = timezone.localtime(stat.posted_at)
        hours[local.hour].append(score)
        days[local.weekday()].append(score)

    def bars(groups, keys):
        rows = []
        for key in keys:
            values = groups.get(key, [])
            rows.append({"key": key, "value": round(sum(values) / len(values), 1) if values else None,
                         "count": len(values)})
        top = max((r["value"] for r in rows if r["value"] is not None), default=0) or 1
        for r in rows:
            r["pct"] = round(100 * r["value"] / top) if r["value"] is not None else 0
        return rows

    state = StatsState.load()
    online = state.online_by_hour if len(state.online_by_hour) == 24 and any(state.online_by_hour) else []
    online_rows = []
    if online:
        top = max(online) or 1
        online_rows = [{"key": h, "value": v, "pct": round(100 * v / top), "count": None} for h, v in enumerate(online)]

    total = len(stats)
    return {
        "posts": total,
        "metric": "rate" if use_rate else "interactions",
        "avg_reach": round(sum(s.reach for s in with_reach) / len(with_reach)) if with_reach else None,
        "avg_rate": round(sum(s.engagement_rate for s in with_reach) / len(with_reach), 1) if with_reach else None,
        "hour_rows": bars(hours, range(24)),
        "day_rows": bars(days, range(7)),
        "online_rows": online_rows,
        "best_window": best_window(hours, online),
        "enough_data": len(scored) >= MIN_POSTS_FOR_ADVICE or bool(online),
        "top_posts": sorted(stats, key=lambda s: (s.engagement_rate or 0, s.interactions), reverse=True)[:10],
        "state": state,
    }


def best_window(hours, online, width=3):
    """The best `width`-hour window between 08:00 and 23:00: by followers online if known, else by results."""
    candidates = range(8, 24 - width + 1)
    if online:
        start = max(candidates, key=lambda h: sum(online[h:h + width]))
        return {"start": start, "end": start + width, "basis": "followers"}
    averages = {h: sum(v) / len(v) for h, v in hours.items() if v}
    if sum(len(v) for v in hours.values()) < MIN_POSTS_FOR_ADVICE or not averages:
        return None

    def window_score(h):
        vals = [averages[x] for x in range(h, h + width) if x in averages]
        return sum(vals) / len(vals) if vals else -1

    start = max(candidates, key=window_score)
    if window_score(start) < 0:
        return None
    return {"start": start, "end": start + width, "basis": "posts"}
