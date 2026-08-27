from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.js"
ASSET_DIR = ROOT / "assets" / "catalog"
PREFIX = "window.GROUNDED_DATA = "


def read_data() -> dict:
    raw = DATA_FILE.read_text(encoding="utf-8").strip()
    raw = raw[len(PREFIX):].rstrip(";\n")
    return json.loads(raw)


def palette(item: dict) -> tuple[str, str]:
    name = item.get("name", "").lower()
    if item.get("category") == "building":
        if any(word in name for word in ("grass", "clover")):
            return "#5f8d58", "#d9ef9c"
        if any(word in name for word in ("stem", "pine", "thatch", "palisade")):
            return "#8b633d", "#f2c98b"
        if any(word in name for word in ("clay", "brick", "pumpkin", "mushroom")):
            return "#a6634c", "#ffd3a5"
        if any(word in name for word in ("pebble", "stone", "foundation")):
            return "#60768a", "#dcecf7"
        if any(word in name for word in ("crow", "feather", "scale")):
            return "#415f86", "#bcd7ff"
        return "#496e7a", "#c8eef3"
    if any(word in name for word in ("mint", "dew", "water", "ice", "chill")):
        return "#327da1", "#b6eff7"
    if any(word in name for word in ("spicy", "sizzle", "burn", "coal", "ash")):
        return "#914f45", "#ffc08d"
    if any(word in name for word in ("berry", "blueberry", "lingonberry", "candy", "gum", "glob")):
        return "#6a548e", "#e0c5ff"
    if any(word in name for word in ("grass", "clover", "plant", "leaf", "fiber")):
        return "#4d8064", "#d7f1a0"
    return "#456780", "#d5e8f5"


def short_label(item: dict) -> str:
    name = item.get("name", "").lower()
    if item.get("category") == "building":
        if "wall" in name or "partition" in name or "palisade" in name:
            return "СТЕНА"
        if "floor" in name or "foundation" in name or "path" in name:
            return "ПОЛ"
        if any(word in name for word in ("roof", "awning", "dome", "gable")):
            return "КРЫША"
        if "door" in name or "gate" in name:
            return "ДВЕРЬ"
        if "stair" in name or "ramp" in name:
            return "ЛЕСТНИЦА"
        return "ДЕКОР"
    return "РЕСУРС"


def building_shape(item: dict, accent: str) -> str:
    name = item.get("name", "").lower()
    if "wall" in name or "partition" in name or "palisade" in name:
        return f'<rect x="64" y="54" width="112" height="112" rx="8" fill="{accent}" opacity=".82"/><path d="M64 91h112M64 128h112M101 54v112M139 54v112" stroke="#132536" stroke-width="6" opacity=".55"/>'
    if any(word in name for word in ("roof", "awning", "dome", "gable")):
        return f'<path d="M43 151L118 53l79 98z" fill="{accent}" opacity=".9"/><path d="M64 145h108M79 125h78M96 103h45" stroke="#132536" stroke-width="7" opacity=".55"/>'
    if "floor" in name or "foundation" in name or "path" in name:
        return f'<path d="M45 89l75-30 75 30-75 30zM45 89v67l75 31 75-31V89l-75 30z" fill="{accent}" opacity=".88"/><path d="M120 119v68M45 89l75 30 75-30" stroke="#132536" stroke-width="6" opacity=".55"/>'
    if "door" in name or "gate" in name:
        return f'<rect x="64" y="47" width="112" height="132" rx="7" fill="{accent}" opacity=".88"/><path d="M92 179V97c0-16 12-28 28-28s28 12 28 28v82" fill="#132536" opacity=".7"/><circle cx="139" cy="137" r="5" fill="#fff"/>'
    if "stair" in name or "ramp" in name:
        return f'<path d="M48 170h34v-27h30v-27h30V89h30v81z" fill="{accent}" opacity=".88"/><path d="M48 170h154M82 143h120M112 116h90M142 89h60" stroke="#132536" stroke-width="6" opacity=".55"/>'
    return f'<rect x="58" y="72" width="124" height="93" rx="14" fill="{accent}" opacity=".86"/><circle cx="120" cy="112" r="21" fill="#132536" opacity=".65"/><path d="M120 91v42M99 112h42" stroke="#fff" stroke-width="6" opacity=".72"/>'


def resource_shape(item: dict, accent: str) -> str:
    name = item.get("name", "").lower()
    if any(word in name for word in ("fiber", "leaf", "grass", "clover", "needle", "fuzz", "fluff")):
        return f'<path d="M120 174C83 147 69 107 90 67c41 4 61 34 30 107z" fill="{accent}" opacity=".9"/><path d="M89 151c19-29 29-55 31-82" stroke="#132536" stroke-width="7" opacity=".6"/>'
    if any(word in name for word in ("leather", "hide", "rope", "cloth", "pelt")):
        return f'<path d="M76 69h88l18 27-18 67H76l-18-67z" fill="{accent}" opacity=".9"/><path d="M78 88h84M72 119h96" stroke="#132536" stroke-width="7" opacity=".55"/>'
    if any(word in name for word in ("shell", "chunk", "part", "stone", "shard", "quartz", "brick", "pebble")):
        return f'<path d="M68 143l12-66 48-20 51 37-14 64-55 19z" fill="{accent}" opacity=".9"/><path d="M80 77l45 39 54-22M125 116l-15 61" stroke="#132536" stroke-width="7" opacity=".55"/>'
    if any(word in name for word in ("meat", "bite", "roast", "jerky", "gland", "venom", "fang", "horn")):
        return f'<path d="M73 134c9-43 42-67 91-62 20 24 16 60-10 83-34 16-65 9-81-21z" fill="{accent}" opacity=".9"/><circle cx="110" cy="115" r="7" fill="#fff" opacity=".8"/><circle cx="143" cy="138" r="7" fill="#fff" opacity=".8"/>'
    return f'<circle cx="120" cy="120" r="58" fill="{accent}" opacity=".9"/><circle cx="103" cy="100" r="13" fill="#fff" opacity=".7"/><path d="M80 143c27 20 55 20 81 0" fill="none" stroke="#132536" stroke-width="8" opacity=".55"/>'


def svg_for(item: dict) -> str:
    bg, accent = palette(item)
    label = short_label(item)
    shape = building_shape(item, accent) if item.get("category") == "building" else resource_shape(item, accent)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="#142b41"/></linearGradient></defs>
<rect width="240" height="240" rx="34" fill="url(#g)"/><circle cx="42" cy="42" r="34" fill="#fff" opacity=".05"/><circle cx="200" cy="194" r="68" fill="#fff" opacity=".04"/>
{shape}<text x="120" y="211" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" letter-spacing="2" fill="#fff" opacity=".9">{label}</text></svg>'''


def main() -> None:
    data = read_data()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    by_name = {item["name"]: item for item in data["items"]}
    count = 0
    for item in data["items"]:
        if item.get("category") not in {"building", "resource"}:
            continue
        relative = f"assets/catalog/{item['id']}.svg"
        item["image"] = relative
        (ROOT / relative).write_text(svg_for(item), encoding="utf-8")
        count += 1
    for item in data["items"]:
        for ingredient in item.get("ingredients", []):
            source = by_name.get(ingredient.get("name"))
            if source and source.get("category") in {"building", "resource"}:
                ingredient["image"] = source["image"]
    DATA_FILE.write_text(PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Created {count} local catalog images in {ASSET_DIR}")


if __name__ == "__main__":
    main()
