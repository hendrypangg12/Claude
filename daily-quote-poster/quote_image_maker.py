"""Render a Folkative-style text-only quote card (1080x1080)."""
from PIL import Image, ImageDraw, ImageFont

CANVAS = 1080
PADDING = 80
BRAND_TEXT = "LALU"
BRAND_FONT_SIZE = 36
MAX_FONT_SIZE = 110
MIN_FONT_SIZE = 50
LINE_SPACING = 1.18


def _load_font(size: int) -> ImageFont.FreeTypeFont:
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


def _fit_font(text: str, max_width: int, max_height: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Find the largest font size where the wrapped text fits the box."""
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -4):
        font = _load_font(size)
        lines = _wrap(text, font, max_width)
        line_h = int(size * LINE_SPACING)
        total_h = line_h * len(lines)
        if total_h <= max_height and all(font.getlength(l) <= max_width for l in lines):
            return font, lines
    font = _load_font(MIN_FONT_SIZE)
    return font, _wrap(text, font, max_width)


def compose_quote(text: str, out_path: str) -> str:
    canvas = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    max_w = CANVAS - 2 * PADDING
    max_h = CANVAS - 2 * PADDING - 80  # leave room for brand at top
    font, lines = _fit_font(text, max_w, max_h)

    line_h = int(font.size * LINE_SPACING)
    block_h = line_h * len(lines)
    y = (CANVAS - block_h) // 2 + 20

    for line in lines:
        w = font.getlength(line)
        x = (CANVAS - w) // 2 if False else PADDING  # left-align like folkative
        draw.text((x, y), line, font=font, fill=(15, 15, 15))
        y += line_h

    brand_font = _load_font(BRAND_FONT_SIZE)
    brand_w = brand_font.getlength(BRAND_TEXT)
    draw.text(
        (CANVAS - PADDING - brand_w, PADDING - 20),
        BRAND_TEXT,
        font=brand_font,
        fill=(15, 15, 15),
    )

    canvas.save(out_path, "JPEG", quality=94)
    return out_path
