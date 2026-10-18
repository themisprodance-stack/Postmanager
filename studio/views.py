import base64
import hmac
import json
import logging
import secrets
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import ai, instagram, scheduler
from .forms import (
    InstagramAppForm, LinkPageForm, MediaAssetForm, MusicUploadForm, MusicVideoForm, PostForm, StoryTextForm, QueueSettingsForm, RecurringRuleForm, TokenForm, UploadForm,
)
from .media import (
    UnsupportedFile, delete_asset_files, plan_direct_upload, register_direct_upload, register_music_upload,
    save_music_upload, save_upload,
)
from .models import (
    InstagramAccount, InstagramApp, LinkPage, MediaAsset, Membership, MusicTrack, Post, QueueSettings, RecurringRule,
    SchedulerHeartbeat, full_url,
)
from .story import save_story, story_jpeg
from .video import VideoError, make_music_video


def _when(dt):
    """A date in the studio's time zone, formatted for the current language (e.g. “Τρι 13 Οκτ, 18:30”)."""
    return date_format(timezone.localtime(dt), "D j M, H:i")


log = logging.getLogger(__name__)

LINK_TRIMMED = gettext_lazy("The part of the link after “#” was removed, because Instagram turns it into a hashtag.")


def owner_required(view):
    """Only owners may change automations, the Instagram connection and the team."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.membership.is_owner:
            messages.error(request, _("Only an owner can do that."))
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return wrapper


@login_required
def dashboard(request):
    now = timezone.now()
    upcoming = Post.objects.filter(status__in=[Post.SCHEDULED, Post.PUBLISHING]).order_by("scheduled_at")[:10]
    recent = Post.objects.filter(status=Post.PUBLISHED).order_by("-published_at")[:6]
    failed = Post.objects.filter(status=Post.FAILED).order_by("-updated_at")[:5]
    rules = RecurringRule.objects.filter(active=True).order_by("next_run_at")[:5]
    queue = QueueSettings.load()
    return render(request, "studio/dashboard.html", {
        "upcoming": upcoming,
        "recent": recent,
        "failed": failed,
        "rules": rules,
        "queue": queue,
        "queue_remaining": queue.candidates().count(),
        "published_this_week": Post.objects.filter(status=Post.PUBLISHED, published_at__gte=now - timedelta(days=7)).count(),
        "drafts": Post.objects.filter(status=Post.DRAFT).count(),
    })


# --- Posts -------------------------------------------------------------------------------------

@login_required
def post_list(request):
    status = request.GET.get("status", "")
    posts = Post.objects.prefetch_related("items__asset")
    if status in dict(Post.STATUS_CHOICES):
        posts = posts.filter(status=status)
    return render(request, "studio/post_list.html", {
        "posts": posts[:200], "status": status, "statuses": Post.STATUS_CHOICES,
    })


def _post_form_context(form, post=None):
    return {
        "form": form,
        "post": post,
        "library": MediaAsset.objects.all()[:300],
    }


@login_required
def post_edit(request, pk=None):
    post = get_object_or_404(Post, pk=pk) if pk else None
    if post and not post.is_editable:
        messages.info(request, _("This post is already published and can't be edited."))
        return redirect("post_list")
    initial = {"media_ids": request.GET["media"]} if not post and request.GET.get("media") else None
    if initial and request.GET.get("type") in dict(Post.TYPE_CHOICES):
        initial["post_type"] = request.GET["type"]
    form = PostForm(request.POST or None, request.FILES or None, instance=post, initial=initial)
    if request.method == "POST" and request.FILES and _uploads_unavailable(request):
        return redirect(request.path)
    if request.method == "POST" and form.is_valid():
        assets = list(form.cleaned_data["media_ids"])
        try:
            for upload in form.cleaned_data["new_files"]:
                assets.append(save_upload(upload, request.user))
        except UnsupportedFile as exc:
            form.add_error("new_files", str(exc))
            return render(request, "studio/post_form.html", _post_form_context(form, post))

        obj = form.save(commit=False)
        problems = instagram.validate(obj, assets)
        action = form.cleaned_data["action"]
        if problems and action != "draft":
            for problem in problems:
                form.add_error(None, problem)
            # Keep newly uploaded files selected so they don't need uploading again.
            form.data = form.data.copy()
            form.data["media_ids"] = ",".join(str(a.pk) for a in assets)
            return render(request, "studio/post_form.html", _post_form_context(form, post))

        if action == "draft":
            obj.status = Post.DRAFT
        elif action == "now":
            obj.status, obj.scheduled_at = Post.SCHEDULED, timezone.now()
        else:
            obj.status = Post.SCHEDULED
        obj.error = ""
        if not obj.created_by_id:
            obj.created_by = request.user
        with transaction.atomic():
            obj.save()
            obj.set_media(assets)

        if form.link_was_trimmed:
            messages.info(request, LINK_TRIMMED)
        if action == "now":
            _publish_now_message(request, obj)
        elif action == "schedule":
            messages.success(request, _("Scheduled for %(when)s.") % {"when": _when(obj.scheduled_at)})
            from .context_processors import _scheduler_stopped
            if _scheduler_stopped():
                messages.warning(request, _(
                    "Heads-up: automatic publishing isn't running right now, so this post won't go out on time. "
                    "An owner needs to set up the timer (see the banner)."))
        else:
            messages.success(request, _("Draft saved."))
        return redirect("post_list")
    return render(request, "studio/post_form.html", _post_form_context(form, post))


def _publish_now_message(request, post):
    if not settings.SERVERLESS:
        messages.success(request, _("Publishing now. It will appear on Instagram within a minute or two."))
        return
    # Serverless: no background process, so start publishing right away within this request.
    scheduler.publish_due_posts(budget_seconds=20)
    post.refresh_from_db()
    if post.status == Post.PUBLISHED:
        messages.success(request, _("Published to Instagram! 🎉"))
    elif post.status == Post.FAILED:
        messages.error(request, _("Publishing failed: %(error)s") % {"error": post.error})
    else:
        messages.info(request, _("Instagram is still processing this post. It will go live within a few minutes."))


@login_required
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.status == Post.PUBLISHING:
        messages.error(request, _("This post is publishing right now; try again in a minute."))
    else:
        post.delete()
        messages.success(request, _("Post removed from Postmanager. It is still on Instagram.")
                         if post.status == Post.PUBLISHED else _("Post removed from Postmanager."))
    return redirect(request.POST.get("next") or "post_list")


@login_required
@require_POST
def post_retry(request, pk):
    updated = Post.objects.filter(pk=pk, status=Post.FAILED).update(
        status=Post.SCHEDULED, scheduled_at=timezone.now(), error="",
    )
    if updated:
        _publish_now_message(request, Post.objects.get(pk=pk))
    return redirect(request.POST.get("next") or "post_list")


@login_required
@require_POST
def post_duplicate(request, pk):
    original = get_object_or_404(Post, pk=pk)
    copy = Post.objects.create(
        post_type=original.post_type, caption=original.caption, link=original.link,
        share_reel_to_feed=original.share_reel_to_feed, user_tags=original.user_tags,
        collaborators=original.collaborators,
        created_by=request.user,
    )
    copy.set_media(original.ordered_media)
    messages.success(request, _("Copied as a new draft."))
    return redirect("post_edit", pk=copy.pk)


# --- Media library -----------------------------------------------------------------------------

def _uploads_unavailable(request):
    if settings.SERVERLESS and not settings.BLOB_READ_WRITE_TOKEN:
        messages.error(request, _("Uploads aren't possible yet: connect Blob storage to the Vercel project, then redeploy."))
        return True
    return False


@login_required
def media_list(request):
    if request.method == "POST" and _uploads_unavailable(request):
        return redirect("media_list")
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        saved, errors = 0, []
        for upload in form.cleaned_data["files"]:
            try:
                asset = save_upload(upload, request.user)
            except UnsupportedFile as exc:
                errors.append(str(exc))
                continue
            if form.cleaned_data["add_to_queue"]:
                asset.in_queue = True
                asset.save(update_fields=["in_queue"])
            saved += 1
        if saved:
            messages.success(request, _("Uploaded %(count)s file(s).") % {"count": saved})
        for error in errors:
            messages.error(request, error)
        return redirect("media_list")
    show = request.GET.get("show", "")
    assets = MediaAsset.objects.all()
    if show == "queue":
        assets = assets.filter(in_queue=True)
    elif show in (MediaAsset.IMAGE, MediaAsset.VIDEO):
        assets = assets.filter(kind=show)
    return render(request, "studio/media_list.html", {"form": form, "assets": assets, "show": show})


@login_required
@require_POST
def media_upload_token(request):
    """Step 1 of a direct browser upload: a short-lived permission to upload one file to cloud storage."""
    if not settings.BLOB_READ_WRITE_TOKEN:
        return JsonResponse({"error": _("Direct uploads are not enabled.")}, status=400)
    from .storage import client_upload_token

    try:
        data = json.loads(request.body)
        pathname, types, max_bytes = plan_direct_upload(
            str(data.get("name", "")), str(data.get("type", "")), int(data.get("size", 0)),
        )
    except UnsupportedFile as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": _("Bad request.")}, status=400)
    token = client_upload_token(pathname, allowed_content_types=types, maximum_size_in_bytes=max_bytes)
    return JsonResponse({"pathname": pathname, "token": token})


@login_required
@require_POST
def media_upload_complete(request):
    """Step 2 of a direct browser upload: turn the uploaded file into a library item."""
    try:
        data = json.loads(request.body)
        asset = register_direct_upload(str(data["pathname"]), str(data.get("name", "upload")), request.user)
    except UnsupportedFile as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": _("Bad request.")}, status=400)
    if data.get("in_queue"):
        asset.in_queue = True
        asset.save(update_fields=["in_queue"])
    return JsonResponse({
        "id": asset.pk, "url": asset.file.url, "is_video": asset.is_video, "title": str(asset),
    })


@login_required
def media_edit(request, pk):
    asset = get_object_or_404(MediaAsset, pk=pk)
    form = MediaAssetForm(request.POST or None, instance=asset)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saved."))
        return redirect("media_list")
    return render(request, "studio/media_form.html", {"form": form, "asset": asset})


@login_required
@require_POST
def media_toggle_queue(request, pk):
    asset = get_object_or_404(MediaAsset, pk=pk)
    asset.in_queue = not asset.in_queue
    asset.save(update_fields=["in_queue"])
    return redirect(request.POST.get("next") or "media_list")


@login_required
@require_POST
def media_delete(request, pk):
    asset = get_object_or_404(MediaAsset, pk=pk)
    try:
        with transaction.atomic():
            asset.delete()
    except ProtectedError:
        messages.error(request, _("This file is used by a post. Delete the post first."))
        return redirect("media_edit", pk=pk)
    delete_asset_files(asset)
    messages.success(request, _("File deleted."))
    return redirect("media_list")


# --- Music library and videos with music ------------------------------------------------------

@login_required
def music_list(request):
    if request.method == "POST" and _uploads_unavailable(request):
        return redirect("music_list")
    form = MusicUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        saved = 0
        for upload in form.cleaned_data["files"]:
            try:
                save_music_upload(upload, request.user)
                saved += 1
            except UnsupportedFile as exc:
                messages.error(request, str(exc))
        if saved:
            messages.success(request, _("Uploaded %(count)s file(s).") % {"count": saved})
        return redirect("music_list")
    return render(request, "studio/music_list.html", {"form": form, "tracks": MusicTrack.objects.all()})


@login_required
@require_POST
def music_upload_complete(request):
    """Step 2 of a direct browser upload of a music file (step 1 is media_upload_token)."""
    try:
        data = json.loads(request.body)
        track = register_music_upload(str(data["pathname"]), str(data.get("name", "music")), request.user)
    except UnsupportedFile as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"error": _("Bad request.")}, status=400)
    return JsonResponse({"id": track.pk, "title": str(track)})


@login_required
@require_POST
def music_rename(request, pk):
    track = get_object_or_404(MusicTrack, pk=pk)
    title = request.POST.get("title", "").strip()[:200]
    if title:
        track.title = title
        track.save(update_fields=["title"])
    return redirect("music_list")


@login_required
@require_POST
def music_delete(request, pk):
    track = get_object_or_404(MusicTrack, pk=pk)
    track.file.delete(save=False)
    track.delete()
    messages.success(request, _("File deleted."))
    return redirect("music_list")


@login_required
def music_video(request):
    initial = {"asset": request.GET.get("asset")} if request.GET.get("asset") else None
    form = MusicVideoForm(request.POST or None, initial=initial)
    if request.method == "POST" and not _uploads_unavailable(request) and form.is_valid():
        data = form.cleaned_data
        try:
            video = make_music_video(data["asset"], data["track"], start=data["start"], length=data["length"],
                                     keep_original_sound=data["keep_original_sound"], user=request.user)
        except (VideoError, UnsupportedFile) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, _("Your video with music is ready and saved in the Library."))
            return redirect(f"{reverse('post_new')}?media={video.pk}&type=story")
    return render(request, "studio/music_video.html", {
        "form": form,
        "library": MediaAsset.objects.all()[:300],
        "tracks": MusicTrack.objects.all(),
    })


# --- Story images with text -------------------------------------------------------------------

@login_required
def story_text(request):
    initial = {"asset": request.GET.get("asset")} if request.GET.get("asset") else None
    form = StoryTextForm(request.POST or None, initial=initial)
    if request.method == "POST" and request.POST.get("preview"):
        # Sent as text (a data: URL) rather than raw image bytes, so nothing between here and the browser can
        # mangle it; errors come back as a message the page shows under the preview.
        if not form.is_valid():
            return JsonResponse({"error": " ".join(e for errors in form.errors.values() for e in errors)}, status=400)
        try:
            jpeg = story_jpeg(form.cleaned_data["asset"], preview_width=540, **form.story_options())
        except Exception as exc:  # shown to the user instead of a blank preview
            log.exception("Story preview failed")
            return JsonResponse({"error": _("The preview couldn't be made: %(error)s") % {"error": exc}}, status=500)
        return JsonResponse({"image": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()})
    if request.method == "POST" and not _uploads_unavailable(request) and form.is_valid():
        options = form.story_options()
        if not (options["headline"].strip() or options["text"].strip()):
            form.add_error("headline", _("Write some text for the story."))
        else:
            story = save_story(form.cleaned_data["asset"], request.user, **options)
            messages.success(request, _(
                "Story image saved in the Library. To add music, use the 🎵 button on it in the Library."))
            return redirect(f"{reverse('post_new')}?media={story.pk}&type=story")
    return render(request, "studio/story_text.html", {
        "form": form,
        "photos": MediaAsset.objects.filter(kind=MediaAsset.IMAGE)[:300],
    })


# --- Recurring rules and queue ----------------------------------------------------------------

@login_required
def recurring_list(request):
    return render(request, "studio/recurring_list.html", {"rules": RecurringRule.objects.all()})


@owner_required
def recurring_edit(request, pk=None):
    rule = get_object_or_404(RecurringRule, pk=pk) if pk else None
    form = RecurringRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        assets = list(form.cleaned_data["media"])
        probe = Post(post_type=form.cleaned_data["post_type"], caption=form.cleaned_data["caption"])
        problems = instagram.validate(probe, assets)
        if problems:
            for problem in problems:
                form.add_error(None, problem)
        else:
            saved = form.save()
            if form.link_was_trimmed:
                messages.info(request, LINK_TRIMMED)
            when = _when(saved.next_run_at) if saved.next_run_at else _("never")
            messages.success(request, _("Saved. Next post: %(when)s.") % {"when": when})
            return redirect("recurring_list")
    selected = {str(v) for v in (form["media"].value() or [])}
    return render(request, "studio/recurring_form.html", {
        "form": form, "rule": rule, "library": MediaAsset.objects.all()[:300], "selected": selected,
    })


@owner_required
@require_POST
def recurring_delete(request, pk):
    get_object_or_404(RecurringRule, pk=pk).delete()
    messages.success(request, _("Recurring post deleted."))
    return redirect("recurring_list")


@login_required
def queue_settings(request):
    queue = QueueSettings.load()
    if request.method == "POST" and not request.membership.is_owner:
        messages.error(request, _("Only an owner can change the queue settings."))
        return redirect("queue")
    form = QueueSettingsForm(request.POST or None, instance=queue)
    if request.method == "POST" and form.is_valid():
        queue = form.save()
        if form.link_was_trimmed:
            messages.info(request, LINK_TRIMMED)
        if not queue.active:
            messages.info(request, _("Saved. The queue is off. Tick “Queue is on” to start posting."))
        elif not queue.next_run_at:
            messages.warning(request, _("Saved, but no posting time could be planned. Check the days and times."))
        else:
            messages.success(request, _("✅ Queue is on. Next post: %(when)s.") % {"when": _when(queue.next_run_at)})
            if not queue.candidates().exists():
                messages.warning(request, _(
                    "There's nothing to post yet. Upload photos or choose “Anything in the library”."))
        return redirect("queue")
    return render(request, "studio/queue.html", {"form": form, "queue": queue, "items": queue.upcoming()})


# --- AI captions -------------------------------------------------------------------------------

@login_required
@require_POST
def caption_suggestions(request):
    ids = [int(i) for i in request.POST.get("media_ids", "").split(",") if i.strip().isdigit()]
    found = MediaAsset.objects.in_bulk(ids)
    assets = [found[i] for i in ids if i in found]
    brief = request.POST.get("brief", "")
    if not brief.strip() and not assets:
        return JsonResponse({"error": _("Describe the post or select some media first.")}, status=400)
    try:
        captions = ai.suggest_captions(brief, assets, request.POST.get("post_type", "feed"))
    except ai.CaptionError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse({"captions": captions})


# --- Instagram connection ----------------------------------------------------------------------

@owner_required
def instagram_settings(request):
    app = InstagramApp.objects.filter(pk=1).first()
    token_form = TokenForm(request.POST if request.POST.get("step") == "token" else None)
    app_form = InstagramAppForm(
        request.POST if request.POST.get("step") == "app" else None,
        initial={"app_id": app.app_id if app else ""},
    )
    account = InstagramAccount.current()

    if request.method == "POST":
        step = request.POST.get("step")
        if step == "token" and token_form.is_valid():
            try:
                account = instagram.connect_with_token(token_form.cleaned_data["access_token"])
            except instagram.InstagramError as exc:
                messages.error(request, _("Couldn't connect: %(error)s") % {"error": exc})
            else:
                messages.success(request, _("🎉 Connected to Instagram as %(account)s.") % {"account": account})
                return redirect("instagram")
        elif step == "app" and app_form.is_valid():
            app = app or InstagramApp(pk=1)
            app.app_id = app_form.cleaned_data["app_id"].strip()
            if app_form.cleaned_data["app_secret"]:
                app.app_secret = app_form.cleaned_data["app_secret"].strip()
            if not app.app_secret:
                app_form.add_error("app_secret", _("Enter the app secret."))
            else:
                app.save()
                messages.success(request, _("Saved. You can now use “Log in with Instagram”."))
                return redirect("instagram")
        elif step == "check" and account:
            try:
                info = instagram.check_connection(account)
            except instagram.InstagramError as exc:
                messages.error(request, _("The connection isn't working: %(error)s") % {"error": exc})
            else:
                messages.success(request, _("✅ Connection works: posting as @%(username)s.") % info)
                if info.get("daily_limit"):
                    messages.info(request, _("%(used)s of %(limit)s daily posts used.") % {
                        "used": info.get("posts_today", 0), "limit": info["daily_limit"]})
            return redirect("instagram")

    app_id, app_secret = InstagramApp.credentials()
    return render(request, "studio/instagram.html", {
        "account": account,
        "token_form": token_form,
        "app_form": app_form,
        "oauth_ready": bool(app_id and app_secret),
        "redirect_uri": instagram.redirect_uri(),
        "site_url": settings.SITE_URL,
        "site_is_public": settings.SITE_URL.startswith("https://"),
        "show_setup": not account or request.GET.get("reconnect") or token_form.errors or app_form.errors,
    })


@owner_required
def instagram_connect(request):
    state = secrets.token_urlsafe(24)
    request.session["ig_oauth_state"] = state
    return redirect(instagram.authorize_url(state))


@owner_required
def instagram_callback(request):
    if request.GET.get("error"):
        messages.error(request, _("Instagram connection cancelled: %(reason)s") % {
            "reason": request.GET.get("error_description", "")})
        return redirect("instagram")
    if request.GET.get("state") != request.session.pop("ig_oauth_state", None):
        messages.error(request, _("The connection request expired. Please try again."))
        return redirect("instagram")
    try:
        account = instagram.connect_with_code(request.GET.get("code", "").removesuffix("#_"))
    except instagram.InstagramError as exc:
        messages.error(request, _("Couldn't connect: %(error)s") % {"error": exc})
    else:
        messages.success(request, _("🎉 Connected to Instagram as %(account)s.") % {"account": account})
    return redirect("instagram")


@owner_required
@require_POST
def instagram_disconnect(request):
    InstagramAccount.objects.all().delete()
    messages.success(request, _("Instagram disconnected. Scheduled posts will fail until you reconnect."))
    return redirect("instagram")


# --- Team & approval ---------------------------------------------------------------------------

def pending(request):
    if not request.user.is_authenticated:
        return redirect("account_login")
    if request.membership.approved:
        return redirect("dashboard")
    return render(request, "studio/pending.html")


@owner_required
def scheduler_setup(request):
    from .context_processors import _scheduler_stopped
    return render(request, "studio/scheduler_setup.html", {
        "tick_url": f"{settings.SITE_URL}/cron/tick/?key={settings.CRON_SECRET}" if settings.CRON_SECRET else "",
        "last_run": SchedulerHeartbeat.last_run(),
        "stopped": _scheduler_stopped(),
        "serverless": settings.SERVERLESS,
    })


@owner_required
def team(request):
    members = Membership.objects.select_related("user", "approved_by").filter(user__is_active=True)
    return render(request, "studio/team.html", {
        "waiting": members.filter(approved=False).order_by("created_at"),
        "members": members.filter(approved=True),
    })


def _owners_left_without(membership):
    return Membership.objects.filter(role=Membership.OWNER, approved=True, user__is_active=True).exclude(
        pk=membership.pk).count()


@owner_required
@require_POST
def team_update(request, pk):
    membership = get_object_or_404(Membership.objects.select_related("user"), pk=pk)
    action = request.POST.get("action")
    who = membership.user.get_full_name() or membership.user.email or membership.user.get_username()
    if membership.user == request.user and action != "approve":
        messages.error(request, _("You can't change your own access. Ask another owner."))
        return redirect("team")
    if action == "approve":
        membership.approved, membership.approved_at, membership.approved_by = True, timezone.now(), request.user
        membership.role = Membership.OWNER if request.POST.get("role") == Membership.OWNER else Membership.EDITOR
        membership.save()
        messages.success(request, _("%(who)s can now use the app as %(role)s.") % {
            "who": who, "role": membership.get_role_display().lower()})
    elif action == "role":
        role = request.POST.get("role")
        if role not in dict(Membership.ROLE_CHOICES):
            return redirect("team")
        if role != Membership.OWNER and membership.role == Membership.OWNER and not _owners_left_without(membership):
            messages.error(request, _("There must always be at least one owner."))
            return redirect("team")
        membership.role = role
        membership.save(update_fields=["role"])
        messages.success(request, _("%(who)s is now %(role)s.") % {"who": who, "role": membership.get_role_display().lower()})
    elif action in ("decline", "remove"):
        if membership.is_owner and not _owners_left_without(membership):
            messages.error(request, _("There must always be at least one owner."))
            return redirect("team")
        # Deactivate instead of deleting so their past posts keep their author.
        user = membership.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        membership.approved = False
        membership.save(update_fields=["approved"])
        messages.success(request, (_("%(who)s no longer has access.") if action == "remove"
                                   else _("Declined %(who)s.")) % {"who": who})
    return redirect("team")


# --- Scheduler link for external timers (Vercel) -------------------------------------------------

def _cron_authorized(request):
    secret = settings.CRON_SECRET
    supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or request.GET.get("key", "")
    return bool(secret) and hmac.compare_digest(supplied.encode(), secret.encode())


@csrf_exempt
def cron_tick(request):
    """Runs one scheduler pass. Called every few minutes by cron-job.org / GitHub Actions / Vercel Cron."""
    if not _cron_authorized(request):
        return JsonResponse({"error": "forbidden"}, status=403)
    summary = scheduler.tick(budget_seconds=40)
    return JsonResponse({"ok": True, **summary})


def cron_status(request):
    """Health check for troubleshooting (same secret as the scheduler): recent posts' states, no captions."""
    if not _cron_authorized(request):
        return JsonResponse({"error": "forbidden"}, status=403)
    account = InstagramAccount.current()
    queue = QueueSettings.load()
    posts = [{
        "id": p.pk, "type": p.post_type, "status": p.status, "source": p.source,
        "scheduled_at": p.scheduled_at, "published_at": p.published_at, "ig_media_id": p.ig_media_id,
        "permalink": p.permalink, "error": p.error[:500], "publish_state": p.publish_state,
        "media": [{"kind": a.kind, "size": [a.width, a.height]} for a in p.ordered_media],
    } for p in Post.objects.order_by("-pk")[:15]]
    return JsonResponse({
        "now": timezone.now(),
        "instagram": {"username": account.username, "type": account.account_type,
                      "token_expires_at": account.token_expires_at} if account else None,
        "scheduler_last_run": SchedulerHeartbeat.last_run(),
        "queue": {
            "active": queue.active, "weekdays": queue.weekdays, "timing_mode": queue.timing_mode, "times": queue.times,
            "window": [str(queue.window_start), str(queue.window_end)], "posts_per_day": queue.posts_per_day,
            "source": queue.source, "random_order": queue.random_order, "reuse_items": queue.reuse_items,
            "caption_mode": queue.caption_mode, "as_story": queue.as_story,
            "next_run_at": queue.next_run_at, "planned_runs": queue.planned_runs, "last_run_at": queue.last_run_at,
            "candidates": queue.candidates().count(), "library_size": MediaAsset.objects.count(),
            "marked_in_queue": MediaAsset.objects.filter(in_queue=True).count(),
        },
        "recurring_active": RecurringRule.objects.filter(active=True).count(),
        "posts": posts,
    })


# --- Public "link in bio" page ---------------------------------------------------------------------

def links_page(request):
    page = LinkPage.load()
    tiles = []
    if page.show_posts:
        posts = (Post.objects.filter(status=Post.PUBLISHED).exclude(link="").exclude(post_type=Post.STORY)
                 .order_by("-published_at").prefetch_related("items__asset")[:30])
        for post in posts:
            media = post.ordered_media
            if media:
                tiles.append({"post": post, "asset": media[0], "url": full_url(post.link)})
    buttons = [{"label": b.get("label"), "url": full_url(b.get("url", ""))} for b in page.buttons if b.get("url")]
    return render(request, "studio/links_public.html", {
        "page": page, "buttons": buttons, "tiles": tiles, "account": InstagramAccount.current(),
    })


@owner_required
def links_settings(request):
    page = LinkPage.load()
    form = LinkPageForm(request.POST or None, initial=LinkPageForm.initial_for(page))
    if request.method == "POST" and form.is_valid():
        page.headline = form.cleaned_data["headline"]
        page.bio = form.cleaned_data["bio"]
        page.show_posts = form.cleaned_data["show_posts"]
        page.buttons = form.cleaned_data["buttons"]
        page.save()
        messages.success(request, _("Links page saved."))
        return redirect("links_settings")
    public_url = f"{settings.SITE_URL}/links/"
    return render(request, "studio/links_settings.html", {
        "form": form, "public_url": public_url,
        "linked_posts": Post.objects.filter(status=Post.PUBLISHED).exclude(link="").exclude(post_type=Post.STORY).count(),
    })


# --- Stats ---------------------------------------------------------------------------------------

@login_required
def stats_page(request):
    from . import stats
    from datetime import time as dtime

    if request.method == "POST" and request.POST.get("action") == "refresh":
        state = stats.refresh(budget_seconds=25, force=True)
        if state.error:
            messages.error(request, state.error)
        else:
            messages.success(request, _("Results updated from Instagram."))
        return redirect("stats")
    if request.method == "POST" and request.POST.get("action") == "use_window":
        if not request.membership.is_owner:
            messages.error(request, _("Only an owner can change the queue settings."))
            return redirect("stats")
        window = stats.summary()["best_window"]
        if window:
            queue = QueueSettings.load()
            queue.timing_mode = QueueSettings.TIMING_RANDOM
            queue.window_start, queue.window_end = dtime(window["start"]), dtime(window["end"] % 24)
            if window["end"] >= 24:
                queue.window_end = dtime(23, 59)
            queue.posts_per_day = min(queue.posts_per_day, 3)
            queue.planned_runs = []
            queue.next_run_at, queue.planned_runs = queue.plan_after()
            queue.save()
            messages.success(request, _("The queue now posts at random times between %(start)s and %(end)s.") % {
                "start": f"{queue.window_start:%H:%M}", "end": f"{queue.window_end:%H:%M}"})
        return redirect("queue")
    data = stats.summary()
    day_names = [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]
    for row in data["day_rows"]:
        row["label"] = day_names[row["key"]]
    for row in data["hour_rows"] + data["online_rows"]:
        row["label"] = f"{row['key']:02d}:00"
    window = data["best_window"]
    if window:
        for row in data["hour_rows"] + data["online_rows"]:
            row["best"] = window["start"] <= row["key"] < window["end"]
    return render(request, "studio/stats.html", {**data, "account": InstagramAccount.current()})
