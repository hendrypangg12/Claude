"""Compose the final 1080x1080 Instagram post with a headline overlay."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

CANVAS = 1080
PADDING = 60
HEADLINE_BOX_HEIGHT = 380
HEADLINE_FONT_SIZE = 58
SOURCE_FONT_SIZE = 28
BRAND_FONT_SIZE = 32
BRAND_TEXT = "BERSTOCK.ID"
BRAND_ACCENT = (255, 196, 0)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    # Try a few common font paths; fall back to PIL default.
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def compose(background_path: str, headline: str, source: str, out_path: str) -> str:
    bg = Image.open(background_path).convert("RGB")
    bg = ImageOps.fit(bg, (CANVAS, CANVAS), method=Image.LANCZOS)

    overlay = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        [(0, CANVAS - HEADLINE_BOX_HEIGHT), (CANVAS, CANVAS)],
        fill=(0, 0, 0, 180),
    )

    brand_font = _load_font(BRAND_FONT_SIZE)
    brand_w = brand_font.getlength(BRAND_TEXT)
    brand_pad_x, brand_pad_y = 18, 10
    brand_box = (
        PADDING,
        PADDING,
        PADDING + brand_w + 2 * brand_pad_x,
        PADDING + BRAND_FONT_SIZE + 2 * brand_pad_y,
    )
    draw.rectangle(brand_box, fill=BRAND_ACCENT)

    composed = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(composed)

    draw.text(
        (PADDING + brand_pad_x, PADDING + brand_pad_y - 2),
        BRAND_TEXT,
        font=brand_font,
        fill=(20, 20, 20),
    )

    headline_font = _load_font(HEADLINE_FONT_SIZE)
    source_font = _load_font(SOURCE_FONT_SIZE)

    max_text_width = CANVAS - 2 * PADDING
    lines = _wrap(headline, headline_font, max_text_width)

    line_height = HEADLINE_FONT_SIZE + 12
    block_height = line_height * len(lines)
    y = CANVAS - HEADLINE_BOX_HEIGHT + (HEADLINE_BOX_HEIGHT - block_height) // 2 - 20

    for line in lines:
        draw.text((PADDING, y), line, font=headline_font, fill=(255, 255, 255))
        y += line_height

    if source:
        draw.text(
            (PADDING, CANVAS - PADDING - SOURCE_FONT_SIZE),
            f"Sumber: {source}",
            font=source_font,
            fill=(220, 220, 220),
        )

    composed.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
