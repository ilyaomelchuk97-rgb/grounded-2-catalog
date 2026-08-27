from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BASE = "https://grounded.wiki.gg"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Grounded2Catalog/1.0)"}
OUT = Path(__file__).with_name("data.js")


def get_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    return r.text


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def abs_img(src: str | None) -> str:
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return BASE + src
    return src


def first_item_anchor(td) -> str:
    # The first non-empty anchor in item cells is the item name; image links have no text.
    for a in td.find_all("a"):
        value = clean(a.get_text(" ", strip=True))
        if value and not value.lower().startswith("tier"):
            return value
    return clean(td.get_text(" ", strip=True)).split("\n")[0]


def item_img(td) -> str:
    img = td.find("img")
    return abs_img(img.get("src")) if img else ""


def tier_from(container) -> str:
    for img in container.find_all("img"):
        alt = clean(img.get("alt", ""))
        m = re.search(r"Tier\s*([0-9]+)", alt, re.I)
        if m:
            return m.group(1)
    return ""


def info_parts(info: str) -> tuple[str, str]:
    info = clean(info)
    quote = re.search(r"[\"“](.*?)[\"”]", info)
    effect = clean(quote.group(1)) if quote else ""
    unlock = ""
    m = re.search(r"(?:Unlocked by|Found|Location|Obtained by):\s*(.*)$", info, re.I)
    if m:
        unlock = clean(m.group(1))
    return effect, unlock


def weapon_data() -> list[dict[str, Any]]:
    soup = BeautifulSoup(get_html(BASE + "/wiki/Weapons_%26_Tools_(Grounded_2)"), "html.parser")
    tables = soup.find_all("table")[:14]
    groups = ["one-handed", "stranger-one-handed", "shield", "stranger-shield", "two-handed", "stranger-two-handed", "dual-wield", "stranger-dual-wield", "bow", "stranger-bow", "greatbow", "stranger-greatbow", "candy-staves", "turret-ammo"]
    out: list[dict[str, Any]] = []
    for table, group in zip(tables, groups):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if not tds:
                continue
            name = first_item_anchor(tds[0])
            if not name or name.lower() in {"tool", "damage"}:
                continue
            texts = [clean(td.get_text(" ", strip=True)) for td in tds]
            if len(texts) >= 8:
                # Bow and greatbow tables have one extra stat column.
                if len(texts) == 9:
                    stats = " • ".join([
                        f"Arrow damage: {texts[1]}" if texts[1] else "",
                        f"Bow multiplier: {texts[2]}" if texts[2] else "",
                        f"Stun: {texts[3]}" if texts[3] else "",
                        f"Speed: {texts[4]}" if texts[4] else "",
                        f"Crit: {texts[5]}" if texts[5] else "",
                    ])
                    info, materials, repair = texts[6], texts[7], texts[8]
                else:
                    stats = " • ".join([
                        f"Damage: {texts[1]}" if texts[1] else "",
                        f"Stun: {texts[2]}" if texts[2] else "",
                        f"Speed: {texts[3]}" if texts[3] else "",
                        f"Crit: {texts[4]}" if texts[4] else "",
                    ])
                    info, materials, repair = texts[5], texts[6], texts[7]
            elif len(texts) == 6:
                stats = f"Block reduction: {texts[1]} • Block stamina cost: {texts[2]}"
                info, materials, repair = texts[3], texts[4], texts[5]
            else:
                stats = " • ".join(texts[1:-2])
                info = texts[-2] if len(texts) >= 3 else ""
                materials = texts[-1] if len(texts) >= 2 else ""
                repair = ""
            effect, unlock = info_parts(info)
            if not effect:
                effect = info.split(" Unlocked by:")[0].strip().strip('"“”') if info else ""
            subtype = {
                "one-handed": "One-handed", "stranger-one-handed": "Stranger variant · one-handed",
                "shield": "Shield", "stranger-shield": "Stranger variant · shield",
                "two-handed": "Two-handed", "stranger-two-handed": "Stranger variant · two-handed",
                "dual-wield": "Dual wield", "stranger-dual-wield": "Stranger variant · dual wield",
                "bow": "Bow", "stranger-bow": "Stranger variant · bow",
                "greatbow": "Greatbow", "stranger-greatbow": "Stranger variant · greatbow",
                "candy-staves": "Candy staff", "turret-ammo": "Turret ammo",
            }[group]
            out.append({
                "id": f"weapon-{len(out)+1}", "name": name, "category": "weapon", "subtype": subtype,
                "tier": tier_from(tds[0]), "image": item_img(tds[0]), "stats": clean(stats.replace(" •  •", " • ")),
                "effect": effect, "recipe": materials, "repair": repair, "unlock": unlock, "info": info,
            })
    return out


def armor_data() -> list[dict[str, Any]]:
    soup = BeautifulSoup(get_html(BASE + "/wiki/Armor_(Grounded_2)"), "html.parser")
    tables = soup.find_all("table")
    out: list[dict[str, Any]] = []
    # Armor set tables contain a row with six cells: item, recipe, item, recipe, item, recipe.
    for table in tables:
        set_name = ""
        first = table.find("tr")
        if first and first.find("th"):
            set_name = clean(first.get_text(" ", strip=True))
            set_name = re.sub(r"\s+Tier\s*\d+", "", set_name, flags=re.I).strip()
        six = None
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) == 6 and clean(tds[0].get_text(" ", strip=True)) and "Recipe" in clean(tds[1].get_text(" ", strip=True)):
                six = tds
                break
        if six and set_name:
            # Find the compact stats/effects row in this set table.
            stats_text, piece_effect, sleek_effect, set_bonus, armor_class = "", "", "", "", ""
            rows = [tr.find_all(["th", "td"], recursive=False) for tr in table.find_all("tr")]
            small_effects = []
            for row in rows:
                vals = [clean(x.get_text(" ", strip=True)) for x in row]
                if len(vals) == 4 and vals[0] and re.search(r"Head.*Body|Head.*Legs", vals[0]):
                    stats_text = f"Defense: {vals[0]} • Resistance: {vals[1]}"
                # On the current wiki these rows collapse to one cell whose text begins with the effect name.
                if vals and vals[0] == "Set Bonus":
                    set_bonus = clean(" ".join(vals[1:]))
                if vals and vals[0] == "Class":
                    armor_class = clean(" ".join(vals[1:]))
                if len(vals) == 2 and vals[0] not in {"Set Bonus", "Class"}:
                    small_effects.append(vals)
            if small_effects:
                piece_effect = small_effects[0][0] + ": " + small_effects[0][1]
            if len(small_effects) > 1:
                sleek_effect = small_effects[1][0] + ": " + small_effects[1][1]
            for pos, slot in [(0, "Head"), (2, "Body"), (4, "Legs")]:
                cell = six[pos]
                recipe = clean(six[pos + 1].get_text(" ", strip=True)).replace("Recipe:", "", 1).strip()
                name = first_item_anchor(cell)
                if not name:
                    continue
                out.append({
                    "id": f"armor-{len(out)+1}", "name": name, "category": "armor", "subtype": slot,
                    "set": set_name.replace(" Armor", ""), "tier": tier_from(cell) or tier_from(first), "image": item_img(cell),
                    "stats": stats_text, "effect": piece_effect, "sleek": sleek_effect, "setBonus": set_bonus,
                    "class": armor_class, "recipe": recipe, "repair": "", "unlock": "",
                    "info": f"{set_name}. {armor_class}".strip(),
                })
        # Individual armor tables have seven columns and a header row beginning with Piece.
        header = table.find("tr")
        header_vals = [clean(x.get_text(" ", strip=True)) for x in header.find_all(["th", "td"], recursive=False)] if header else []
        if header_vals and header_vals[0] == "Piece" and len(header_vals) >= 6:
            for tr in table.find_all("tr")[1:]:
                tds = tr.find_all("td", recursive=False)
                if len(tds) < 6:
                    continue
                name = first_item_anchor(tds[0])
                if not name:
                    continue
                vals = [clean(td.get_text(" ", strip=True)) for td in tds]
                out.append({
                    "id": f"armor-{len(out)+1}", "name": name, "category": "armor", "subtype": "Individual",
                    "set": "Individual", "tier": tier_from(tds[0]), "image": item_img(tds[0]),
                    "stats": vals[3], "effect": vals[4], "sleek": vals[5] if len(vals) > 5 else "",
                    "setBonus": "", "class": vals[6] if len(vals) > 6 else "", "recipe": vals[1],
                    "repair": vals[2], "unlock": "", "info": vals[1],
                })
    return out


def trinket_data() -> list[dict[str, Any]]:
    soup = BeautifulSoup(get_html(BASE + "/wiki/Trinkets_(Grounded_2)"), "html.parser")
    out: list[dict[str, Any]] = []
    groups = ["Crafted", "Creature drop", "Resource drop", "Unique", "Ominent token", "Stranger"]
    for table, group in zip(soup.find_all("table")[:6], groups):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if not tds:
                continue
            name = first_item_anchor(tds[0])
            if not name or name.lower() == "trinket":
                continue
            vals = [clean(td.get_text(" ", strip=True)) for td in tds]
            info = vals[1] if len(vals) > 1 else ""
            effect, unlock = info_parts(info)
            # Crafted: materials in cell 2 and perks in cell 3. Stranger rows have 5 cells.
            if len(vals) >= 5:
                recipe, perks = vals[-2], vals[-1]
                source = vals[2]
            else:
                recipe = vals[2] if group == "Crafted" and len(vals) > 2 else ""
                source = vals[2] if group != "Crafted" and len(vals) > 2 else ""
                perks = vals[3] if len(vals) > 3 else ""
            out.append({
                "id": f"trinket-{len(out)+1}", "name": name, "category": "trinket", "subtype": group,
                "tier": tier_from(tds[0]), "image": item_img(tds[0]), "stats": "Passive accessory",
                "effect": perks or effect, "recipe": recipe, "repair": "", "unlock": unlock or source,
                "info": info, "source": source,
            })
    return out


def building_subtype(name: str, table_index: int) -> str:
    n = name.lower()
    if any(k in n for k in ["roof", "awning", "dome", "gable"]):
        return "Roofs"
    if any(k in n for k in ["wall", "door", "partition", "fence", "railing", "palisade"]):
        return "Walls & doors"
    if any(k in n for k in ["floor", "foundation", "path", "ramp", "stairs", "scaffold", "pillar"]):
        return "Floors & foundations"
    if table_index in {0, 3, 4}:
        return "Decorations & utilities"
    return "Structures"


def building_data() -> list[dict[str, Any]]:
    url = "https://www.destructoid.com/all-construction-recipes-in-grounded-2/"
    soup = BeautifulSoup(get_html(url), "html.parser")
    out: list[dict[str, Any]] = []
    # The article has five recipe tables; avoid unrelated tables in the article shell.
    tables = soup.find_all("table")[:5]
    for ti, table in enumerate(tables):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 2:
                continue
            name = clean(tds[0].get_text(" ", strip=True))
            recipe = clean(tds[1].get_text(" ", strip=True))
            if not name or name.lower() in {"construction item", "recipe"}:
                continue
            out.append({
                "id": f"building-{len(out)+1}", "name": name, "category": "building",
                "subtype": building_subtype(name, ti), "tier": "", "image": guessed_building_image(name), "stats": "Build piece",
                "effect": "", "recipe": recipe, "repair": "", "unlock": "",
                "info": f"Construction recipe · {building_subtype(name, ti)}",
            })
    return out


def resource_data() -> list[dict[str, Any]]:
    soup = BeautifulSoup(get_html(BASE + "/wiki/Resources_(Grounded_2)"), "html.parser")
    out: list[dict[str, Any]] = []
    tables = soup.find_all("table")[:15]
    for ti, table in enumerate(tables):
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 2:
                continue
            name = first_item_anchor(tds[0])
            if not name or name.lower() in {"resource", "resources"}:
                continue
            vals = [clean(td.get_text(" ", strip=True)) for td in tds]
            description = vals[1] if len(vals) > 1 else ""
            source = vals[2] if len(vals) > 2 else ""
            locations = vals[3] if len(vals) > 3 else ""
            out.append({
                "id": f"resource-{len(out)+1}", "name": name, "category": "resource",
                "subtype": "Upgrade material" if ti < 5 else "Natural resource", "tier": tier_from(tds[0]),
                "image": item_img(tds[0]), "stats": "Crafting material", "effect": description,
                "recipe": source if ti < 5 else "", "repair": "", "unlock": locations,
                "info": description, "source": source,
            })
    return out


def recipe_segments(recipe: str) -> list[tuple[str, int]]:
    """Read both recipe formats used by the sources: `4 Material` and `Material (4)`."""
    recipe = clean(recipe).replace("Recipe:", "", 1).strip()
    result: list[tuple[str, int]] = []
    for match in re.finditer(r"([^()]+?)\s*\((\d+)\)", recipe):
        name = clean(match.group(1)).strip(" ·,")
        if name:
            result.append((name, int(match.group(2))))
    for match in re.finditer(r"(?<!\w)(\d+)\s*x?\s+(.+?)(?=\s+\d+\s*x?\s+|$)", recipe):
        name = clean(match.group(2)).strip(" ·,")
        if name and not name.isdigit():
            result.append((name, int(match.group(1))))
    return result


def guessed_resource_image(name: str) -> str:
    """A stable MediaWiki file URL for recipe-only resources absent from the main table."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return f"{BASE}/wiki/Special:FilePath/{quote(slug + '.png')}?width=50"


def guessed_building_image(name: str) -> str:
    """Construction pieces use the same item icon naming convention on the wiki."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    encoded = quote(slug, safe="_")
    return f"{BASE}/images/thumb/{encoded}.png/100px-{encoded}.png"


def add_recipe_only_resources(items: list[dict[str, Any]]) -> None:
    known = {item["name"] for item in items}
    missing: list[str] = []
    for item in items:
        for name, _qty in recipe_segments(item.get("recipe", "")):
            # The recipe parser may capture a malformed joined token; keep only plausible resource names.
            if name not in known and 1 < len(name) < 70 and not any(ch.isdigit() for ch in name):
                if name not in missing:
                    missing.append(name)
    for name in missing:
        items.append({
            "id": f"resource-recipe-{len(items)+1}", "name": name, "category": "resource",
            "subtype": "Crafting material", "tier": "", "image": guessed_resource_image(name),
            "stats": "Crafting material", "effect": "Resource used in crafting recipes.",
            "recipe": "", "repair": "", "unlock": "", "info": "Resource used in crafting recipes.",
        })


def attach_ingredients(items: list[dict[str, Any]]) -> None:
    """Add structured recipe ingredients so the UI can show a thumbnail per resource."""
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        # Prefer an entry with an actual image when names are repeated.
        if item["name"] not in lookup or (not lookup[item["name"]].get("image") and item.get("image")):
            lookup[item["name"]] = item
    known = sorted(lookup, key=len, reverse=True)
    for item in items:
        recipe = clean(item.get("recipe", "")).replace("Recipe:", "", 1).strip()
        found: list[tuple[int, int, str, int]] = []
        # Building recipes use the form "Material (4)".
        for name in known:
            for match in re.finditer(re.escape(name) + r"\s*\((\d+)\)", recipe, flags=re.I):
                found.append((match.start(), match.end(), name, int(match.group(1))))
        # Equipment recipes use the form "4 Material" or "4x Material".
        for match in re.finditer(r"(?<!\w)(\d+)\s*x?\s+", recipe):
            start = match.end()
            for name in known:
                if recipe[start:start + len(name)].lower() == name.lower():
                    found.append((match.start(), start + len(name), name, int(match.group(1))))
                    break
        found.sort(key=lambda value: value[0])
        clean_found = []
        used_positions = set()
        for start, end, name, qty in found:
            if start in used_positions:
                continue
            used_positions.add(start)
            ing = lookup[name]
            clean_found.append({"name": name, "qty": qty, "image": ing.get("image", ""), "category": ing.get("category", "")})
        # Fallback for recipes where a source omitted a separator: still show each known resource.
        if not clean_found:
            for name, qty in recipe_segments(recipe):
                if name in lookup:
                    ing = lookup[name]
                    clean_found.append({"name": name, "qty": qty, "image": ing.get("image", ""), "category": ing.get("category", "")})
        item["ingredients"] = clean_found


def main() -> None:
    data = weapon_data() + armor_data() + trinket_data() + building_data() + resource_data()
    # Preserve first occurrence if the source repeats a row.
    seen = set()
    unique = []
    for item in data:
        key = (item["category"], item["name"], item.get("subtype", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    add_recipe_only_resources(unique)
    attach_ingredients(unique)
    payload = {
        "updated": "2026-08-27",
        "sources": [
            {"label": "Grounded Wiki · Weapons & Tools", "url": BASE + "/wiki/Weapons_%26_Tools_(Grounded_2)"},
            {"label": "Grounded Wiki · Armor", "url": BASE + "/wiki/Armor_(Grounded_2)"},
            {"label": "Grounded Wiki · Trinkets", "url": BASE + "/wiki/Trinkets_(Grounded_2)"},
            {"label": "Destructoid · Construction recipes", "url": "https://www.destructoid.com/all-construction-recipes-in-grounded-2/"},
            {"label": "Grounded Wiki · Resources", "url": BASE + "/wiki/Resources_(Grounded_2)"},
        ],
        "items": unique,
    }
    OUT.write_text("window.GROUNDED_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    from collections import Counter
    print("Generated", len(unique), "items", Counter(x["category"] for x in unique))


if __name__ == "__main__":
    main()
