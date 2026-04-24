"""Build a photo collage from a list of JPEG thumbnails using Pillow."""
import io
import math
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

TILE_W = 480
TILE_H = 270
GAP = 4
HEADER_H = 52
BG = (15, 23, 42)       # dark navy
TEXT_COLOR = (255, 255, 255)


def _grid_dims(n: int) -> Tuple[int, int]:
    if n <= 3:
        return n, 1
    if n <= 6:
        return 3, 2
    return 3, 3


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_collage(thumbnails: List[Tuple[str, bytes]], title: str = "") -> bytes:
    """Compose thumbnails into a grid image and return JPEG bytes.

    thumbnails: list of (headline, jpeg_bytes)
    title: optional header text
    """
    if not thumbnails:
        raise ValueError("No thumbnails to build collage")

    cols, rows = _grid_dims(len(thumbnails))
    canvas_w = cols * TILE_W + (cols - 1) * GAP
    canvas_h = HEADER_H + rows * TILE_H + (rows - 1) * GAP

    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)

    # Header
    font = _load_font(22)
    draw.text((canvas_w // 2, HEADER_H // 2), title, fill=TEXT_COLOR, font=font, anchor="mm")

    # Tiles
    for idx, (headline, img_bytes) in enumerate(thumbnails):
        col = idx % cols
        row = idx // cols
        x = col * (TILE_W + GAP)
        y = HEADER_H + row * (TILE_H + GAP)
        try:
            tile = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            tile = tile.resize((TILE_W, TILE_H), Image.LANCZOS)
        except Exception:
            tile = Image.new("RGB", (TILE_W, TILE_H), (30, 30, 50))
        canvas.paste(tile, (x, y))

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()
