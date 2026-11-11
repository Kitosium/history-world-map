#!/usr/bin/env python3
"""Compile the public catalog from the normalized entity, source and spatial data.

Outputs (``data/dist/catalog``):

* ``entities-index.json`` – compact, searchable index of every entity;
* ``sources-index.json`` – bibliographic index of every source record;
* ``timeline.json`` – timeline metadata with live feature/entity counts;
* ``stats.json`` – dataset-level quality and coverage statistics.

The compiler only reads existing files. It never invents names, dates or
descriptions, so rebuilding it is always safe.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DIST_CATALOG_DIR,
    DATA_DIR,
    DIST_SPATIAL_DIR,
    ENTITIES_DIR,
    HISTORICAL_DATE_METADATA,
    SCHEMA_VERSION,
    SOURCES_DIR,
    TODAY,
    entity_path,
    load_entities,
    read_json,
    write_json,
)

ENTITY_TYPE_TAXONOMY = DATA_DIR / "taxonomies" / "entity-types.json"
SOURCE_TIER_TAXONOMY = DATA_DIR / "taxonomies" / "source-tiers.json"


def load_taxonomy(path: Path, key: str) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path).get(key, {}) or {}
    except Exception:
        return {}


def localized_name(names: Dict[str, Any]) -> Dict[str, str]:
    canonical = (names or {}).get("canonical", {}) or {}
    return {
        lang: value
        for lang, value in canonical.items()
        if isinstance(value, str) and value.strip()
    }


def description_excerpt(descriptions: Dict[str, Any], lang: str, limit: int = 280) -> str:
    text = (descriptions or {}).get(lang) or ""
    if not isinstance(text, str):
        return ""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def source_title(source: Dict[str, Any]) -> Dict[str, str]:
    title = source.get("title", {}) or {}
    canonical = title.get("canonical", {}) if isinstance(title, dict) else {}
    if isinstance(canonical, dict):
        return {
            lang: value
            for lang, value in canonical.items()
            if isinstance(value, str) and value.strip()
        }
    return {}


def build_entities_index(
    entities: Dict[str, Dict[str, Any]],
    type_taxonomy: Dict[str, Any],
) -> List[Dict[str, Any]]:
    index: List[Dict[str, Any]] = []
    for eid, doc in sorted(entities.items()):
        names = localized_name(doc.get("names", {}))
        existence = doc.get("existence", {}) or {}
        from_obj = existence.get("from", {}) or {}
        to_obj = existence.get("to", {}) or {}
        from_year = from_obj.get("year")
        to_year = to_obj.get("year")
        from_month = from_obj.get("month")
        from_day = from_obj.get("day")
        from_precision = from_obj.get("precision", "year")
        from_label = from_obj.get("label")
        to_month = to_obj.get("month")
        to_day = to_obj.get("day")
        to_precision = to_obj.get("precision", "year")
        to_label = to_obj.get("label")
        if not isinstance(from_year, int):
            from_year = None
        if not isinstance(to_year, int):
            to_year = None
        etype = doc.get("type", "state")
        spatial = doc.get("spatial_coverage", {}) or {}
        index.append(
            {
                "id": eid,
                "path": entity_path(eid, etype).relative_to(DATA_DIR.parent).as_posix(),
                "name_vi": names.get("vi") or names.get("en") or eid,
                "name_en": names.get("en") or names.get("vi") or eid,
                "name_zh": names.get("zh-CN") or names.get("zh") or "",
                "name_zh_tw": names.get("zh-TW") or "",
                "name_ja": names.get("ja") or "",
                "names": names,
                "type": etype,
                "type_category": (type_taxonomy.get(etype, {}) or {}).get("category", "polity"),
                "from_year": from_year if from_year is not None else 2026,
                "from_month": from_month,
                "from_day": from_day,
                "from_precision": from_precision,
                "from_label": from_label,
                "to_year": to_year if to_year is not None else 2026,
                "to_month": to_month,
                "to_day": to_day,
                "to_precision": to_precision,
                "to_label": to_label,
                "status": existence.get("status", "historical"),
                "existence_basis": existence.get("basis", "unknown"),
                "is_approximate": bool(existence.get("is_approximate")),
                "observed_years": spatial.get("observed_years", doc.get("observed_periods", [])),
                "observed_year_count": len(spatial.get("observed_years", doc.get("observed_periods", [])) or []),
                "confidence": doc.get("confidence", "low"),
                "confidence_basis": doc.get("confidence_basis", ""),
                "boundary_confidence": spatial.get("boundary_confidence"),
                "boundary_precision": spatial.get("boundary_precision"),
                "feature_count": spatial.get("feature_count"),
                "source_ids": doc.get("source_ids", []),
                "wikidata_id": doc.get("wikidata_id"),
                "description_vi": description_excerpt(doc.get("descriptions", {}), "vi"),
                "description_en": description_excerpt(doc.get("descriptions", {}), "en"),
            }
        )
    index.sort(key=lambda item: (item["from_year"], item["id"]))
    return index


def build_sources_index(
    sources: Dict[str, Dict[str, Any]],
    tier_taxonomy: Dict[str, Any],
) -> List[Dict[str, Any]]:
    index: List[Dict[str, Any]] = []
    for sid, doc in sorted(sources.items()):
        title = source_title(doc)
        reliability = doc.get("critique_and_reliability", {}) or {}
        tier = reliability.get("tier", "tier_5_general_reference")
        publication = doc.get("publication", {}) or {}
        license_info = doc.get("license", {}) or {}
        access = doc.get("digital_access", []) or []
        urls = [entry.get("url") for entry in access if isinstance(entry, dict) and entry.get("url")]
        index.append(
            {
                "id": sid,
                "title": title,
                "title_vi": title.get("vi") or title.get("en") or sid,
                "title_en": title.get("en") or title.get("vi") or sid,
                "type": doc.get("type"),
                "tier": tier,
                "tier_rank": (tier_taxonomy.get(tier, {}) or {}).get("rank"),
                "creators": doc.get("creators", []),
                "publication_year": publication.get("year"),
                "publisher": publication.get("publisher"),
                "edition": publication.get("edition"),
                "license": license_info.get("spdx") or license_info.get("name"),
                "urls": urls,
                "coverage": doc.get("coverage", {}),
                "last_verified": doc.get("last_verified"),
            }
        )
    index.sort(key=lambda item: (item.get("tier_rank") or 99, item["id"]))
    return index


def build_timeline() -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    layers = sorted(DIST_SPATIAL_DIR.glob("*.geojson"), key=lambda p: int(p.stem))
    for layer in layers:
        year = int(layer.stem)
        meta = HISTORICAL_DATE_METADATA.get(year, {})
        valid_from = meta.get("valid_from", f"{year:04d}-01-01" if year > 0 else f"{year}-01-01")
        valid_to = meta.get("valid_to", f"{year:04d}-12-31" if year > 0 else f"{year}-12-31")
        precision = meta.get("precision", "year")
        month = meta.get("month")
        day = meta.get("day")
        if month is None and precision in {"day", "month"}:
            parts = valid_from.split("-")
            if valid_from.startswith("-"):
                month = int(parts[2]) if len(parts) >= 3 else 1
                day = int(parts[3]) if len(parts) >= 4 and precision == "day" else None
            else:
                month = int(parts[1]) if len(parts) >= 2 else 1
                day = int(parts[2]) if len(parts) >= 3 and precision == "day" else None

        timeline.append(
            {
                "year": year,
                "month": month,
                "day": day,
                "label_vi": f"{abs(year)} TCN" if year < 0 else f"{year} SCN",
                "label_en": f"{abs(year)} BCE" if year < 0 else f"{year} CE",
                "era_vi": meta.get("era_vi", "Thời kỳ Lịch sử"),
                "era_en": meta.get("era_en", "Historical Period"),
                "valid_from": valid_from,
                "valid_to": valid_to,
                "precision": precision,
                "event_name_vi": meta.get("event_vi", f"{abs(year)} TCN" if year < 0 else f"{year} SCN"),
                "event_name_en": meta.get("event_en", f"{abs(year)} BCE" if year < 0 else f"{year} CE"),
                "file_path": f"data/geojson/{layer.name}",
            }
        )
    return timeline


def enrich_timeline(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    year_stats: Dict[str, Any] = {}
    for entry in timeline:
        year = entry.get("year")
        if not isinstance(year, int):
            continue
        layer = DIST_SPATIAL_DIR / f"{year}.geojson"
        feature_count = 0
        entity_ids = set()
        confidence = collections.Counter()
        if layer.exists():
            try:
                doc = read_json(layer)
            except Exception:
                doc = {}
            for feature in doc.get("features", []):
                props = feature.get("properties", {}) or {}
                feature_count += 1
                eid = props.get("entity_id")
                if eid:
                    entity_ids.add(eid)
                confidence[props.get("confidence") or "low"] += 1
        entry["feature_count"] = feature_count
        entry["entity_count"] = len(entity_ids)
        entry["confidence_counts"] = dict(sorted(confidence.items()))
        entry["file_path"] = entry.get("file_path") or f"data/geojson/{year}.geojson"
        year_stats[str(year)] = {
            "feature_count": feature_count,
            "entity_count": len(entity_ids),
            "confidence_counts": dict(sorted(confidence.items())),
        }
    return year_stats


def build_stats(
    entities: Dict[str, Dict[str, Any]],
    sources: Dict[str, Dict[str, Any]],
    year_stats: Dict[str, Any],
) -> Dict[str, Any]:
    type_counts = collections.Counter(doc.get("type", "state") for doc in entities.values())
    confidence_counts = collections.Counter(doc.get("confidence", "low") for doc in entities.values())
    tier_counts = collections.Counter(
        (doc.get("critique_and_reliability", {}) or {}).get("tier", "unknown")
        for doc in sources.values()
    )
    no_description = sum(1 for doc in entities.values() if not (doc.get("descriptions") or {}))
    no_sources = sum(1 for doc in entities.values() if not doc.get("source_ids"))
    no_geometry = sum(
        1
        for doc in entities.values()
        if not (doc.get("spatial_coverage", {}) or {}).get("observed_years")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "entities": {
            "total": len(entities),
            "with_geometry": len(entities) - no_geometry,
            "without_geometry": no_geometry,
            "without_description": no_description,
            "without_sources": no_sources,
            "by_type": dict(sorted(type_counts.items())),
            "by_confidence": dict(sorted(confidence_counts.items())),
        },
        "sources": {
            "total": len(sources),
            "by_tier": dict(sorted(tier_counts.items())),
        },
        "spatial": {
            "layers": len(year_stats),
            "features": sum(item["feature_count"] for item in year_stats.values()),
            "by_year": year_stats,
        },
    }


def update_manifest(
    stats: Dict[str, Any], entity_count: int, source_count: int, source_ids: List[str]
) -> None:
    path = DATA_DIR / "manifest.json"
    if not path.exists():
        return
    try:
        manifest = read_json(path)
    except Exception:
        return
    manifest["generated_at"] = TODAY
    manifest.setdefault("counts", {})
    manifest["counts"].update(
        {
            "entities": entity_count,
            "entities_with_geometry": stats["entities"]["with_geometry"],
            "sources": source_count,
            "spatial_layers": stats["spatial"]["layers"],
            "spatial_features": stats["spatial"]["features"],
        }
    )
    manifest["entity_type_counts"] = stats["entities"]["by_type"]
    manifest["confidence_counts"] = stats["entities"]["by_confidence"]
    years = sorted(int(year) for year in stats["spatial"]["by_year"])
    manifest.setdefault("temporal_coverage", {})
    manifest["temporal_coverage"]["snapshot_years"] = years
    manifest["sources"] = sorted(source_ids)
    write_json(path, manifest)


def main() -> None:
    print("=" * 78)
    print("COMPILE PUBLIC CATALOG")
    print("=" * 78)

    type_taxonomy = load_taxonomy(ENTITY_TYPE_TAXONOMY, "types")
    tier_taxonomy = load_taxonomy(SOURCE_TIER_TAXONOMY, "tiers")

    entities = load_entities()
    sources: Dict[str, Dict[str, Any]] = {}
    for path in sorted(SOURCES_DIR.rglob("*.json")):
        try:
            doc = read_json(path)
        except Exception:
            continue
        if doc.get("id", "").startswith("src-"):
            sources[doc["id"]] = doc

    entities_index = build_entities_index(entities, type_taxonomy)
    sources_index = build_sources_index(sources, tier_taxonomy)
    timeline = build_timeline()
    year_stats = enrich_timeline(timeline)
    stats = build_stats(entities, sources, year_stats)

    write_json(DIST_CATALOG_DIR / "entities-index.json", entities_index)
    entities_summary = [
        {
            "id": item["id"],
            "name_vi": item["name_vi"],
            "name_en": item["name_en"],
            "type": item["type"],
            "from_year": item["from_year"],
            "from_month": item.get("from_month"),
            "from_day": item.get("from_day"),
            "from_precision": item.get("from_precision"),
            "to_year": item["to_year"],
            "to_month": item.get("to_month"),
            "to_day": item.get("to_day"),
            "to_precision": item.get("to_precision"),
            "observed_years": item["observed_years"],
            "path": item["path"],
        }
        for item in entities_index
    ]
    (DIST_CATALOG_DIR / "entities-summary.json").write_text(
        json.dumps(entities_summary, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    write_json(DIST_CATALOG_DIR / "sources-index.json", sources_index)
    write_json(DIST_CATALOG_DIR / "timeline.json", timeline)
    write_json(DIST_CATALOG_DIR / "stats.json", stats)
    update_manifest(stats, len(entities), len(sources), list(sources))

    print(f"  • entities: {len(entities_index)}")
    print(f"  • sources: {len(sources_index)}")
    print(f"  • timeline years: {len(timeline)} ({timeline[0]['year']} → {timeline[-1]['year']})" if timeline else "  • timeline years: 0")
    print(f"  • spatial features: {stats['spatial']['features']}")
    print("✅ Catalog compiled.")


if __name__ == "__main__":
    main()
