#!/usr/bin/env python3
"""Generate PNG link-preview assets. iMessage/Safari ignore SVG for og:image — PNG is required."""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

C0 = (24, 24, 27)
C1 = (63, 63, 70)
TEXT = (244, 244, 245)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def diagonal_gradient(size: tuple[int, int]) -> Image.Image:
    w, h = size
    im = Image.new("RGB", size)
    px = im.load()
    wm, hm = max(w - 1, 1), max(h - 1, 1)
    for y in range(h):
        for x in range(w):
            t = (x / wm + y / hm) / 2.0
            px[x, y] = _lerp(C0, C1, t)
    return im


def rounded_tile_rgba(size: int) -> Image.Image:
    """Rounded square tile with transparent pixels outside the radius (for clean paste on OG bg)."""
    base = diagonal_gradient((size, size)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    r = max(1, int(size * 9 / 32))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=255)
    base.putalpha(mask)
    return base


def _serif_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_r_dot(im: Image.Image, tile_px: int) -> None:
    tile = rounded_tile_rgba(tile_px)
    w, h = im.size
    x0 = (w - tile_px) // 2
    y0 = (h - tile_px) // 2
    im.paste(tile, (x0, y0), tile)
    dr = ImageDraw.Draw(im)
    stroke_w = max(1, tile_px // 32)
    r = max(1, int(tile_px * 9 / 32))
    dr.rounded_rectangle(
        (x0, y0, x0 + tile_px - 1, y0 + tile_px - 1),
        radius=r,
        outline=(63, 63, 70),
        width=stroke_w,
    )
    font_size = max(10, int(tile_px * 13 / 32))
    font = _serif_font(font_size)
    cx, cy = x0 + tile_px // 2, y0 + tile_px // 2
    try:
        dr.text((cx, cy), "r.", font=font, fill=TEXT, anchor="mm")
    except Exception:
        bbox = dr.textbbox((0, 0), "r.", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        dr.text((cx - tw // 2, cy - th // 2 - bbox[1]), "r.", font=font, fill=TEXT)


def write_apple_touch() -> None:
    """180×180 PNG for apple-touch-icon (iOS / some link previews)."""
    size = 180
    im = Image.new("RGB", (size, size), C0)
    draw_r_dot(im, tile_px=168)
    out = PUBLIC / "apple-touch-icon.png"
    im.save(out, "PNG", optimize=True)
    print(f"Wrote {out}")


def write_og_image() -> None:
    """1200×630 PNG — large r. tile; messengers want raster og:image."""
    w, h = 1200, 630
    bg = diagonal_gradient((w, h))
    # Slightly richer background (match prior SVG stops loosely)
    im = bg.copy()
    tile_px = 340
    draw_r_dot(im, tile_px=tile_px)
    out = PUBLIC / "og-image.png"
    im.save(out, "PNG", optimize=True)
    print(f"Wrote {out}")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    write_apple_touch()
    write_og_image()


if __name__ == "__main__":
    main()
