"""AI caption suggestions using Claude. Disabled when ANTHROPIC_API_KEY is not set."""

import base64
import io
import json
import logging

import anthropic
from django.conf import settings
from django.utils.translation import gettext as _
from PIL import Image

log = logging.getLogger(__name__)

MAX_IMAGES = 4
IMAGE_MAX_SIDE = 1024

CAPTION_SCHEMA = {
    "type": "object",
    "properties": {"captions": {"type": "array", "items": {"type": "string"}}},
    "required": ["captions"],
    "additionalProperties": False,
}

POST_TYPE_HINTS = {
    "feed": "a single-photo feed post",
    "carousel": "a carousel post (several photos/videos people swipe through)",
    "reel": "a Reel (short vertical dance video)",
    "story": "a Story (keep it very short; captions are shown as text overlay ideas)",
}


class CaptionError(Exception):
    pass


def enabled():
    return bool(settings.ANTHROPIC_API_KEY)


def _image_block(asset):
    with asset.file.open("rb") as fh:
        image = Image.open(fh).convert("RGB")
    image.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85)
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(buffer.getvalue()).decode()},
    }


def suggest_captions(brief, assets=(), post_type="feed", count=3):
    """Return `count` caption options for the given brief and media."""
    if not enabled():
        raise CaptionError(_("AI captions are not set up: add ANTHROPIC_API_KEY to the environment."))

    content = [_image_block(a) for a in assets if not a.is_video][:MAX_IMAGES]
    videos = sum(1 for a in assets if a.is_video)
    request = [f"Write {count} different Instagram caption options for {POST_TYPE_HINTS.get(post_type, 'a post')}."]
    if brief.strip():
        request.append(f"What the post is about: {brief.strip()}")
    if content:
        request.append("The attached photos are the post's media.")
    if videos:
        request.append(f"The post also includes {videos} video(s) you cannot see; rely on the description for them.")
    request.append(
        "Each option should have a different angle (e.g. inspiring, playful, informative). "
        "End each with 5-10 relevant hashtags. Keep each under 1,500 characters. "
        "Write in the same language as the description (English if there is none). "
        "Don't invent specific facts such as prices, dates or teacher names unless they are in the description."
    )
    content.append({"type": "text", "text": "\n\n".join(request)})

    system = (
        f"You write Instagram captions for {settings.STUDIO_NAME}, a dance studio. "
        f"Brand voice: {settings.STUDIO_VOICE}"
    )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.beta.messages.create(
            model=settings.CAPTION_MODEL,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": CAPTION_SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise CaptionError(_("The Anthropic API key is invalid."))
    except anthropic.RateLimitError:
        raise CaptionError(_("Too many AI requests right now; try again in a minute."))
    except anthropic.APIStatusError as exc:
        log.exception("Caption request failed")
        raise CaptionError(_("AI service error (%(status)s).") % {"status": exc.status_code})
    except anthropic.APIConnectionError:
        raise CaptionError(_("Could not reach the AI service."))

    if response.stop_reason == "refusal":
        raise CaptionError(_("The AI declined to write a caption for this content."))
    if response.stop_reason == "max_tokens":
        raise CaptionError(_("The AI response was cut off; try a shorter description."))
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        captions = [c.strip() for c in json.loads(text)["captions"] if c.strip()]
    except (ValueError, KeyError, TypeError):
        raise CaptionError(_("The AI returned an unexpected response."))
    if not captions:
        raise CaptionError(_("The AI returned no captions."))
    return captions[:count]


def write_caption(brief, assets=(), post_type="feed"):
    """One caption, for automated posts."""
    return suggest_captions(brief, assets, post_type, count=1)[0]
