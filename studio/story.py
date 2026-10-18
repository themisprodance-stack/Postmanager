"""Story images with text on them, e.g. “Tonight 20:00 · Beginners” over a class photo (1080×1920 JPEG)."""

import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .media import STORY_SIZE, create_image_asset, story_canvas

FONTS = Path(__file__).parent / "fonts"
W, H = STORY_SIZE
MARGIN = 80  # Instagram covers the top and bottom ~250 px with the profile bar and reply box
SAFE_TOP, SAFE_BOTTOM = 270, H - 300

TOP, MIDDLE, BOTTOM = "top", "middle", "bottom"
POSITIONS = [TOP, MIDDLE, BOTTOM]

# name: (panel colour with alpha, text colour)
STYLES = {
    "dark": ((0, 0, 0, 150), (255, 255, 255)),
    "light": ((255, 255, 255, 215), (31, 26, 36)),
    "brand": ((194, 24, 91, 230), (255, 255, 255)),
    "none": (None, (255, 255, 255)),
}
BRAND_BACKGROUND = ((194, 24, 91), (74, 20, 140))  # used when no photo is picked: pink to purple

# The bundled font has no emoji; they would show as empty boxes.
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def _font(weight, size):
    return ImageFont.truetype(str(FONTS / f"NotoSans-{weight}.ttf"), size)


def _wrap(draw, text, font, width):
    lines = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return [line for line in lines if line] or []


def _gradient():
    top, bottom = BRAND_BACKGROUND
    column = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return column.resize(STORY_SIZE)


def _fit_lines(draw, text, weight, size, min_size, max_lines, width):
    """Shrink the font until the text fits in max_lines lines."""
    while True:
        font = _font(weight, size)
        lines = _wrap(draw, text, font, width)
        if len(lines) <= max_lines or size <= min_size:
            return font, lines[:max_lines]
        size -= max(2, size // 20)


def render_story(image, headline, text="", position=BOTTOM, style="dark", headline_size=100, text_size=100):
    """Return a 1080×1920 RGB image: the photo (or a brand gradient) with the text on a panel.
    headline_size and text_size are percentages of the normal letter size."""
    canvas = story_canvas(image) if image is not None else _gradient()
    headline, text = EMOJI.sub("", headline).strip(), EMOJI.sub("", text).strip()
    panel_colour, text_colour = STYLES.get(style, STYLES["dark"])
    if not (headline or text):
        return canvas

    overlay = Image.new("RGBA", STORY_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    pad = 50
    width = W - 2 * MARGIN - 2 * pad
    blocks = []  # (font, lines, line height)
    if headline:
        scale = headline_size / 100
        font, lines = _fit_lines(draw, headline, "Bold", round(120 * scale), round(48 * scale), 6, width)
        blocks.append((font, lines, round(font.size * 1.18)))
    if text:
        scale = text_size / 100
        font, lines = _fit_lines(draw, text, "Regular", round(62 * scale), round(30 * scale), 10, width)
        blocks.append((font, lines, round(font.size * 1.3)))
    gap = 30
    content_h = sum(len(lines) * lh for _f, lines, lh in blocks) + gap * (len(blocks) - 1)
    panel_h = content_h + 2 * pad

    if position == TOP:
        y0 = SAFE_TOP
    elif position == MIDDLE:
        y0 = (H - panel_h) // 2
    else:
        y0 = SAFE_BOTTOM - panel_h
    if panel_colour:
        draw.rounded_rectangle((MARGIN, y0, W - MARGIN, y0 + panel_h), radius=36, fill=panel_colour)

    y = y0 + pad
    for i, (font, lines, line_h) in enumerate(blocks):
        for line in lines:
            x = (W - draw.textlength(line, font=font)) / 2
            if not panel_colour:  # plain text needs a shadow to stay readable on any photo
                draw.text((x + 3, y + 4), line, font=font, fill=(0, 0, 0, 170))
            draw.text((x, y), line, font=font, fill=text_colour)
            y += line_h
        if i < len(blocks) - 1:
            y += gap
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _open_photo(asset):
    if asset is None:
        return None
    with asset.file.open("rb") as fh:
        return ImageOps.exif_transpose(Image.open(fh)).convert("RGB")


def story_jpeg(asset, preview_width=None, **options):
    image = render_story(_open_photo(asset), **options)
    if preview_width:
        image = image.resize((preview_width, round(preview_width * H / W)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85 if preview_width else 90)
    return buffer.getvalue()


def save_story(asset, user=None, **options):
    """Create a library photo from the story design. Returns the new MediaAsset."""
    title = (options.get("headline") or "Story")[:60]
    return create_image_asset(io.BytesIO(story_jpeg(asset, **options)), f"{title}.jpg", user)
