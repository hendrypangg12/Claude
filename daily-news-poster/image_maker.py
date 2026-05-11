"""Compose the 1080x1080 Instagram carousel slides for a news post."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

CANVAS = 1080
PADDING = 60
HEADLINE_BOX_HEIGHT = 380
HEADLINE_FONT_SIZE = 58
SOURCE_FONT_SIZE = 28
BRAND_FONT_SIZE = 32
BODY_FONT_SIZE = 44
BODY_TITLE_FONT_SIZE = 56
SWIPE_FONT_SIZE = 26
BRAND_TEXT = "BERSTOCK.ID"
BRAND_ACCENT = (255, 196, 0)
DARK_BG = (18, 22, 28)
TEXT_LIGHT = (245, 245, 245)
TEXT_MUTED = (180, 180, 180)


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


def _draw_brand_chip(draw: ImageDraw.ImageDraw, x: int = PADDING, y: int = PADDING) -> None:
    brand_font = _load_font(BRAND_FONT_SIZE)
    brand_w = brand_font.getlength(BRAND_TEXT)
    pad_x, pad_y = 18, 10
    draw.rectangle(
        [(x, y), (x + brand_w + 2 * pad_x, y + BRAND_FONT_SIZE + 2 * pad_y)],
        fill=BRAND_ACCENT,
    )
    draw.text((x + pad_x, y + pad_y - 2), BRAND_TEXT, font=brand_font, fill=(20, 20, 20))


def _draw_slide_number(draw: ImageDraw.ImageDraw, index: int, total: int) -> None:
    font = _load_font(SWIPE_FONT_SIZE)
    text = f"{index}/{total}"
    tw = font.getlength(text)
    draw.text((CANVAS - PADDING - tw, PADDING + 8), text, font=font, fill=TEXT_LIGHT)


def _blurred_background(image_path: str) -> Image.Image:
    bg = Image.open(image_path).convert("RGB")
    bg = ImageOps.fit(bg, (CANVAS, CANVAS), method=Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=24))
    dim = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 140))
    return Image.alpha_composite(bg.convert("RGBA"), dim).convert("RGB")


def _solid_background() -> Image.Image:
    return Image.new("RGB", (CANVAS, CANVAS), DARK_BG)


def compose_slide_points(background_path: str, points: list[str], out_path: str) -> str:
    """Slide 2: 'Poin Penting' with 3 bullet points over a blurred bg."""
    try:
        canvas = _blurred_background(background_path)
    except Exception:
        canvas = _solid_background()
    draw = ImageDraw.Draw(canvas)

    _draw_brand_chip(draw)
    _draw_slide_number(draw, 2, 3)

    title_font = _load_font(BODY_TITLE_FONT_SIZE)
    body_font = _load_font(BODY_FONT_SIZE)

    title = "POIN PENTING"
    draw.text((PADDING, 260), title, font=title_font, fill=BRAND_ACCENT)

    y = 360
    bullet_gap = 30
    max_w = CANVAS - 2 * PADDING - 50
    for i, point in enumerate(points[:3], start=1):
        if not point:
            continue
        number = f"{i}."
        draw.text((PADDING, y), number, font=body_font, fill=BRAND_ACCENT)
        text_x = PADDING + 50
        lines = _wrap(point, body_font, max_w)
        for line in lines:
            draw.text((text_x, y), line, font=body_font, fill=TEXT_LIGHT)
            y += BODY_FONT_SIZE + 12
        y += bullet_gap

    swipe_font = _load_font(SWIPE_FONT_SIZE)
    swipe = "Geser →"
    sw = swipe_font.getlength(swipe)
    draw.text((CANVAS - PADDING - sw, CANVAS - PADDING - SWIPE_FONT_SIZE), swipe, font=swipe_font, fill=TEXT_MUTED)

    canvas.save(out_path, "JPEG", quality=92)
    return out_path


def compose_slide_takeaway(background_path: str, takeaway: str, source: str, out_path: str) -> str:
    """Slide 3: takeaway quote + follow CTA over a blurred bg."""
    try:
        canvas = _blurred_background(background_path)
    except Exception:
        canvas = _solid_background()
    draw = ImageDraw.Draw(canvas)

    _draw_brand_chip(draw)
    _draw_slide_number(draw, 3, 3)

    body_font = _load_font(BODY_FONT_SIZE + 4)
    title_font = _load_font(BODY_TITLE_FONT_SIZE)
    cta_font = _load_font(BODY_FONT_SIZE)
    source_font = _load_font(SOURCE_FONT_SIZE)

    draw.text((PADDING, 260), "INTINYA", font=title_font, fill=BRAND_ACCENT)

    lines = _wrap(takeaway, body_font, CANVAS - 2 * PADDING)
    y = 360
    for line in lines:
        draw.text((PADDING, y), line, font=body_font, fill=TEXT_LIGHT)
        y += BODY_FONT_SIZE + 16

    cta_main = "Follow @berstock.id"
    cta_sub = "untuk berita harian terkurasi"
    cta_y = CANVAS - PADDING - 2 * (BODY_FONT_SIZE + 14) - SOURCE_FONT_SIZE - 10
    draw.text((PADDING, cta_y), cta_main, font=cta_font, fill=BRAND_ACCENT)
    draw.text((PADDING, cta_y + BODY_FONT_SIZE + 8), cta_sub, font=cta_font, fill=TEXT_LIGHT)

    if source:
        draw.text(
            (PADDING, CANVAS - PADDING - SOURCE_FONT_SIZE),
            f"Sumber: {source}",
            font=source_font,
            fill=TEXT_MUTED,
        )

    canvas.save(out_path, "JPEG", quality=92)
    return out_path


def compose(background_path: str, headline: str, source: str, out_path: str) -> str:
    bg = Image.open(background_path).convert("RGB")
    bg = ImageOps.fit(bg, (CANVAS, CANVAS), method=Image.LANCZOS)

    overlay = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, CANVAS - HEADLINE_BOX_HEIGHT), (CANVAS, CANVAS)],
        fill=(0, 0, 0, 180),
    )

    composed = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(composed)

    _draw_brand_chip(draw)
    _draw_slide_number(draw, 1, 3)

    headline_font = _load_font(HEADLINE_FONT_SIZE)
    source_font = _load_font(SOURCE_FONT_SIZE)
    swipe_font = _load_font(SWIPE_FONT_SIZE)

    max_text_width = CANVAS - 2 * PADDING
    lines = _wrap(headline, headline_font, max_text_width)

    line_height = HEADLINE_FONT_SIZE + 12
    block_height = line_height * len(lines)
    y = CANVAS - HEADLINE_BOX_HEIGHT + (HEADLINE_BOX_HEIGHT - block_height) // 2 - 30

    for line in lines:
        draw.text((PADDING, y), line, font=headline_font, fill=TEXT_LIGHT)
        y += line_height

    if source:
        draw.text(
            (PADDING, CANVAS - PADDING - SOURCE_FONT_SIZE),
            f"Sumber: {source}",
            font=source_font,
            fill=(220, 220, 220),
        )

    swipe = "Geser →"
    sw = swipe_font.getlength(swipe)
    draw.text((CANVAS - PADDING - sw, CANVAS - PADDING - SWIPE_FONT_SIZE), swipe, font=swipe_font, fill=BRAND_ACCENT)

    composed.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
