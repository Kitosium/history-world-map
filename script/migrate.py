#!/usr/bin/env python3
"""Apply identifier migrations and merges declared in data/aliases/entity-aliases.json.

This is deliberately a small, auditable step:

* ``entity_id_migrations`` renames an entity file and keeps the old identifier as
  an alias.
* ``entity_id_merges`` folds a duplicate entity into the canonical one, merging
  names, descriptions, sources and the observed time range.

The script is idempotent: running it again after the migration is a no-op.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DATA_DIR,
    ENTITIES_DIR,
    TODAY,
    entity_path,
    load_alias_config,
    load_entities,
    read_json,
    write_json,
)


def _merge_unique(*values: Iterable[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for value in values:
        for item in value or []:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else item
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def _merge_language_maps(*maps: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for mapping in maps:
        for key, value in (mapping or {}).items():
            if value in (None, "", [], {}):
                continue
            if key not in out or not out[key]:
                out[key] = value
    return out


def _merge_alias_lists(*maps: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for mapping in maps:
        for key, values in (mapping or {}).items():
            out.setdefault(key, [])
            for value in values or []:
                if value and value not in out[key]:
                    out[key].append(value)
    return out


def _range(doc: Dict[str, Any]) -> tuple:
    existence = doc.get("existence", {}) or {}
    return (
        existence.get("from", {}).get("year", 2026),
        existence.get("to", {}).get("year", 2026),
        existence,
    )


def merge_documents(target: Dict[str, Any], source: Dict[str, Any], old_id: str) -> Dict[str, Any]:
    """Merge *source* into *target* without inventing new facts."""
    target = json.loads(json.dumps(target))  # deep copy
    target_names = target.setdefault("names", {})
    source_names = source.get("names", {}) or {}
    target_names["canonical"] = _merge_language_maps(
        target_names.get("canonical", {}), source_names.get("canonical", {})
    )
    target_names["aliases"] = _merge_alias_lists(
        target_names.get("aliases", {}), source_names.get("aliases", {})
    )
    old_name = (source_names.get("canonical", {}) or {}).get("en") or old_id
    aliases = target_names.setdefault("aliases", {})
    for lang in {"en", "vi"}:
        aliases.setdefault(lang, [])
        if old_name not in aliases[lang]:
            aliases[lang].append(old_name)
        if old_id not in aliases[lang]:
            aliases[lang].append(old_id)

    target["descriptions"] = _merge_language_maps(
        target.get("descriptions", {}), source.get("descriptions", {})
    )

    t_from, t_to, t_ex = _range(target)
    s_from, s_to, s_ex = _range(source)
    from_year = min(t_from, s_from)
    to_year = max(t_to, s_to)
    target["existence"] = t_ex
    t_ex["from"] = {"year": from_year, "year_system": "astronomical", "precision": "year", "label": f"{abs(from_year)} {'TCN' if from_year < 0 else 'SCN'}"}
    t_ex["to"] = {"year": to_year, "year_system": "astronomical", "precision": "year", "label": f"{abs(to_year)} {'TCN' if to_year < 0 else 'SCN'}"}
    t_ex["duration_years"] = max(0, to_year - from_year)
    t_ex["status"] = "active" if to_year >= 2026 else t_ex.get("status", "historical")

    target["source_ids"] = _merge_unique(target.get("source_ids", []), source.get("source_ids", []))
    target["observed_periods"] = sorted(
        set(target.get("observed_periods", []) or []) | set(source.get("observed_periods", []) or [])
    )
    target["wikidata_id"] = target.get("wikidata_id") or source.get("wikidata_id")
    target["external_links"] = {
        key: value
        for key, value in {**source.get("external_links", {}), **target.get("external_links", {})}.items()
        if value
    }
    if target.get("confidence") != "high":
        target["confidence"] = source.get("confidence") or target.get("confidence")
    target["last_updated"] = TODAY
    target["last_verified"] = TODAY
    return target


def migrate() -> Dict[str, str]:
    aliases = load_alias_config()
    migrations: Dict[str, str] = {}
    migrations.update(aliases.get("entity_id_migrations", {}) or {})
    migrations.update(aliases.get("entity_id_merges", {}) or {})
    if not migrations:
        print("No entity id migrations declared.")
        return {}

    entities = load_entities()
    entity_paths = {path.stem: path for path in ENTITIES_DIR.rglob("*.json") if path.parent.name != "dynasties"}
    applied: Dict[str, str] = {}
    for old_id, new_id in migrations.items():
        if old_id == new_id:
            continue
        old_path = entity_paths.get(old_id)
        if not old_path or not old_path.exists():
            applied[old_id] = new_id
            continue

        old_doc = read_json(old_path)
        new_path = entity_paths.get(new_id) or entity_path(new_id, old_doc.get("type", "state"))
        if new_path.exists():
            new_doc = read_json(new_path)
            merged = merge_documents(new_doc, old_doc, old_id)
            write_json(new_path, merged)
            old_path.unlink()
            print(f"  ⇄ merged {old_id} → {new_id}")
        else:
            old_doc["id"] = new_id
            names = old_doc.setdefault("names", {})
            aliases_map = names.setdefault("aliases", {})
            canonical_en = (names.get("canonical", {}) or {}).get("en") or old_id
            for lang in {"en", "vi"}:
                aliases_map.setdefault(lang, [])
                if canonical_en not in aliases_map[lang]:
                    aliases_map[lang].append(canonical_en)
            old_doc["last_updated"] = TODAY
            old_doc["last_verified"] = TODAY
            write_json(new_path, old_doc)
            old_path.unlink()
            print(f"  → renamed {old_id} → {new_id}")
        applied[old_id] = new_id

    # update simple foreign-key references outside the entity directory.
    if applied:
        alias_config_path = DATA_DIR / "aliases" / "entity-aliases.json"
        for path in sorted(DATA_DIR.rglob("*.json")):
            if ENTITIES_DIR in path.parents or path == alias_config_path:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            replaced = text
            for old_id, new_id in applied.items():
                replaced = replaced.replace(f'"{old_id}"', f'"{new_id}"')
            if replaced != text:
                path.write_text(replaced, encoding="utf-8")
                print(f"  ↻ updated references in {path.relative_to(DATA_DIR)}")

    write_json(DATA_DIR / "cache" / "entity-id-migration.json", {
        "schema_version": "1.0.0",
        "applied_at": TODAY,
        "migrations": applied,
    })
    return applied


if __name__ == "__main__":
    print("=" * 78)
    print("MIGRATE ENTITY IDENTIFIERS")
    print("=" * 78)
    result = migrate()
    print(f"✅ {len(result)} identifier migrations/merges recorded.")
