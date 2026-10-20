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

# Narwal room-type code -> label (the app labels rooms by type unless the user
# renamed them). Verified against the T10 (types 1/3/4 = Master Bedroom/Living
# Room/Kitchen on the test map); higher values match the app's room-name keys.
ROOM_TYPE_NAMES: dict[int, str] = {
    0: "Room", 1: "Master Bedroom", 2: "Second Bedroom", 3: "Living Room",
    4: "Kitchen", 5: "Bathroom", 6: "Toilet", 7: "Dining Room", 8: "Dining Room",
    9: "Balcony", 10: "Utility Room", 11: "Study", 12: "Nursery",
    13: "Recreation Room", 14: "Storage Room", 15: "Other",
}
# Room ids with these type codes are not cleanable rooms (forbidden/virtual areas).
_NON_ROOM_TYPES = {254, 255}


def _looks_numeric(s: Any) -> bool:
    try:
        int(str(s))
        return True
    except (TypeError, ValueError):
        return False


def parse_rooms(map_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return cleanable rooms as ``[{"room_id", "type", "name"}]`` from a map result.

    A room keeps its user-given name when set; otherwise it is labelled by type.
    Forbidden/virtual areas (type >= 254) are dropped.
    """
    ra = (map_result or {}).get("room_attr") or {}
    attrs = ra.get("attr") if isinstance(ra, dict) else None
    if not isinstance(attrs, list):
        return []
    rooms: list[dict[str, Any]] = []
    for a in attrs:
        if not isinstance(a, dict):
            continue
        rid = a.get("room_id")
        typ = a.get("type")
        if rid is None or (isinstance(typ, int) and (typ in _NON_ROOM_TYPES or typ >= 90)):
            continue
        name = a.get("name")
        label = name if (isinstance(name, str) and name.strip() and not _looks_numeric(name)) else None
        if not label:
            label = ROOM_TYPE_NAMES.get(typ, f"Room {rid}")
        rooms.append({"room_id": rid, "type": typ, "name": label})
    return rooms


def decode_layer(map_data: dict[str, Any]) -> tuple[int, int, list[int]]:
    """Return (width, height, flat room-id list) from a map_data dict."""
    w = int(map_data["width"])
    h = int(map_data["height"])
    raw = zlib.decompress(base64.b64decode(map_data["room_layer"])).decode("latin-1")
    layer = json.loads(raw)
    return w, h, layer


def _room_id_of(v: int) -> int | None:
    """Room id for a layer value. Each room is a single set bit (value == 1 << id).
    Pixels with more than one bit set are room boundaries (drawn as walls)."""
    if v <= 0 or v >= 256:
        return None
    if v & (v - 1):  # more than one bit set => boundary pixel
        return None
    return v.bit_length() - 1


def render_png(
    map_data: dict[str, Any], scale: int = 4, rooms: list[dict[str, Any]] | None = None
) -> bytes:
    """Render the map to PNG bytes, labelling rooms when ``rooms`` is given.

    Requires Pillow (bundled with Home Assistant).
    """
    from PIL import Image, ImageDraw, ImageFont

    w, h, layer = decode_layer(map_data)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    # Accumulate room-interior pixel centroids for labelling.
    cent: dict[int, list[int]] = {}
    for i, v in enumerate(layer):
        if not v:
            continue
        rid = _room_id_of(v)
        if rid is not None:
            col = ROOM_COLORS[rid % len(ROOM_COLORS)]
            acc = cent.setdefault(rid, [0, 0, 0])
            acc[0] += i % w
            acc[1] += i // w
            acc[2] += 1
        else:
            col = WALL
        px[i % w, i // w] = (col[0], col[1], col[2], 255)
    img = img.resize((w * scale, h * scale), Image.NEAREST)
    d = ImageDraw.Draw(img)

    # Room name labels at each room's centroid.
    if rooms:
        try:
            font = ImageFont.load_default()
        except Exception:  # noqa: BLE001
            font = None
        names = {r["room_id"]: r.get("name", "") for r in rooms}
        for rid, (sx, sy, n) in cent.items():
            if n < 30 or rid not in names:
                continue
            label = str(names[rid])
            cx, cy = sx / n * scale, sy / n * scale
            tw = d.textlength(label, font=font) if font else len(label) * 6
            d.rectangle([cx - tw / 2 - 3, cy - 8, cx + tw / 2 + 3, cy + 8], fill=(255, 255, 255, 220))
            d.text((cx - tw / 2, cy - 6), label, fill=(0, 0, 0), font=font)

    # Dock marker from world coordinates.
    try:
        res = float(map_data["resolution"])
        ox = float(map_data["origin_x"])
        oy = float(map_data["origin_y"])
        bx = map_data.get("base_station_x")
        by = map_data.get("base_station_y")
        if bx is not None and by is not None and res:
            dx = int((float(bx) - ox) / res * scale)
            dy = int((float(by) - oy) / res * scale)
            d.ellipse([dx - 9, dy - 9, dx + 9, dy + 9], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    except (KeyError, TypeError, ValueError):
        pass

    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
