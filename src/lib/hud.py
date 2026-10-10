"""Glass look for the arcade replay windows: carbon backdrop, translucent rounded panels, F1 red accents.

Panels are built once as GPU shape lists and reused while their geometry stays the same,
so drawing them every frame costs a single draw call each.
"""

import math
from collections import OrderedDict

import arcade
import numpy as np
from PIL import Image

from src.lib.fonts import display_font_family

F1_RED = (225, 6, 0)
TEXT = (242, 243, 245)
TEXT_DIM = (176, 180, 192)
TEXT_FAINT = (136, 140, 152)
PANEL_FILL = (255, 255, 255, 15)
PANEL_BORDER = (255, 255, 255, 28)
PANEL_HIGHLIGHT = (255, 255, 255, 7)
CONTROL_FILL = (255, 255, 255, 22)
CONTROL_BORDER = (255, 255, 255, 40)
GREEN = (46, 204, 113)
AMBER = (255, 176, 32)

DISPLAY_FONT = (display_font_family(), "calibri", "arial")

_SHAPE_CACHE = OrderedDict()
_SHAPE_CACHE_SIZE = 512
_BACKDROP = None
_FLAGS = {}


def _rounded_points(left, bottom, width, height, radius, segments=6):
    radius = max(0.0, min(radius, width / 2, height / 2))
    right, top = left + width, bottom + height
    corners = (
        (right - radius, top - radius, 0),
        (left + radius, top - radius, 90),
        (left + radius, bottom + radius, 180),
        (right - radius, bottom + radius, 270),
    )
    points = []
    for cx, cy, start in corners:
        for i in range(segments + 1):
            angle = math.radians(start + 90 * i / segments)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def cached_shapes(key, build):
    """ShapeElementList built by `build()` (an iterable of shapes), reused while `key` is unchanged."""
    shapes = _SHAPE_CACHE.get(key)
    if shapes is None:
        shapes = arcade.shape_list.ShapeElementList()
        for shape in build():
            shapes.append(shape)
        _SHAPE_CACHE[key] = shapes
        if len(_SHAPE_CACHE) > _SHAPE_CACHE_SIZE:
            _SHAPE_CACHE.popitem(last=False)
    else:
        _SHAPE_CACHE.move_to_end(key)
    return shapes


def draw_panel(left, bottom, width, height, radius=14, fill=PANEL_FILL, border=PANEL_BORDER, accent=None):
    """Rounded translucent panel. `accent` adds a thin coloured bar along the top edge."""
    left, bottom, width, height = round(left), round(bottom), round(width), round(height)
    key = ("panel", left, bottom, width, height, radius, tuple(fill), tuple(border or ()), tuple(accent or ()))

    def build():
        points = _rounded_points(left, bottom, width, height, radius)
        yield arcade.shape_list.create_polygon(points, fill)
        # Soft top sheen so the panel reads as glass rather than a flat box
        sheen_h = min(height / 2, 26)
        yield arcade.shape_list.create_polygon(
            _rounded_points(left + 1, bottom + height - sheen_h - 1, width - 2, sheen_h, max(0, radius - 1)),
            PANEL_HIGHLIGHT,
        )
        if accent:
            yield arcade.shape_list.create_rectangle_filled(left + width / 2, bottom + height - 1.5, width - 2 * radius, 3, accent)
        if border:
            yield arcade.shape_list.create_line_loop(points, border, 1)

    cached_shapes(key, build).draw()


def draw_pill(cx, cy, width, height, fill=CONTROL_FILL, border=CONTROL_BORDER):
    draw_panel(cx - width / 2, cy - height / 2, width, height, radius=height / 2, fill=fill, border=border)


def draw_section_title(text, x, y, color=TEXT_FAINT, size=10, **kwargs):
    """Small upper-case caption above a value or at the top of a panel."""
    from src.ui_components import cached_text

    kwargs.setdefault("anchor_y", "top")
    cached_text(text, round(x), round(y), color, size, bold=True, **kwargs).draw()


def _backdrop_texture():
    """Carbon gradient with soft red light (same recipe as the Qt Backdrop), rendered once."""
    global _BACKDROP
    if _BACKDROP is None:
        w, h = 480, 270
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        u, v = xs / w, ys / h  # v=0 is the top of the image
        t = (u + v) / 2
        base = np.array([0x16, 0x18, 0x1F], np.float32) * (1 - t)[..., None] + np.array([0x0B, 0x0C, 0x10], np.float32) * t[..., None]
        img = base
        for cx, cy, radius, color, alpha in (
            (0.08, 0.0, 0.75, (225, 6, 0), 70),
            (0.95, 1.0, 0.65, (255, 70, 40), 34),
            (0.60, 0.35, 0.45, (90, 110, 160), 22),
        ):
            d = np.sqrt(((u - cx) * w) ** 2 + ((v - cy) * h) ** 2) / (radius * max(w, h))
            a = (np.clip(1 - d, 0, 1) * alpha / 255.0)[..., None]
            img = img * (1 - a) + np.array(color, np.float32) * a
        image = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        _BACKDROP = arcade.Texture(image, hash="f1-glass-backdrop")
    return _BACKDROP


def draw_backdrop(window):
    arcade.draw_texture_rect(_backdrop_texture(), arcade.LBWH(0, 0, window.width, window.height))


def flag_texture(country, width=27, height=18, radius=3):
    """Country flag with rounded corners as a texture, or None when there is no flag for it.

    The flag files are SVG, which arcade can't load, so they are rasterised once with Qt's SVG renderer.
    """
    key = (str(country or "").lower(), width, height, radius)
    if key not in _FLAGS:
        _FLAGS[key] = _render_flag(country, width, height, radius)
    return _FLAGS[key]


def _render_flag(country, width, height, radius):
    from src.lib.flags import flag_path

    path = flag_path(country)
    if path is None:
        return None
    try:
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QImage, QPainter, QPainterPath
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:
        return None

    scale = 2  # render at 2x so it stays sharp when scaled down
    w, h = width * scale, height * scale
    image = QImage(w, h, QImage.Format_RGBA8888)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), radius * scale, radius * scale)
    painter.setClipPath(clip)
    QSvgRenderer(path).render(painter, QRectF(0, 0, w, h))
    painter.end()
    pil = Image.frombuffer("RGBA", (w, h), bytes(image.constBits()), "raw", "RGBA", image.bytesPerLine(), 1)
    return arcade.Texture(pil.copy(), hash=f"flag-{path}-{width}x{height}")
