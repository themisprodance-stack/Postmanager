"""Instagram Graph API client ("Instagram API with Instagram Login").

Publishing is a multi-step flow: create media containers from public URLs, wait until Instagram has
processed them, then publish. Progress is kept in Post.publish_state so the steps can be spread over
several short scheduler runs (needed on serverless hosts). Docs:
https://developers.facebook.com/docs/instagram-platform/content-publishing
"""

import json
import logging
import re
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy

from .media import feed_ready_url
from .models import InstagramAccount, InstagramApp, Post

log = logging.getLogger(__name__)

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH = "https://graph.instagram.com"
SCOPES = "instagram_business_basic,instagram_business_content_publish"


class InstagramError(Exception):
    code = None


def _api(path):
    return f"{GRAPH}/{settings.INSTAGRAM_API_VERSION}/{path.lstrip('/')}"


# Plain-language explanations for the errors people actually run into.
NO_PUBLISH_PERMISSION = gettext_lazy(
    "Instagram didn't grant permission to publish. When generating the token, allow all requested permissions.")
FRIENDLY_ERRORS = {
    190: gettext_lazy("The Instagram connection key is invalid or has expired. Generate a new one in the Meta app "
                      "(Instagram → API setup → Generate access tokens) and paste it on the Instagram page."),
    10: NO_PUBLISH_PERMISSION,
    200: NO_PUBLISH_PERMISSION,
    9: gettext_lazy("Instagram's limit of 100 posts per 24 hours was reached. Try again later."),
    4: gettext_lazy("Instagram is rate-limiting requests right now. It will retry automatically."),
}


def _check(resp, friendly=True):
    try:
        data = resp.json()
    except ValueError:
        raise InstagramError(_("Instagram returned an unexpected response (HTTP %(status)s).") % {"status": resp.status_code})
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error") if isinstance(data.get("error"), dict) else {}
        code = err.get("code", data.get("code", resp.status_code))
        message = err.get("error_user_msg") or err.get("message") or data.get("error_message") or resp.text[:300]
        explanation = FRIENDLY_ERRORS.get(code) if friendly else None
        error = InstagramError(
            _("%(explanation)s (Instagram said: %(message)s)") % {"explanation": explanation, "message": message}
            if explanation else f"{message} (code {code})")
        error.code = code
        raise error
    return data


# --- Connecting the account -------------------------------------------------------------------

def redirect_uri():
    return f"{settings.SITE_URL}/instagram/callback/"


def authorize_url(state):
    app_id = InstagramApp.credentials()[0]
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def connect_with_code(code):
    """Exchange an OAuth code for a long-lived token and store the account."""
    app_id, app_secret = InstagramApp.credentials()
    short = _check(requests.post(TOKEN_URL, data={
        "client_id": app_id,
        "client_secret": app_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri(),
        "code": code,
    }, timeout=30))
    long_lived = _check(requests.get(f"{GRAPH}/access_token", params={
        "grant_type": "ig_exchange_token",
        "client_secret": app_secret,
        "access_token": short["access_token"],
    }, timeout=30))
    return connect_with_token(long_lived["access_token"], long_lived.get("expires_in"))


PROFESSIONAL_TYPES = {"BUSINESS", "MEDIA_CREATOR", "CREATOR"}
TOKEN_LIFETIME = timedelta(days=60)


def _profile(token):
    return _check(requests.get(_api("me"), params={
        "fields": "user_id,username,account_type,profile_picture_url", "access_token": token,
    }, timeout=30))


def clean_token(raw):
    """People often paste extra text around the token (quotes, 'Bearer', line breaks)."""
    token = "".join(raw.split()).strip("\"'")
    return token.removeprefix("Bearer").removeprefix("access_token=")


def connect_with_token(token, expires_in=None):
    """Store an account from a token, e.g. one generated in the Meta app dashboard (valid 60 days)."""
    token = clean_token(token)
    if len(token) < 30:
        raise InstagramError(_("That doesn't look like an access token. It's a long code starting with “IG”."))
    me = _profile(token)
    account_type = (me.get("account_type") or "").upper()
    if account_type and account_type not in PROFESSIONAL_TYPES:
        raise InstagramError(_(
            "@%(username)s is a personal account. Instagram only allows apps to post to professional "
            "accounts: in the Instagram app go to Settings → Account type and tools → Switch to professional "
            "account (free), then generate a new token.") % {"username": me.get("username", "")})
    InstagramAccount.objects.exclude(ig_user_id=me["user_id"]).delete()
    account, _created = InstagramAccount.objects.update_or_create(
        ig_user_id=me["user_id"],
        defaults={
            "username": me.get("username", ""),
            "account_type": account_type,
            "profile_picture_url": me.get("profile_picture_url", "")[:1000],
            "access_token": token,
            "token_obtained_at": timezone.now(),
            # Tokens from the Meta dashboard last 60 days. They can only be renewed once they're a day old,
            # so the scheduler renews them later (see refresh_token_if_needed).
            "token_expires_at": timezone.now() + (timedelta(seconds=int(expires_in)) if expires_in else TOKEN_LIFETIME),
        },
    )
    return account


def check_connection(account):
    """Verify the token still works, refresh the profile details and return publishing quota info."""
    me = _profile(account.access_token)
    account.username = me.get("username", account.username)
    account.account_type = (me.get("account_type") or account.account_type).upper()
    account.profile_picture_url = me.get("profile_picture_url", "")[:1000]
    account.save(update_fields=["username", "account_type", "profile_picture_url", "updated_at"])
    info = {"username": account.username, "account_type": account.account_type}
    try:
        quota = _check(requests.get(_api(f"{account.ig_user_id}/content_publishing_limit"), params={
            "fields": "quota_usage,config", "access_token": account.access_token,
        }, timeout=30)).get("data", [{}])[0]
        info["posts_today"] = quota.get("quota_usage")
        info["daily_limit"] = (quota.get("config") or {}).get("quota_total")
    except (InstagramError, IndexError):
        pass
    return info


def refresh_token(account):
    """Long-lived tokens last 60 days; refreshing extends them. Called by the scheduler."""
    data = _check(requests.get(f"{GRAPH}/refresh_access_token", params={
        "grant_type": "ig_refresh_token", "access_token": account.access_token,
    }, timeout=30))
    account.access_token = data["access_token"]
    account.token_obtained_at = timezone.now()
    account.token_expires_at = timezone.now() + timedelta(seconds=int(data.get("expires_in", 60 * 86400)))
    account.save(update_fields=["access_token", "token_obtained_at", "token_expires_at", "updated_at"])
    return account


# --- Publishing ------------------------------------------------------------------------------

READY = "ready"
WAITING = "waiting"


def _create_container(account, **params):
    params["access_token"] = account.access_token
    data = _check(requests.post(_api(f"{account.ig_user_id}/media"), data=params, timeout=60))
    return data["id"]


def _container_status(account, container_id):
    data = _check(requests.get(_api(container_id), params={
        "fields": "status_code,status", "access_token": account.access_token,
    }, timeout=30))
    status = data.get("status_code")
    if status in ("FINISHED", "PUBLISHED"):
        return READY
    if status in ("ERROR", "EXPIRED"):
        raise InstagramError(_("Instagram could not process the media: %(status)s") % {"status": data.get("status", status)})
    return WAITING


def _media_params(asset, *, for_feed):
    if asset.is_video:
        return {"video_url": asset.public_url}
    return {"image_url": feed_ready_url(asset) if for_feed else asset.public_url}


def _user_tags_param(usernames, *, is_video):
    """Instagram wants a position for tags on photos (spread them out); videos and Reels take names only."""
    if not usernames:
        return {}
    if is_video:
        tags = [{"username": name} for name in usernames]
    else:
        n = len(usernames)
        tags = [{"username": name, "x": round((i + 1) / (n + 1), 3), "y": 0.85 if i % 2 else 0.75}
                for i, name in enumerate(usernames)]
    return {"user_tags": json.dumps(tags)}


def _collaborators_param(post):
    """Collab posts appear on the invited accounts' profiles too, once they accept the invitation."""
    return {"collaborators": json.dumps(post.collaborator_usernames)} if post.collaborator_usernames else {}


def validate(post, assets=None):
    """Return a list of problems that would stop this post from publishing."""
    assets = post.ordered_media if assets is None else assets
    problems = []
    if not assets:
        problems.append(_("Add at least one photo or video."))
    elif post.post_type == Post.FEED:
        if len(assets) != 1 or assets[0].is_video:
            problems.append(_("A photo post needs exactly one photo (use Reel for a video, Carousel for several)."))
    elif post.post_type == Post.CAROUSEL:
        if not 2 <= len(assets) <= 10:
            problems.append(_("A carousel needs between 2 and 10 photos/videos."))
    elif post.post_type == Post.REEL:
        if len(assets) != 1 or not assets[0].is_video:
            problems.append(_("A Reel needs exactly one video."))
    elif post.post_type == Post.STORY:
        if len(assets) != 1:
            problems.append(_("A Story needs exactly one photo or video."))
    if len(post.full_caption) > 2200:
        problems.append(_("Instagram captions (including the link) are limited to 2,200 characters."))
    if post.caption.count("#") > 30:
        problems.append(_("Instagram allows at most 30 hashtags."))
    if post.tagged_usernames and post.post_type == Post.STORY:
        problems.append(_("Instagram doesn't allow apps to tag people in Stories. Remove the tags or choose another type."))
    if post.collaborator_usernames and post.post_type == Post.STORY:
        problems.append(_("Stories can't be collab posts. Remove the collaborators or choose another type."))
    return problems


def _create_main_container(account, post, assets, children=None):
    if post.post_type == Post.FEED:
        return _create_container(account, caption=post.full_caption, **_media_params(assets[0], for_feed=True),
                                 **_user_tags_param(post.tagged_usernames, is_video=False), **_collaborators_param(post))
    if post.post_type == Post.REEL:
        return _create_container(
            account, media_type="REELS", caption=post.full_caption, video_url=assets[0].public_url,
            share_to_feed="true" if post.share_reel_to_feed else "false",
            **_user_tags_param(post.tagged_usernames, is_video=True), **_collaborators_param(post),
        )
    if post.post_type == Post.STORY:
        return _create_container(account, media_type="STORIES", **_media_params(assets[0], for_feed=False))
    return _create_container(account, media_type="CAROUSEL", caption=post.full_caption, children=",".join(children),
                             **_collaborators_param(post))


USERS_NOT_ACCESSIBLE = 110


def _drop_inaccessible_tags(post, message, state):
    """Private accounts, wrong usernames and people who don't allow tags can't be tagged. Rather than failing the
    whole post, publish without them and remember who was left out."""
    match = re.search(r"accessed:\s*(.+?)(?:\s*\(code \d+\))?\.?$", message)
    named = {n.strip().lstrip("@").lower() for n in match[1].split(",")} if match else set()
    dropped = [n for n in post.tagged_usernames if n in named] or post.tagged_usernames
    post.user_tags = " ".join(n for n in post.tagged_usernames if n not in dropped)
    Post.objects.filter(pk=post.pk).update(user_tags=post.user_tags)
    state["untagged"] = state.get("untagged", []) + dropped
    log.info("Post %s: publishing without tags for %s", post.pk, dropped)


def _create_first_containers(account, post, assets, state):
    if post.post_type == Post.CAROUSEL:
        children = []
        for i, asset in enumerate(assets):
            params = _media_params(asset, for_feed=True)
            if asset.is_video:
                params["media_type"] = "VIDEO"
            if i == 0:  # Instagram tags people per slide; put them on the first one
                params.update(_user_tags_param(post.tagged_usernames, is_video=asset.is_video))
            children.append(_create_container(account, is_carousel_item="true", **params))
        state["children"] = children
    else:
        state["container"] = _create_main_container(account, post, assets)


def publish_step(post):
    """Move a post one step closer to being published, without waiting.

    Updates post.publish_state in place (the caller saves it). Returns (media_id, permalink) once the post
    is live, or None if Instagram is still processing and this should be called again later.
    Raises InstagramError when publishing can't succeed.
    """
    account = InstagramAccount.current()
    if not account:
        raise InstagramError(_("No Instagram account is connected."))
    state = post.publish_state
    if state.get("media_id"):  # already live; never publish twice
        return state["media_id"], post.permalink
    assets = post.ordered_media

    if not (state.get("container") or state.get("children")):
        problems = validate(post, assets)
        if problems:
            raise InstagramError(" ".join(problems))
        try:
            _create_first_containers(account, post, assets, state)
        except InstagramError as exc:
            if exc.code != USERS_NOT_ACCESSIBLE or not post.tagged_usernames:
                raise
            _drop_inaccessible_tags(post, str(exc), state)
            _create_first_containers(account, post, assets, state)

    if "container" not in state:
        if any(_container_status(account, child) == WAITING for child in state["children"]):
            return None
        state["container"] = _create_main_container(account, post, assets, state["children"])

    if _container_status(account, state["container"]) == WAITING:
        return None

    published = _check(requests.post(_api(f"{account.ig_user_id}/media_publish"), data={
        "creation_id": state["container"], "access_token": account.access_token,
    }, timeout=60))
    media_id = published["id"]
    state["media_id"] = media_id

    permalink = ""
    try:
        permalink = _check(requests.get(_api(media_id), params={
            "fields": "permalink", "access_token": account.access_token,
        }, timeout=30)).get("permalink", "")
    except InstagramError as exc:  # published fine; the link is only a convenience
        log.warning("Could not fetch permalink for %s: %s", media_id, exc)
    return media_id, permalink
