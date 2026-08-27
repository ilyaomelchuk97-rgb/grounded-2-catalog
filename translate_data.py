from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from deep_translator import GoogleTranslator

# deep-translator does not set a request timeout; add one so one bad text cannot block a build forever.
_original_get = requests.get

def _get_with_timeout(*args, **kwargs):
    kwargs.setdefault("timeout", 12)
    return _original_get(*args, **kwargs)

requests.get = _get_with_timeout

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.js"
PREFIX = "window.GROUNDED_DATA = "
# Only fields rendered by the interface are translated. Recipes are rendered from structured ingredients.
FIELDS = ["name", "set", "stats", "effect", "sleek", "setBonus", "class", "unlock", "source", "repair"]


def read_data() -> dict:
    raw = DATA_FILE.read_text(encoding="utf-8").strip()
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX):]
    if raw.endswith(";"):
        raw = raw[:-1]
    return json.loads(raw)


def fallback(text: str) -> str:
    # A small offline fallback for a future refresh when Google Translate is unavailable.
    pairs = {
        "Damage": "Урон", "Stun": "Оглушение", "Speed": "Скорость", "Crit": "Критический удар",
        "Fast": "Быстро", "Average": "Средне", "Slow": "Медленно", "Block reduction": "Снижение урона при блоке",
        "Block stamina cost": "Расход выносливости на блок", "Crafting material": "Материал для крафта",
        "Resource used in crafting recipes.": "Ресурс используется в рецептах крафта.",
        "Passive accessory": "Пассивный аксессуар", "Build piece": "Деталь строительства",
    }
    return pairs.get(text, text)


def translate_all(strings: list[str]) -> dict[str, str]:
    unique = list(dict.fromkeys(s for s in strings if s))
    cache_file = ROOT / "translation_cache.json"
    result: dict[str, str] = {}
    if cache_file.exists():
        try:
            result.update(json.loads(cache_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    pending = [value for value in unique if value not in result]
    translator = GoogleTranslator(source="en", target="ru")
    for index, value in enumerate(pending, start=1):
        try:
            translated = translator.translate(value)
            result[value] = (translated or fallback(value)).strip()
        except Exception as exc:
            print(f"Fallback for item {index}/{len(pending)}: {type(exc).__name__}", flush=True)
            result[value] = fallback(value)
        if index % 25 == 0 or index == len(pending):
            cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            print(f"Translated {len(result)}/{len(unique)}", flush=True)
    if cache_file.exists():
        cache_file.unlink()
    return result


def main() -> None:
    data = read_data()
    strings = []
    for item in data["items"]:
        for field in FIELDS:
            if item.get(field):
                strings.append(str(item[field]))
        for ingredient in item.get("ingredients", []):
            strings.append(str(ingredient.get("name", "")))
    translations = translate_all(strings)
    for item in data["items"]:
        for field in FIELDS:
            if item.get(field):
                item[f"{field}Ru"] = translations.get(str(item[field]), fallback(str(item[field])))
        item["nameRu"] = translations.get(item["name"], item["name"])
        if item.get("set"):
            item["setRu"] = translations.get(item["set"], item["set"])
        for ingredient in item.get("ingredients", []):
            ingredient["nameRu"] = translations.get(ingredient["name"], ingredient["name"])
    DATA_FILE.write_text(PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Russian localization added to {len(data['items'])} items")


if __name__ == "__main__":
    main()
