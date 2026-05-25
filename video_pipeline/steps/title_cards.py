"""Title + end-card PNG renderers (Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1920


def render_title_card(text: str, dest: Path, *, font_path: str | None = None) -> Path:
    img = Image.new("RGB", (W, H), (10, 10, 14))
    d = ImageDraw.Draw(img)
    font = _load_font(font_path, size=160)
    bbox = d.multiline_textbbox((0, 0), text, font=font, align="center")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    d.multiline_text(((W - tw) / 2, (H - th) / 2), text, font=font, fill="white", align="center")
    img.save(dest)
    return dest


def render_end_card(text: str, dest: Path, *, font_path: str | None = None) -> Path:
    img = Image.new("RGB", (W, H), (10, 10, 14))
    d = ImageDraw.Draw(img)
    font = _load_font(font_path, size=110)
    bbox = d.multiline_textbbox((0, 0), text, font=font, align="center")
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    d.multiline_text(((W - tw) / 2, (H - th) / 2), text, font=font, fill="white", align="center")
    img.save(dest)
    return dest


def _load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont:
    if font_path:
        return ImageFont.truetype(font_path, size=size)
    # Fallback to a common default; user should set font_path for a real channel look.
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:
        return ImageFont.load_default()
