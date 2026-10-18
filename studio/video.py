"""Turning a photo or video plus a music track into an Instagram-ready MP4 (H.264 video, AAC audio).

Uses the ffmpeg binary that ships with the imageio-ffmpeg package, so nothing needs installing on the server.
Inputs are copied to a temporary folder first, because cloud storage files only exist as URLs.
"""

import logging
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

import requests
from django.core.files import File
from django.utils.translation import gettext as _
from PIL import Image, ImageFilter, ImageOps

from .models import MediaAsset

log = logging.getLogger(__name__)

STORY_SIZE = (1080, 1920)  # 9:16, the shape of Stories and Reels
FRAME_RATE = 24  # Instagram accepts 23-60 fps; fewer frames encode faster
MIN_SECONDS = 3  # Instagram rejects shorter videos
MAX_PHOTO_SECONDS = 30
MAX_VIDEO_BYTES = 150 * 1024 * 1024  # download + upload must fit in one server request
FFMPEG_TIMEOUT = 50


class VideoError(Exception):
    pass


def ffmpeg_exe():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(args):
    try:
        result = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostdin", *args], capture_output=True, text=True,
                                timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise VideoError(_("Making the video took too long. Try a shorter video or length."))
    return result


def probe(path):
    """Return (duration in seconds or None, has_audio) for a media file."""
    stderr = _run(["-i", str(path)]).stderr  # ffmpeg prints the file info and exits with an error; that's fine
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    duration = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else None
    return duration, bool(re.search(r"Stream #.*: Audio:", stderr))


def local_copy(fieldfile, folder):
    """Path of a local copy of a stored file (the file itself when storage is local)."""
    try:
        return fieldfile.path
    except NotImplementedError:  # cloud storage
        pass
    dest = Path(folder) / f"in-{uuid.uuid4().hex}{Path(fieldfile.name).suffix}"
    with requests.get(fieldfile.url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(1 << 20):
                fh.write(chunk)
    return str(dest)


def _story_frame(asset, dest):
    """The photo fitted inside a 9:16 frame, on a blurred copy of itself so nothing gets cropped."""
    with asset.file.open("rb") as fh:
        image = ImageOps.exif_transpose(Image.open(fh)).convert("RGB")
    frame = ImageOps.fit(image, STORY_SIZE).filter(ImageFilter.GaussianBlur(40))
    image = ImageOps.contain(image, STORY_SIZE, Image.LANCZOS)
    frame.paste(image, ((STORY_SIZE[0] - image.width) // 2, (STORY_SIZE[1] - image.height) // 2))
    frame.save(dest, "JPEG", quality=92)


def _fades(length):
    fade_out = min(2.0, length / 3)
    return f"afade=t=in:d=0.5,afade=t=out:st={length - fade_out:.2f}:d={fade_out:.2f}"


AUDIO_OUT = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def make_music_video(asset, track, *, start=0.0, length=15, keep_original_sound=False, user=None):
    """Create a new library video: the photo (shown for `length` seconds) or video, with the track playing from
    `start` seconds. The music loops if it's shorter than the video. Returns the new MediaAsset."""
    with tempfile.TemporaryDirectory() as tmp:
        music = local_copy(track.file, tmp)
        out = str(Path(tmp) / "out.mp4")
        music_input = ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", music]
        if asset.is_video:
            if (asset.file.size or 0) > MAX_VIDEO_BYTES:
                raise VideoError(_("This video is too big to add music here (max 150 MB)."))
            source = local_copy(asset.file, tmp)
            length, has_audio = probe(source)
            if not length:
                raise VideoError(_("This video couldn't be read."))
            if keep_original_sound and has_audio:
                audio = ["-filter_complex",
                         f"[0:a]volume=0.35[orig];[1:a]{_fades(length)}[song];"
                         "[orig][song]amix=inputs=2:duration=first:normalize=0[a]",
                         "-map", "0:v:0", "-map", "[a]"]
            else:
                audio = ["-af", _fades(length), "-map", "0:v:0", "-map", "1:a:0"]
            args = ["-y", "-i", source, *music_input, "-t", f"{length:.2f}", *audio, "-c:v", "copy", *AUDIO_OUT]
            size = (asset.width, asset.height)
        else:
            frame = str(Path(tmp) / "frame.jpg")
            _story_frame(asset, frame)
            args = ["-y", "-loop", "1", "-framerate", str(FRAME_RATE), "-i", frame, *music_input,
                    "-t", str(length), "-map", "0:v", "-map", "1:a", "-af", _fades(length),
                    "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-r", str(FRAME_RATE), "-g", str(FRAME_RATE * 2), *AUDIO_OUT]
            size = STORY_SIZE
        result = _run([*args, "-movflags", "+faststart", out])
        if result.returncode != 0 or not Path(out).exists():
            log.warning("ffmpeg failed: %s", result.stderr[-2000:])
            raise VideoError(_("The video couldn't be made from these files."))
        new = MediaAsset(kind=MediaAsset.VIDEO, title=f"{asset} + {track}"[:200], width=size[0], height=size[1],
                         uploaded_by=user)
        with open(out, "rb") as fh:
            new.file.save("music.mp4", File(fh), save=False)
        new.save()
        return new
