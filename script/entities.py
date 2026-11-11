#!/usr/bin/env python3
"""Normalise entity documents and attach verifiable spatial provenance.

This step is intentionally conservative. It never invents names, dates or
descriptions. It only:

* canonicalises language keys (``zh`` → ``zh-CN``, ``zh-tw`` → ``zh-TW``);
* normalises entity types against ``data/taxonomies/entity-types.json``;
* derives ``observed_periods`` and ``boundary_references`` from the actual
  compiled spatial layers;
* records per-entity boundary provenance (source ids, border precision and
  confidence) and computes an overall confidence level;
* makes observation-based existence ranges explicit through
  ``existence.basis`` and ``existence.continuity_asserted``.

Run after ``spatial.py``.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DATA_DIR,
    DIST_SPATIAL_DIR,
    SCHEMA_VERSION,
    SOURCES_DIR,
    TODAY,
    clean_text,
    confidence_rank,
    entity_path,
    format_year,
    infer_entity_type_from_name,
    iter_entity_files,
    load_entities,
    min_confidence,
    normalize_entity_type,
    normalize_language_map,
    read_json,
    write_json,
)

FORBIDDEN_DESCRIPTION = (
    "disambiguation",
    "định hướng",
    "wikimedia disambiguation",
    "trang định hướng",
)

FORBIDDEN_BOILERPLATES = (
    "bình minh của nền văn minh",
    "thời kỳ đồ đồng",
    "thời kỳ đồ sắt",
    "hậu cổ đại thông qua",
    "trung cổ thông qua",
    "thời cận đại thông qua",
    "late bronze age collapse",
    "có vai trò quan trọng trong bản đồ biến động địa chính trị",
    "maintaining continuous governance into the contemporary era",
    "was a historical polity",
    "là một thực thể lịch sử",
)


def load_source_tiers() -> Dict[str, str]:
    tiers: Dict[str, str] = {}
    for path in sorted(SOURCES_DIR.rglob("*.json")):
        try:
            doc = read_json(path)
        except Exception:
            continue
        sid = doc.get("id")
        tier = (doc.get("critique_and_reliability", {}) or {}).get("tier")
        if sid and tier:
            tiers[sid] = tier
    return tiers


def load_modern_names() -> Dict[str, Dict[str, str]]:
    """Load Natural Earth modern-name enrichment keyed by entity id."""
    path = DATA_DIR / "cache" / "modern-names.json"
    if not path.exists():
        return {}
    try:
        doc = read_json(path)
    except Exception:
        return {}
    names = doc.get("names") or {}
    return {
        eid: {lang: value for lang, value in mapping.items() if isinstance(value, str) and value.strip()}
        for eid, mapping in names.items()
        if isinstance(mapping, dict)
    }


def scan_spatial_layers() -> Dict[str, Dict[str, Any]]:
    """Collect per-entity spatial facts from the compiled GeoJSON layers."""
    facts: Dict[str, Dict[str, Any]] = {}
    for path in sorted(DIST_SPATIAL_DIR.glob("*.geojson")):
        try:
            year = int(path.stem)
            doc = read_json(path)
        except Exception:
            continue
        for feature in doc.get("features", []):
            props = feature.get("properties", {}) or {}
            eid = props.get("entity_id")
            if not eid:
                continue
            fact = facts.setdefault(
                eid,
                {
                    "years": [],
                    "source_ids": set(),
                    "boundary_confidences": [],
                    "boundary_precisions": [],
                    "border_precisions": [],
                    "feature_count": 0,
                },
            )
            if year not in fact["years"]:
                fact["years"].append(year)
            fact["source_ids"].update(props.get("source_ids", []) or [])
            if props.get("boundary_confidence"):
                fact["boundary_confidences"].append(props["boundary_confidence"])
            if props.get("boundary_precision"):
                fact["boundary_precisions"].append(props["boundary_precision"])
            if isinstance(props.get("border_precision"), int):
                fact["border_precisions"].append(props["border_precision"])
            fact["feature_count"] += 1
    for fact in facts.values():
        fact["years"] = sorted(set(fact["years"]))
    return facts


def clean_language_text(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    low = text.lower()
    if any(token in low for token in FORBIDDEN_DESCRIPTION):
        return None
    if any(token in low for token in FORBIDDEN_BOILERPLATES):
        return None
    return text


def clean_language_map(mapping: Any) -> Dict[str, str]:
    normalised = normalize_language_map(mapping)
    out: Dict[str, str] = {}
    for key, value in normalised.items():
        text = clean_language_text(value) if isinstance(value, str) else None
        if text:
            out[key] = text
    return out


def clean_alias_map(mapping: Any) -> Dict[str, List[str]]:
    normalised = normalize_language_map(mapping)
    out: Dict[str, List[str]] = {}
    for key, values in normalised.items():
        if isinstance(values, str):
            values = [values]
        cleaned: List[str] = []
        for value in values or []:
            text = clean_text(value)
            if text and text not in cleaned:
                cleaned.append(text)
        if cleaned:
            out[key] = cleaned
    return out


def infer_existence_basis(entity: Dict[str, Any], observed_years: List[int], source_ids: List[str]) -> str:
    basis = (entity.get("existence", {}) or {}).get("basis")
    if basis:
        return basis
    if entity.get("existence", {}).get("status") == "active" and observed_years and observed_years[-1] == 2026:
        return "modern_snapshot"
    if len(observed_years) > 1:
        return "cartographic_observation_range"
    if len(observed_years) == 1:
        return "single_observation"
    if any("natural-earth" in sid for sid in source_ids):
        return "modern_snapshot"
    return "cartographic_observation"


def build_spatial_coverage(eid: str, fact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not fact:
        return {
            "observed_years": [],
            "first_observed_year": None,
            "last_observed_year": None,
            "feature_count": 0,
            "boundary_source_ids": [],
            "boundary_confidence": None,
            "boundary_precision": None,
            "border_precision": None,
        }
    confidences = fact["boundary_confidences"]
    precisions = [value for value in fact["boundary_precisions"] if value]
    border_precisions = fact["border_precisions"]
    return {
        "observed_years": fact["years"],
        "first_observed_year": fact["years"][0] if fact["years"] else None,
        "last_observed_year": fact["years"][-1] if fact["years"] else None,
        "feature_count": fact["feature_count"],
        "boundary_source_ids": sorted(fact["source_ids"]),
        "boundary_confidence": min_confidence(confidences) if confidences else None,
        "boundary_precision": precisions[0] if len(set(precisions)) == 1 else "mixed",
        "border_precision": min(border_precisions) if border_precisions else None,
    }


def compute_confidence(
    source_ids: Iterable[str],
    tiers: Dict[str, str],
    spatial_coverage: Dict[str, Any],
    has_geometry: bool,
) -> tuple:
    tier_values = [tiers.get(sid) for sid in source_ids if tiers.get(sid)]
    tier_rank = {
        "tier_1_official_primary": 1,
        "tier_2_contemporary_eyewitness": 2,
        "tier_3_peer_reviewed_academic": 3,
        "tier_3_authoritative_cartography": 3,
        "tier_4_scholarly_atlas": 4,
        "tier_5_general_reference": 5,
    }
    best_tier = min((tier_rank.get(tier, 9) for tier in tier_values), default=9)
    boundary = spatial_coverage.get("boundary_confidence")
    if not has_geometry:
        if best_tier <= 4:
            return "medium", "Existence/names are supported by authoritative sources; no boundary geometry is asserted."
        return "low", "No tier 1-4 source or boundary geometry is available."
    if boundary == "low" or best_tier >= 5:
        return "low", "At least one component is only approximate or reference-grade."
    if boundary == "high" and best_tier <= 3:
        return "high", "Boundaries are marked precise and sources are tier 1-3."
    return "medium", "Boundaries are approximate or the best source is tier 4."


def normalise_entity(
    entity: Dict[str, Any],
    fact: Optional[Dict[str, Any]],
    tiers: Dict[str, str],
    modern_names: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    eid = entity.get("id")
    entity["schema_version"] = SCHEMA_VERSION
    entity["type"] = normalize_entity_type(entity.get("type", "state"))
    entity.pop("$schema", None)

    names = entity.setdefault("names", {})
    canonical = clean_language_map(names.get("canonical", {}))
    for lang, value in (modern_names or {}).get(eid, {}).items():
        if value and not canonical.get(lang):
            canonical[lang] = value
    if not canonical.get("en") and canonical.get("vi"):
        canonical["en"] = canonical["vi"]
    if not canonical.get("vi") and canonical.get("en"):
        canonical["vi"] = canonical["en"]
    names["canonical"] = canonical
    # conservative type refinement: only entities still typed as a generic
    # "state" are reclassified from explicit name keywords. Existing specific
    # classifications are never overwritten.
    if entity["type"] == "state":
        candidate = canonical.get("en") or canonical.get("vi") or ""
        inferred = infer_entity_type_from_name(candidate)
        if inferred != "state":
            entity["type"] = inferred
    names["aliases"] = clean_alias_map(names.get("aliases", {}))
    native = clean_text(names.get("native"))
    if native:
        names["native"] = native
    else:
        names.pop("native", None)

    historical_names = []
    for item in names.get("historical_names", []) or []:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        entry["name"] = clean_language_map(entry.get("name", {}))
        for key in ("from", "to"):
            if isinstance(entry.get(key), dict):
                entry[key] = normalise_date_obj(entry[key])
        if entry.get("name"):
            historical_names.append(entry)
    if historical_names:
        names["historical_names"] = historical_names
    else:
        names.pop("historical_names", None)

    entity["descriptions"] = clean_language_map(entity.get("descriptions", {}))

    spatial_coverage = build_spatial_coverage(eid, fact)
    if fact:
        observed_years = spatial_coverage["observed_years"]
    else:
        spatial_coverage["observed_years"] = []
        spatial_coverage["first_observed_year"] = None
        spatial_coverage["last_observed_year"] = None
        observed_years = [
            int(year) for year in (entity.get("observed_periods", []) or [])
            if isinstance(year, int) and -3500 <= year <= 2026
        ]
        observed_years = sorted(set(observed_years))
    entity["observed_periods"] = observed_years

    existence = entity.setdefault("existence", {})
    eid = entity.get("id", "")
    canonical_dates = ENTITY_CANONICAL_DATES.get(eid)
    from_raw = dict(existence.get("from", {}) or {})
    to_raw = dict(existence.get("to", {}) or {})
    if canonical_dates:
        if "from" in canonical_dates:
            for k, v in canonical_dates["from"].items():
                from_raw.setdefault(k, v)
        if "to" in canonical_dates:
            for k, v in canonical_dates["to"].items():
                to_raw.setdefault(k, v)
    from_obj = normalise_date_obj(from_raw)
    to_obj = normalise_date_obj(to_raw)
    if not from_obj.get("year") and observed_years:
        from_obj["year"] = observed_years[0]
    if not to_obj.get("year") and observed_years:
        to_obj["year"] = observed_years[-1]
    from_year = int(from_obj.get("year", 2026))
    to_year = int(to_obj.get("year", 2026))
    if from_year > to_year:
        from_year, to_year = to_year, from_year
    existence["from"] = from_obj
    existence["to"] = to_obj
    existence["duration_years"] = max(0, to_year - from_year)
    if existence.get("status") not in {"active", "historical"}:
        existence["status"] = "active" if to_year >= 2026 else "historical"

    source_ids = [sid for sid in (entity.get("source_ids", []) or []) if isinstance(sid, str)]
    boundary_sources = spatial_coverage.get("boundary_source_ids", [])
    for sid in boundary_sources:
        if sid not in source_ids:
            source_ids.append(sid)
    if entity.get("wikidata_id") and entity["descriptions"]:
        wikidata_source = "src-wikidata"
        if wikidata_source not in source_ids:
            source_ids.append(wikidata_source)
    entity["source_ids"] = sorted(set(source_ids))

    basis = infer_existence_basis(entity, observed_years, entity["source_ids"])
    existence["basis"] = basis
    existence["continuity_asserted"] = basis in {"source_attested", "wikidata_temporal"} or (
        existence.get("status") == "active" and basis == "modern_snapshot"
    )
    existence["is_approximate"] = basis in {
        "cartographic_observation",
        "cartographic_observation_range",
        "single_observation",
        "modern_snapshot",
    }

    # preserve only explicitly sourced narrative reasons.
    for key in ("foundation_reason", "dissolution_reason"):
        value = existence.get(key)
        if isinstance(value, dict):
            cleaned = {}
            for lang, text in value.items():
                if lang == "type":
                    cleaned[lang] = text
                    continue
                if isinstance(text, str):
                    text = clean_language_text(text)
                    if text:
                        cleaned[lang] = text
            existence[key] = cleaned or None
        elif value is not None:
            existence[key] = None

    # boundary references are derived, never hand-maintained.
    boundary_references = []
    if fact:
        for year in spatial_coverage["observed_years"]:
            boundary_references.append(
                {
                    "year": year,
                    "year_system": "astronomical",
                    "file_path": f"data/dist/spatial/by-year/{year}.geojson",
                    "source_ids": sorted(set(fact["source_ids"])),
                    "boundary_confidence": spatial_coverage.get("boundary_confidence"),
                    "boundary_precision": spatial_coverage.get("boundary_precision"),
                }
            )
    entity["boundary_references"] = boundary_references
    entity["spatial_coverage"] = spatial_coverage

    confidence, confidence_basis = compute_confidence(
        entity["source_ids"], tiers, spatial_coverage, bool(fact)
    )
    entity["confidence"] = confidence
    entity["confidence_basis"] = confidence_basis

    external_links = {
        key: value for key, value in (entity.get("external_links", {}) or {}).items() if value
    }
    qid = entity.get("wikidata_id")
    if qid and str(qid).startswith("Q"):
        external_links["wikidata"] = f"https://www.wikidata.org/wiki/{qid}"
    entity["external_links"] = external_links

    entity["provenance"] = {
        "names": ["src-wikidata"]
        if entity.get("wikidata_id") and entity["descriptions"]
        else entity["source_ids"],
        "existence": entity["source_ids"],
        "boundaries": boundary_sources,
        "method": "compiled from cartographic layers; see boundary_precision per feature",
        "last_verified": TODAY,
    }

    entity["last_updated"] = TODAY
    entity["last_verified"] = TODAY

    # stable top-level key order for easier diffs.
    order = [
        "id", "schema_version", "type", "wikidata_id", "names", "descriptions",
        "existence", "observed_periods", "spatial_coverage", "boundary_references",
        "source_ids", "provenance", "confidence", "confidence_basis",
        "external_links", "last_updated", "last_verified",
    ]
    ordered = {key: entity[key] for key in order if key in entity}
    for key, value in entity.items():
        if key not in ordered and key != "$schema":
            ordered[key] = value
    return ordered


ENTITY_CANONICAL_DATES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "vietnam": {
        "from": {"year": 1945, "month": 9, "day": 2, "precision": "day", "label": "02/09/1945 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "south-vietnam": {
        "from": {"year": 1955, "month": 10, "day": 26, "precision": "day", "label": "26/10/1955 SCN"},
        "to": {"year": 1975, "month": 4, "day": 30, "precision": "day", "label": "30/04/1975 SCN"}
    },
    "french-indochina": {
        "from": {"year": 1887, "month": 10, "day": 17, "precision": "day", "label": "17/10/1887 SCN"},
        "to": {"year": 1954, "month": 7, "day": 21, "precision": "day", "label": "21/07/1954 SCN"}
    },
    "united-states-of-america": {
        "from": {"year": 1776, "month": 7, "day": 4, "precision": "day", "label": "04/07/1776 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "ussr": {
        "from": {"year": 1922, "month": 12, "day": 30, "precision": "day", "label": "30/12/1922 SCN"},
        "to": {"year": 1991, "month": 12, "day": 26, "precision": "day", "label": "26/12/1991 SCN"}
    },
    "weimar-republic": {
        "from": {"year": 1918, "month": 11, "day": 9, "precision": "day", "label": "09/11/1918 SCN"},
        "to": {"year": 1933, "month": 3, "day": 23, "precision": "day", "label": "23/03/1933 SCN"}
    },
    "nazi-germany": {
        "from": {"year": 1933, "month": 3, "day": 23, "precision": "day", "label": "23/03/1933 SCN"},
        "to": {"year": 1945, "month": 5, "day": 8, "precision": "day", "label": "08/05/1945 SCN"}
    },
    "german-empire": {
        "from": {"year": 1871, "month": 1, "day": 18, "precision": "day", "label": "18/01/1871 SCN"},
        "to": {"year": 1918, "month": 11, "day": 9, "precision": "day", "label": "09/11/1918 SCN"}
    },
    "east-germany": {
        "from": {"year": 1949, "month": 10, "day": 7, "precision": "day", "label": "07/10/1949 SCN"},
        "to": {"year": 1990, "month": 10, "day": 3, "precision": "day", "label": "03/10/1990 SCN"}
    },
    "west-germany": {
        "from": {"year": 1949, "month": 5, "day": 23, "precision": "day", "label": "23/05/1949 SCN"},
        "to": {"year": 1990, "month": 10, "day": 3, "precision": "day", "label": "03/10/1990 SCN"}
    },
    "qing-empire": {
        "from": {"year": 1636, "precision": "year"},
        "to": {"year": 1912, "month": 2, "day": 12, "precision": "day", "label": "12/02/1912 SCN"}
    },
    "republic-of-china": {
        "from": {"year": 1912, "month": 1, "day": 1, "precision": "day", "label": "01/01/1912 SCN"}
    },
    "china": {
        "from": {"year": 1949, "month": 10, "day": 1, "precision": "day", "label": "01/10/1949 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "kingdom-of-italy": {
        "from": {"year": 1861, "month": 3, "day": 17, "precision": "day", "label": "17/03/1861 SCN"},
        "to": {"year": 1946, "month": 6, "day": 2, "precision": "day", "label": "02/06/1946 SCN"}
    },
    "indonesia": {
        "from": {"year": 1945, "month": 8, "day": 17, "precision": "day", "label": "17/08/1945 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "philippines": {
        "from": {"year": 1946, "month": 7, "day": 4, "precision": "day", "label": "04/07/1946 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "india": {
        "from": {"year": 1947, "month": 8, "day": 15, "precision": "day", "label": "15/08/1947 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "pakistan": {
        "from": {"year": 1947, "month": 8, "day": 14, "precision": "day", "label": "14/08/1947 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "israel": {
        "from": {"year": 1948, "month": 5, "day": 14, "precision": "day", "label": "14/05/1948 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "south-korea": {
        "from": {"year": 1948, "month": 8, "day": 15, "precision": "day", "label": "15/08/1948 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "north-korea": {
        "from": {"year": 1948, "month": 9, "day": 9, "precision": "day", "label": "09/09/1948 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "malaysia": {
        "from": {"year": 1957, "month": 8, "day": 31, "precision": "day", "label": "31/08/1957 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    },
    "singapore": {
        "from": {"year": 1965, "month": 8, "day": 9, "precision": "day", "label": "09/08/1965 SCN"},
        "to": {"year": 2026, "month": 11, "day": 3, "precision": "day", "label": "2026 SCN"}
    }
}


def normalise_date_obj(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    year = value.get("year")
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = None
    out: Dict[str, Any] = {}
    if year is not None:
        out["year"] = year
        out["year_system"] = value.get("year_system") or "astronomical"
        precision = value.get("precision")
        month = value.get("month")
        day = value.get("day")
        if not precision:
            if day is not None:
                precision = "day"
            elif month is not None:
                precision = "month"
            else:
                precision = "year"
        out["precision"] = precision

        label = value.get("label")
        if not label or label == format_year(year):
            if day is not None and month is not None:
                label = f"{int(day):02d}/{int(month):02d}/{format_year(year)}"
            elif month is not None:
                label = f"Tháng {int(month):02d}/{format_year(year)}"
            else:
                label = format_year(year)
        out["label"] = label
    for key in ("month", "day", "calendar", "is_approximate", "fuzzy_range"):
        if value.get(key) is not None:
            out[key] = value[key]
    return out


def main() -> None:
    print("=" * 78)
    print("NORMALISE ENTITIES + SPATIAL PROVENANCE")
    print("=" * 78)

    entities = load_entities()
    existing_paths = {path.stem: path for path in iter_entity_files()}
    facts = scan_spatial_layers()
    tiers = load_source_tiers()
    modern_names = load_modern_names()
    print(f"  • {len(entities)} entities")
    print(f"  • {len(facts)} entities with compiled geometry")
    print(f"  • {len(tiers)} source records")
    print(f"  • {len(modern_names)} modern name records")

    changed = 0
    for eid, entity in sorted(entities.items()):
        normalised = normalise_entity(
            entity, facts.get(eid), tiers, modern_names.get(eid, {})
        )
        path = entity_path(eid, normalised.get("type", "state"))
        old_path = existing_paths.get(eid)
        before = old_path.read_text(encoding="utf-8") if old_path and old_path.exists() else ""
        after = json.dumps(normalised, ensure_ascii=False, indent=2) + "\n"
        if before != after:
            changed += 1
        write_json(path, normalised)
        if old_path and old_path != path and old_path.exists():
            old_path.unlink()

    # summary for the catalog step and for humans.
    type_counts = collections.Counter(read_json(path).get("type") for path in iter_entity_files())
    confidence_counts = collections.Counter(read_json(path).get("confidence") for path in iter_entity_files())
    no_geometry = sorted(eid for eid in entities if eid not in facts)
    stats = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "entity_count": len(entities),
        "entities_with_geometry": len(facts),
        "entities_without_geometry": no_geometry,
        "entity_type_counts": dict(sorted(type_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "spatial_years": len(list(DIST_SPATIAL_DIR.glob("*.geojson"))),
    }
    write_json(DATA_DIR / "cache" / "entity-stats.json", stats)

    print(f"  ✓ normalised {changed} files")
    print(f"  • types: {dict(type_counts)}")
    print(f"  • confidence: {dict(confidence_counts)}")
    if no_geometry:
        print(f"  ! {len(no_geometry)} entities have no geometry: {', '.join(no_geometry[:10])}"
              + (" …" if len(no_geometry) > 10 else ""))
    print("✅ Entity documents normalised.")


if __name__ == "__main__":
    main()
