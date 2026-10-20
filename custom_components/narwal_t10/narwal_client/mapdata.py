"""Decode and render the Narwal T10 cloud map.

``GET /robot/pita/map`` returns ``map_data`` with a zlib+base64 ``room_layer``:
a flat width*height array (row-major) of room ids (0 = outside/unknown, small
ints = rooms, >=90 = walls/doorways). This renders it to a PNG.
"""

from __future__ import annotations

import base64
import json
import zlib
from typing import Any

# Calm categorical palette; room id picks an entry.
ROOM_COLORS = [
    (0xBF, 0xDB, 0xFE), (0xA7, 0xF3, 0xD0), (0xFD, 0xE6, 0x8A), (0xFD, 0xBA, 0x74),
    (0xF9, 0xA8, 0xD4), (0xC4, 0xB5, 0xFD), (0x93, 0xC5, 0xFD), (0x6E, 0xE7, 0xB7),
    (0xFC, 0xD3, 0x4D), (0xFB, 0x92, 0x3C),
]
WALL = (0x37, 0x41, 0x51)


def decode_layer(map_data: dict[str, Any]) -> tuple[int, int, list[int]]:
    """Return (width, height, flat room-id list) from a map_data dict."""
    w = int(map_data["width"])
    h = int(map_data["height"])
    raw = zlib.decompress(base64.b64decode(map_data["room_layer"])).decode("latin-1")
    layer = json.loads(raw)
    return w, h, layer


def render_png(map_data: dict[str, Any], scale: int = 4) -> bytes:
    """Render the map to PNG bytes. Requires Pillow (bundled with Home Assistant)."""
    from PIL import Image, ImageDraw

    w, h, layer = decode_layer(map_data)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for i, v in enumerate(layer):
        if not v:
            continue
        col = WALL if v >= 90 else ROOM_COLORS[(v - 1) % len(ROOM_COLORS)]
        px[i % w, i // w] = (col[0], col[1], col[2], 255)
    img = img.resize((w * scale, h * scale), Image.NEAREST)

    # Dock marker from world coordinates.
    try:
        res = float(map_data["resolution"])
        ox = float(map_data["origin_x"])
        oy = float(map_data["origin_y"])
        bx = map_data.get("base_station_x")
        by = map_data.get("base_station_y")
        if bx is not None and by is not None and res:
            d = ImageDraw.Draw(img)
            dx = int((float(bx) - ox) / res * scale)
            dy = int((float(by) - oy) / res * scale)
            d.ellipse([dx - 9, dy - 9, dx + 9, dy + 9], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    except (KeyError, TypeError, ValueError):
        pass

    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
