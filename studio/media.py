"""Upload handling. Instagram only accepts JPEG photos with an aspect ratio between 4:5 and 1.91:1 in the
feed, and MP4/MOV videos, so photos are normalised on upload and padded on demand when publishing."""

import io
import logging
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.translation import gettext as _
from PIL import Image, ImageFilter, ImageOps

from .models import MediaAsset, MusicTrack, absolute_url

log = logging.getLogger(__name__)

try:  # iPhone photos
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav"}
MAX_IMAGE_WIDTH = 1440
STORY_SIZE = (1080, 1920)  # 9:16, the shape of Stories and Reels
FEED_MIN_RATIO = 4 / 5
FEED_MAX_RATIO = 1.91


class UnsupportedFile(ValueError):
    pass


def save_upload(uploaded, user=None):
    ext = Path(uploaded.name).suffix.lower()
    title = Path(uploaded.name).stem[:200]
    if ext in VIDEO_EXTENSIONS:
        asset = MediaAsset(kind=MediaAsset.VIDEO, title=title, uploaded_by=user)
        asset.file.save(f"upload{ext}", uploaded, save=False)
        asset.save()
        return asset
    if ext in IMAGE_EXTENSIONS or (uploaded.content_type or "").startswith("image/"):
        return create_image_asset(uploaded, uploaded.name, user)
    raise UnsupportedFile(_("%(name)s: only photos and MP4/MOV videos are supported.") % {"name": uploaded.name})


def create_image_asset(fileobj, original_name, user=None):
    """Normalise a photo to an Instagram-friendly JPEG (upright, max 1440 px wide) and store it."""
    try:
        image = Image.open(fileobj)
        image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception:  # Pillow raises many different errors for bad files
        try:
            fileobj.seek(0)
            head = fileobj.read(16)
        except Exception:
            head = b""
        log.warning("Unreadable image %s (first bytes %r)", original_name, head)
        raise UnsupportedFile(_("%(name)s: this file couldn't be opened as a photo. Try exporting it as JPEG.")
                              % {"name": original_name})
    if image.width > MAX_IMAGE_WIDTH:
        image = image.resize((MAX_IMAGE_WIDTH, round(image.height * MAX_IMAGE_WIDTH / image.width)), Image.LANCZOS)
    asset = MediaAsset(
        kind=MediaAsset.IMAGE, title=Path(original_name).stem[:200], width=image.width, height=image.height,
        uploaded_by=user,
    )
    asset.file.save("upload.jpg", ContentFile(_jpeg_bytes(image)), save=False)
    asset.save()
    return asset


# --- Direct browser uploads (Vercel Blob) ------------------------------------------------------

MAX_DIRECT_IMAGE_BYTES = 40 * 1024 * 1024
MAX_DIRECT_VIDEO_BYTES = 300 * 1024 * 1024  # Instagram's Reels limit
DIRECT_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/gif"]
DIRECT_VIDEO_TYPES = ["video/mp4", "video/quicktime"]
MAX_MUSIC_BYTES = 50 * 1024 * 1024
DIRECT_AUDIO_TYPES = ["audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/aac", "audio/wav", "audio/x-wav",
                      "audio/wave", "application/octet-stream"]


def plan_direct_upload(filename, content_type, size):
    """Decide where a browser upload goes. Returns (pathname, allowed_types, max_bytes)."""
    ext = Path(filename).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        if size > MAX_MUSIC_BYTES:
            raise UnsupportedFile(_("%(name)s: music files can be at most 50 MB.") % {"name": filename})
        return f"music/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}", DIRECT_AUDIO_TYPES, MAX_MUSIC_BYTES
    if ext in VIDEO_EXTENSIONS or content_type in DIRECT_VIDEO_TYPES:
        if size > MAX_DIRECT_VIDEO_BYTES:
            raise UnsupportedFile(_("%(name)s: videos can be at most 300 MB.") % {"name": filename})
        ext = ext if ext in VIDEO_EXTENSIONS else ".mp4"
        return f"library/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}", DIRECT_VIDEO_TYPES, MAX_DIRECT_VIDEO_BYTES
    if ext in IMAGE_EXTENSIONS or content_type.startswith("image/"):
        if size > MAX_DIRECT_IMAGE_BYTES:
            raise UnsupportedFile(_("%(name)s: photos can be at most 40 MB.") % {"name": filename})
        return f"incoming/{uuid.uuid4().hex}{ext or '.jpg'}", DIRECT_IMAGE_TYPES, MAX_DIRECT_IMAGE_BYTES
    raise UnsupportedFile(_("%(name)s: only photos and MP4/MOV videos are supported.") % {"name": filename})


def register_direct_upload(pathname, original_name, user=None):
    """Create a library item from a file the browser uploaded straight to storage."""
    if not default_storage.exists(pathname):
        raise UnsupportedFile(_("%(name)s: the upload didn't arrive. Please try again.") % {"name": original_name})
    if pathname.startswith("library/") and Path(pathname).suffix.lower() in VIDEO_EXTENSIONS:
        asset = MediaAsset(kind=MediaAsset.VIDEO, title=Path(original_name).stem[:200], uploaded_by=user)
        asset.file.name = pathname
        asset.save()
        return asset
    if pathname.startswith("incoming/"):
        try:
            with default_storage.open(pathname) as fh:
                return create_image_asset(fh, original_name, user)
        finally:
            default_storage.delete(pathname)
    raise UnsupportedFile(_("Unknown upload."))


# --- Music ------------------------------------------------------------------------------------

def _check_music_name(name):
    if Path(name).suffix.lower() not in AUDIO_EXTENSIONS:
        raise UnsupportedFile(_("%(name)s: only MP3, M4A, AAC and WAV music files are supported.") % {"name": name})


def _with_duration(track):
    """Read the track's length and refuse files that aren't really audio."""
    import tempfile

    from .video import local_copy, probe

    with tempfile.TemporaryDirectory() as tmp:
        duration, has_audio = probe(local_copy(track.file, tmp))
    if not has_audio:
        track.file.delete(save=False)
        raise UnsupportedFile(_("%(name)s: this file couldn't be played as music.") % {"name": track})
    track.duration = duration
    track.save()
    return track


def save_music_upload(uploaded, user=None):
    _check_music_name(uploaded.name)
    track = MusicTrack(title=Path(uploaded.name).stem[:200], uploaded_by=user)
    track.file.save(f"music{Path(uploaded.name).suffix.lower()}", uploaded, save=False)
    return _with_duration(track)


def register_music_upload(pathname, original_name, user=None):
    """Create a music track from a file the browser uploaded straight to storage."""
    _check_music_name(original_name)
    if not pathname.startswith("music/") or not default_storage.exists(pathname):
        raise UnsupportedFile(_("%(name)s: the upload didn't arrive. Please try again.") % {"name": original_name})
    track = MusicTrack(title=Path(original_name).stem[:200], uploaded_by=user)
    track.file.name = pathname
    return _with_duration(track)


def _jpeg_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90, optimize=True)
    return buffer.getvalue()


def feed_ready_url(asset):
    """Public URL of a version of this photo that fits Instagram's feed aspect-ratio limits."""
    ratio = asset.aspect_ratio
    if ratio is None or FEED_MIN_RATIO <= ratio <= FEED_MAX_RATIO:
        return asset.public_url
    name = str(Path(asset.file.name).with_suffix("")) + "_feed.jpg"
    if not default_storage.exists(name):
        with asset.file.open("rb") as fh:
            image = Image.open(fh).convert("RGB")
        default_storage.save(name, ContentFile(_jpeg_bytes(_pad_to_ratio(image, ratio))))
    return absolute_url(default_storage.url(name))


def _pad_to_ratio(image, ratio):
    """Place the photo on a blurred copy of itself so nothing gets cropped."""
    target = FEED_MIN_RATIO if ratio < FEED_MIN_RATIO else FEED_MAX_RATIO
    if ratio < target:  # too tall: widen the canvas
        size = (round(image.height * target), image.height)
    else:  # too wide: make the canvas taller
        size = (image.width, round(image.width / target))
    background = ImageOps.fit(image, size).filter(ImageFilter.GaussianBlur(40))
    background.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return background


def story_canvas(image):
    """The photo fitted inside a 9:16 frame, on a blurred copy of itself so nothing gets cropped."""
    image = image.convert("RGB")
    frame = ImageOps.fit(image, STORY_SIZE).filter(ImageFilter.GaussianBlur(40))
    image = ImageOps.contain(image, STORY_SIZE, Image.LANCZOS)
    frame.paste(image, ((STORY_SIZE[0] - image.width) // 2, (STORY_SIZE[1] - image.height) // 2))
    return frame


def delete_asset_files(asset):
    derived = str(Path(asset.file.name).with_suffix("")) + "_feed.jpg"
    if default_storage.exists(derived):
        default_storage.delete(derived)
    asset.file.delete(save=False)
