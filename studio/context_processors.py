from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from . import ai
from .models import InstagramAccount, Membership, Post, SchedulerHeartbeat


def studio(request):
    membership = getattr(request, "membership", None)
    common = {"static_version": settings.STATIC_VERSION, "js_i18n": js_i18n()}
    if not request.user.is_authenticated or not membership or not membership.approved:
        return {**common, "studio_name": settings.STUDIO_NAME, "membership": membership}
    return {
        **common,
        "direct_upload": bool(settings.BLOB_READ_WRITE_TOKEN),
        # On Vercel there's no disk: uploads need Blob storage connected.
        "uploads_unavailable": settings.SERVERLESS and not settings.BLOB_READ_WRITE_TOKEN,
        "membership": membership,
        "is_owner": membership.is_owner,
        "scheduler_stopped": _scheduler_stopped(),
        "waiting_count": Membership.objects.filter(approved=False, user__is_active=True).count()
        if membership.is_owner else 0,
        "studio_name": settings.STUDIO_NAME,
        "ig_account": InstagramAccount.current(),
        "ai_enabled": ai.enabled(),
        "failed_count": Post.objects.filter(status=Post.FAILED).count(),
    }


def _scheduler_stopped():
    """True when nothing has run the scheduler for a while, so scheduled posts would sit and wait."""
    last = SchedulerHeartbeat.last_run()
    return not last or timezone.now() - last > timedelta(minutes=20)


def js_i18n():
    """Texts used by the page scripts (app.js, direct-upload.js), in the current language."""
    return {
        "selected": _("%(n)s selected"),
        "none_selected": _("None selected"),
        "hint_feed": _("One photo. Photos that are too tall or wide get soft blurred borders automatically."),
        "hint_carousel": _("2–10 photos/videos. Click them in the order you want them to appear."),
        "hint_reel": _("One vertical video (MP4/MOV, 9:16 works best, 3 sec – 15 min)."),
        "hint_story": _("One photo or video. Stories have no caption and disappear after 24h."),
        "counter": _("%(chars)s / 2200 characters · %(tags)s / 30 hashtags"),
        "confirm_publish": _("Publish this to Instagram now?"),
        "writing": _("Writing…"),
        "went_wrong": _("Something went wrong."),
        "use_caption": _("Use this caption"),
        "copied": _("Copied ✓"),
        "copy_this": _("Copy this:"),
        "video": _("Video"),
        "uploading": _("Uploading %(i)s of %(n)s: %(name)s"),
        "uploaded": _("Uploaded %(n)s file(s)."),
        "upload_failed": _("Upload failed (%(status)s)."),
        "storage_refused": _("Storage refused the upload (%(status)s)."),
        "network_error": _("Network error while uploading."),
    }
