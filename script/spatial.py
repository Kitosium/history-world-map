#!/usr/bin/env python3
"""Rebuild every spatial layer from the upstream cartographic sources.

Design goals
------------
* Reproducible: source URLs, versions and hashes are recorded in
  ``data/sources/manifests/cartographic.json``.
* Lossless provenance: upstream ``BORDERPRECISION`` is preserved and exposed as
  ``border_precision`` / ``boundary_precision`` / ``boundary_confidence``.
* Clean topology per year: features are dissolved by ``entity_id`` so each
  year contains one (Multi)Polygon feature per polity.
* Identifier reconciliation: source names are mapped through
  ``data/aliases/entity-aliases.json``; missing polities become explicit entity
  stubs instead of being silently dropped.

Usage
-----
    python3 script/spatial.py --hb-dir /tmp/opencode/hb
    python3 script/spatial.py            # downloads to a cache folder
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DATA_DIR,
    DIST_SPATIAL_DIR,
    HISTORICAL_DATE_METADATA,
    SCHEMA_VERSION,
    SOURCE_CATALOG,
    TODAY,
    apply_aliases,
    bbox_of,
    border_precision_to_confidence,
    build_name_index,
    clean_geometry,
    entity_path,
    entity_type_to_layer_type,
    infer_entity_type_from_name,
    is_excluded_name,
    load_alias_config,
    load_entities,
    load_exclusions,
    merge_geometries,
    min_confidence,
    normalize_entity_type,
    read_json,
    sha256_file,
    slugify,
    transliterate,
    write_json,
)

NE_SOURCE_ID = "src-natural-earth"
HB_SOURCE_ID = "src-basemaps"
WIKIDATA_SOURCE_ID = "src-wikidata"

# source ids used by older builds; mapped forward when reading legacy layers
LEGACY_SOURCE_IDS = {
    "src-historical-basemaps-ourednik": "src-basemaps",
    "src-natural-earth-2026": "src-natural-earth",
    "src-dai-viet-su-ky-toan-thu": "src-dai-viet",
    "src-su-ky-tu-ma-thien": "src-shiji",
    "src-dai-nam-nhat-thong-chi": "src-dai-nam",
    "src-dao-duy-anh-dat-nuoc-viet-nam-qua-cac-doi": "src-dao-duy-anh",
    "src-george-coedes-etats-hindouises": "src-coedes",
    "src-luong-ninh-lich-su-vuong-quoc-champa": "src-luong-ninh",
    "src-khao-co-hoc-viet-nam": "src-khao-co",
    "src-wikidata-historical-entities": "src-wikidata",
}

HB_COMMIT = "4b5039e50d8d2464b065bd76ad6086cd4597108d"
HB_INDEX_URL = "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/index.json"
HB_RAW_URL = "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/{filename}"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson"

# timeline used by application, kept in sync with catalog timeline
YEARS = [
    -3500, -3000, -2000, -1500, -1000, -700, -500, -400, -323, -300,
    -200, -100, -1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
    1100, 1200, 1279, 1300, 1400, 1492, 1500, 1530, 1600, 1650, 1700,
    1715, 1783, 1800, 1815, 1878, 1880, 1900, 1914, 1920, 1930, 1938,
    1945, 1960, 1994, 2000, 2010,
]
MODERN_YEAR = 2026

NE_NAME_FIELDS = {
    "en": "NAME_EN",
    "vi": "NAME_VI",
    "zh-CN": "NAME_ZH",
    "zh-TW": "NAME_ZHT",
    "ja": "NAME_JA",
    "fr": "NAME_FR",
    "es": "NAME_ES",
    "de": "NAME_DE",
    "ru": "NAME_RU",
    "ar": "NAME_AR",
}


def log(message: str) -> None:
    print(message, flush=True)


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    log(f"  ⬇  {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "WorldHistoryAtlas/1.3"})
    with urllib.request.urlopen(req, timeout=120) as response, open(destination, "wb") as fh:
        fh.write(response.read())
    return destination


def ensure_sources(hb_dir: Path, ne_path: Path) -> Tuple[Dict[int, Path], Path]:
    hb_dir.mkdir(parents=True, exist_ok=True)
    index_path = download(HB_INDEX_URL, hb_dir / "index.json")
    index = read_json(index_path)
    entries = index.get("years", index if isinstance(index, list) else [])
    by_year = {int(item["year"]): item for item in entries}
    paths: Dict[int, Path] = {}
    for year in YEARS:
        item = by_year.get(year)
        if not item and year == -3500:
            item = by_year.get(-3000)
        if not item:
            raise SystemExit(f"Upstream historical-basemaps has no layer for year {year}")
        paths[year] = download(HB_RAW_URL.format(filename=item["filename"]), hb_dir / f"{year}.geojson")
    ne_path = download(NE_URL, ne_path)
    return paths, ne_path


# ---------------------------------------------------------------------------
# legacy mapping / special source preservation
# ---------------------------------------------------------------------------

def load_custom_features() -> Dict[int, List[Dict[str, Any]]]:
    """Load hand-curated regional features (academic historical geography)."""
    path = DATA_DIR / "geography" / "custom-features.geojson"
    by_year: Dict[int, List[Dict[str, Any]]] = collections.defaultdict(list)
    if not path.exists():
        return by_year
    doc = read_json(path)
    for feature in doc.get("features", []):
        props = feature.get("properties", {}) or {}
        year = props.get("valid_year")
        if isinstance(year, int):
            by_year[year].append(feature)
    return by_year


def load_legacy_context() -> Tuple[Dict[str, str], Dict[Tuple[int, str], List[str]], Dict[Tuple[int, str], Dict[str, Any]]]:
    """Read the previous dist layer to preserve manual regional citations."""
    name_to_entity: Dict[str, str] = {}
    extra_sources: Dict[Tuple[int, str], List[str]] = collections.defaultdict(list)
    extra_props: Dict[Tuple[int, str], Dict[str, Any]] = collections.defaultdict(dict)
    if not DIST_SPATIAL_DIR.exists():
        return name_to_entity, extra_sources, extra_props
    for path in sorted(DIST_SPATIAL_DIR.glob("*.geojson")):
        try:
            year = int(path.stem)
            doc = read_json(path)
        except Exception:
            continue
        for feature in doc.get("features", []):
            props = feature.get("properties", {}) or {}
            entity_id = props.get("entity_id")
            name = (props.get("name_en") or "").strip()
            if name and entity_id:
                name_to_entity.setdefault(name, entity_id)
            if entity_id:
                extra = [
                    mapped
                    for mapped in (
                        LEGACY_SOURCE_IDS.get(s, s)
                        for s in props.get("source_ids", [])
                    )
                    if mapped not in {HB_SOURCE_ID, NE_SOURCE_ID}
                ]
                if extra:
                    extra_sources[(year, entity_id)].extend(extra)
                ignored = {"id", "feature_id", "entity_id", "valid_year", "year_system", "year_label", "source_ids"}
                carried = {
                    key: value
                    for key, value in props.items()
                    if key in {"subject_to", "part_of", "type", "layer_type"} and key not in ignored
                }
                if carried:
                    extra_props[(year, entity_id)].update(carried)
    return name_to_entity, extra_sources, extra_props


# ---------------------------------------------------------------------------
# entity stubs
# ---------------------------------------------------------------------------

def cache_lookup(cache: Dict[str, Any], *names: str) -> Optional[Dict[str, Any]]:
    by_key = {str(key).strip().casefold(): value for key, value in cache.items() if isinstance(value, dict)}
    for name in names:
        if name and str(name).strip().casefold() in by_key:
            return by_key[str(name).strip().casefold()]
    return None


def names_from_cache(cache: Dict[str, Any], *names: str) -> Dict[str, str]:
    entry = cache_lookup(cache, *names)
    if not entry:
        return {}
    labels = entry.get("labels", {}) or {}
    out: Dict[str, str] = {}
    for key, value in labels.items():
        if not value:
            continue
        norm = {
            "zh": "zh-CN",
            "zh-cn": "zh-CN",
            "zh-tw": "zh-TW",
            "zh-hant": "zh-TW",
            "zh-hans": "zh-CN",
        }.get(key.lower(), key)
        out.setdefault(norm, value)
    return out


def descriptions_from_cache(cache: Dict[str, Any], *names: str) -> Dict[str, str]:
    entry = cache_lookup(cache, *names)
    if not entry:
        return {}
    descriptions = entry.get("descriptions", {}) or {}
    out: Dict[str, str] = {}
    for key, value in descriptions.items():
        if not value:
            continue
        norm = {"zh": "zh-CN", "zh-cn": "zh-CN", "zh-tw": "zh-TW"}.get(key.lower(), key)
        out.setdefault(norm, value)
    return out


def make_historical_stub(name: str, cache: Dict[str, Any], seen_years: Iterable[int]) -> Dict[str, Any]:
    entity_id = slugify(name)
    years = sorted(set(seen_years))
    first = years[0] if years else -3500
    last = years[-1] if years else 2010
    names = names_from_cache(cache, name)
    names.setdefault("en", name)
    names.setdefault("vi", names.get("vi") or name)
    entry = cache_lookup(cache, name)
    descriptions = descriptions_from_cache(cache, name)
    source_ids = [HB_SOURCE_ID]
    if entry and entry.get("qid"):
        source_ids.append(WIKIDATA_SOURCE_ID)
    return {
        "id": entity_id,
        "schema_version": SCHEMA_VERSION,
        "type": infer_entity_type_from_name(name),
        "wikidata_id": (entry or {}).get("qid"),
        "names": {"canonical": names, "aliases": {}},
        "descriptions": descriptions,
        "existence": {
            "from": {"year": first, "year_system": "astronomical", "precision": "year", "label": f"{abs(first)} {'TCN' if first < 0 else 'SCN'}"},
            "to": {"year": last, "year_system": "astronomical", "precision": "year", "label": f"{abs(last)} {'TCN' if last < 0 else 'SCN'}"},
            "duration_years": max(0, last - first),
            "status": "historical",
            "basis": "cartographic_observation",
            "continuity_asserted": False,
            "is_approximate": True,
            "foundation_reason": None,
            "dissolution_reason": None,
        },
        "observed_periods": years,
        "boundary_references": [],
        "source_ids": source_ids,
        "external_links": {},
        "confidence": "medium",
        "last_updated": TODAY,
        "last_verified": TODAY,
    }


def ne_layer_type(props: Dict[str, Any]) -> str:
    name = (props.get("NAME_EN") or "").strip()
    admin = (props.get("ADMIN") or "").strip()
    sovereign = (props.get("SOVEREIGNT") or "").strip()
    source_type = (props.get("TYPE") or "").strip()

    # israel is a sovereign un member state
    if name == "Israel" or admin == "Israel":
        return "sovereign_territory"

    # disputed / indeterminate / lease
    if source_type in {"Disputed", "Indeterminate", "Lease"}:
        return "disputed_territory"

    # dependencies
    if source_type == "Dependency":
        return "dependent_territory"

    # sovereign countries
    if source_type in {"Sovereign country", "Sovereignty"}:
        return "sovereign_territory"

    # country: check if sovereign metropole or constituent/dependent territory
    if source_type == "Country":
        if admin == sovereign:
            return "sovereign_territory"
        return "dependent_territory"

    return "sovereign_territory"


def make_modern_stub(props: Dict[str, Any], cache: Dict[str, Any]) -> Dict[str, Any]:
    name = (props.get("NAME_EN") or props.get("ADMIN") or props.get("NAME") or "").strip()
    entity_id = slugify(name or props.get("ADMIN") or "territory")
    canonical = {lang: props.get(field) for lang, field in NE_NAME_FIELDS.items() if props.get(field)}
    canonical.setdefault("en", name)
    canonical.setdefault("vi", canonical.get("vi") or name)
    descriptions = descriptions_from_cache(cache, name, props.get("ADMIN", ""))
    layer_type = ne_layer_type(props)
    source_ids = [NE_SOURCE_ID]
    if descriptions:
        source_ids.append(WIKIDATA_SOURCE_ID)
    return {
        "id": entity_id,
        "schema_version": SCHEMA_VERSION,
        "type": {
            "dependent_territory": "dependent_territory",
            "disputed_territory": "disputed_territory",
        }.get(layer_type, "state"),
        "wikidata_id": (props.get("WIKIDATAID") or None),
        "names": {"canonical": canonical, "aliases": {}},
        "descriptions": descriptions,
        "existence": {
            "from": {"year": MODERN_YEAR, "year_system": "astronomical", "precision": "year", "label": f"{MODERN_YEAR} SCN"},
            "to": {"year": MODERN_YEAR, "year_system": "astronomical", "precision": "year", "label": f"{MODERN_YEAR} SCN"},
            "duration_years": 0,
            "status": "active",
            "basis": "modern_snapshot",
            "continuity_asserted": True,
            "is_approximate": True,
            "foundation_reason": None,
            "dissolution_reason": None,
        },
        "observed_periods": [MODERN_YEAR],
        "boundary_references": [],
        "source_ids": source_ids,
        "external_links": {
            "wikidata": f"https://www.wikidata.org/wiki/{props['WIKIDATAID']}"
            if props.get("WIKIDATAID")
            else None
        },
        "confidence": "high",
        "last_updated": TODAY,
        "last_verified": TODAY,
    }


# ---------------------------------------------------------------------------
# spatial features
# ---------------------------------------------------------------------------

def feature_base_properties(
    entity: Dict[str, Any],
    year: int,
    border_confidence: str,
    boundary_precision: str,
    border_precision: Optional[int],
    source_ids: List[str],
    layer_type: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    names = entity.get("names", {}).get("canonical", {}) or {}
    props: Dict[str, Any] = {
        "id": f"feat-{year}-{entity['id']}",
        "entity_id": entity["id"],
        "name_vi": names.get("vi") or names.get("en") or entity["id"],
        "name_en": names.get("en") or names.get("vi") or entity["id"],
        "name_zh": names.get("zh-CN") or names.get("zh") or "",
        "name_ja": names.get("ja") or "",
        "name_fr": names.get("fr") or "",
        "name_es": names.get("es") or "",
        "name_de": names.get("de") or "",
        "name_ru": names.get("ru") or "",
        "name_ar": names.get("ar") or "",
        "type": entity.get("type", "state"),
        "layer_type": layer_type or entity_type_to_layer_type(entity.get("type", "state")),
        "valid_year": year,
        "year_system": "astronomical",
        "year_label": f"{abs(year)} {'TCN' if year < 0 else 'SCN'}" if year else "1 TCN",
        "source_ids": sorted(set(source_ids)),
        "confidence": border_confidence,
        "boundary_precision": boundary_precision,
        "boundary_confidence": border_confidence,
        "border_precision": border_precision,
        "wikidata_id": entity.get("wikidata_id"),
    }
    meta = HISTORICAL_DATE_METADATA.get(year, {})
    if meta:
        props["valid_from"] = meta.get("valid_from")
        props["valid_to"] = meta.get("valid_to")
        props["precision"] = meta.get("precision", "year")
        props["valid_month"] = meta.get("month")
        props["valid_day"] = meta.get("day")
    if extra:
        for key, value in extra.items():
            if value not in (None, "", [], {}):
                props[key] = value
    return props


def group_features(year: int, raw_features: List[Dict[str, Any]], resolve) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for raw in raw_features:
        props = raw.get("properties", {}) or {}
        name = (props.get("NAME") or "").strip()
        if not name or name in {"?", "??", "-", "—", "N/A", "Unknown"}:
            # unnamed / placeholder polygons are mostly antarctica fragments or blank units
            continue
        # in 1920-1938 (french indochina era), upstream historical basemaps split
        # french indochina into subdivisions ("annam", "cochin china", etc.)
        if year in {1920, 1930, 1938} and name in {
            "Annam",
            "Cochin China",
            "French Indo-China",
            "French Indochina",
            "Laos",
            "Cambodia",
        }:
            entity = resolve("French Indochina")
        else:
            entity = resolve(name)

        if not entity:
            continue
        geometry = clean_geometry(raw.get("geometry"))
        if not geometry:
            continue
        eid = entity["id"]
        bucket = grouped.setdefault(
            eid,
            {
                "entity": entity,
                "geometries": [],
                "border_precisions": [],
                "subject_to": set(),
                "part_of": set(),
                "source_ids": {HB_SOURCE_ID},
            },
        )
        bucket["geometries"].append(geometry)
        try:
            bucket["border_precisions"].append(int(props.get("BORDERPRECISION")))
        except (TypeError, ValueError):
            bucket["border_precisions"].append(0)

        # for french indochina during colonial era, ensure subject_to is France
        if eid == "french-indochina":
            bucket["subject_to"].add("France")
        else:
            subject = (props.get("SUBJECTO") or "").strip()
            part_of = (props.get("PARTOF") or "").strip()
            if subject and subject != name:
                bucket["subject_to"].add(subject)
            if part_of and part_of != name:
                bucket["part_of"].add(part_of)
    return grouped


def build_historical_layers(
    paths: Dict[int, Path],
    entities: Dict[str, Dict[str, Any]],
    name_index: Dict[str, str],
    aliases: Dict[str, Any],
    legacy_names: Dict[str, str],
    extra_sources: Dict[Tuple[int, str], List[str]],
    extra_props: Dict[Tuple[int, str], Dict[str, Any]],
    custom_features: Dict[int, List[Dict[str, Any]]],
    cache: Dict[str, Any],
    excluded_ids: Set[str],
    excluded_names: Set[str],
) -> Tuple[Dict[str, List[int]], Dict[int, int]]:
    coverage: Dict[str, List[int]] = collections.defaultdict(list)
    year_counts: Dict[int, int] = {}
    created: List[str] = []
    name_to_entity = dict(legacy_names)

    def is_excluded(value: str) -> bool:
        return is_excluded_name(value, excluded_ids, excluded_names)

    def resolve(name: str) -> Optional[Dict[str, Any]]:
        # prefer entities that still exist; exclusion blocks creation of new stubs
        key = apply_aliases(name, aliases)
        if key in entities:
            return entities[key]
        if name in name_to_entity:
            eid = name_to_entity[name]
            eid = aliases.get("entity_id_migrations", {}).get(eid, eid)
            if eid not in excluded_ids and eid in entities:
                return entities[eid]
        slug = slugify(name)
        if slug in entities:
            return entities[slug]
        if slug in name_index and name_index[slug] in entities:
            return entities[name_index[slug]]

        if is_excluded(name) or is_excluded(key) or slug in excluded_names:
            return None
        # culture/tribe layers removed; do not recreate them as stubs
        if infer_entity_type_from_name(name) == "culture":
            return None
        candidate_id = slugify(name)
        if candidate_id in excluded_ids:
            return None
        # create a stub for a polity that exists upstream but not locally
        stub = make_historical_stub(name, cache, [])
        entities[stub["id"]] = stub
        name_to_entity[name] = stub["id"]
        created.append(stub["id"])
        return stub

    for year in YEARS:
        raw = read_json(paths[year])
        grouped = group_features(year, raw.get("features", []), resolve)

        # merge hand-curated regional features from custom-features.geojson
        for custom in custom_features.get(year, []):
            cp = custom.get("properties", {}) or {}
            eid = aliases.get("entity_id_migrations", {}).get(cp.get("entity_id"), cp.get("entity_id"))
            entity = entities.get(eid)
            if not entity:
                continue
            custom_sources = [s for s in cp.get("source_ids", []) if s]
            if eid in grouped:
                grouped[eid]["source_ids"].update(custom_sources)
                continue
            geometry = clean_geometry(custom.get("geometry"))
            if not geometry:
                continue
            grouped[eid] = {
                "entity": entity,
                "geometries": [geometry],
                "border_precisions": [2],
                "subject_to": set(),
                "part_of": set(),
                "source_ids": set(custom_sources or [HB_SOURCE_ID]),
                "custom": True,
            }

        features: List[Dict[str, Any]] = []
        for eid, bucket in sorted(grouped.items()):
            entity = bucket["entity"]
            geometry = merge_geometries(bucket["geometries"])
            if not geometry:
                continue
            precisions = [value for value in bucket["border_precisions"] if value in (1, 2, 3)]
            border_precision = min(precisions) if precisions else 0
            boundary_precision, border_confidence = border_precision_to_confidence(border_precision)
            if bucket.get("custom"):
                boundary_precision = "historical_reconstruction"
                border_confidence = "medium"
            special = [s for s in extra_sources.get((year, eid), []) if s]
            source_ids = sorted({HB_SOURCE_ID, *special, *(bucket.get("source_ids") or [])})
            extra: Dict[str, Any] = {}
            if bucket["subject_to"]:
                clean_subjects = [s for s in bucket["subject_to"] if len(s) > 1 and not s.isdigit()]
                if clean_subjects:
                    extra["subject_to"] = sorted(clean_subjects)[0] if len(clean_subjects) == 1 else sorted(clean_subjects)
            if bucket["part_of"]:
                clean_part_of = [p for p in bucket["part_of"] if len(p) > 1 and not p.isdigit()]
                if clean_part_of:
                    extra["part_of"] = sorted(clean_part_of)[0] if len(clean_part_of) == 1 else sorted(clean_part_of)
            carried = extra_props.get((year, eid), {})
            extra.update({k: v for k, v in carried.items() if k in {"subject_to", "part_of"}})

            entity_type = entity.get("type", "state")
            if entity_type == "dependent_territory":
                layer_type = "dependent_territory"
            elif entity_type == "disputed_territory":
                layer_type = "disputed_territory"
            elif entity_type in {"empire", "kingdom", "civilization"}:
                layer_type = "sovereign_territory"
            elif extra.get("subject_to"):
                subj_str = str(extra["subject_to"]).lower()
                if "claim" in subj_str:
                    layer_type = "disputed_territory"
                else:
                    layer_type = "dependent_territory"
            else:
                layer_type = entity_type_to_layer_type(entity_type)

            props = feature_base_properties(
                entity,
                year,
                border_confidence,
                boundary_precision,
                border_precision if border_precision in (1, 2, 3) else 0,
                source_ids,
                layer_type=layer_type,
                extra=extra,
            )
            bbox = bbox_of(geometry)
            feature = {"type": "Feature", "id": props["id"], "properties": props, "geometry": geometry}
            if bbox:
                feature["bbox"] = bbox
            features.append(feature)
            coverage[eid].append(year)
        features.sort(key=lambda item: item["properties"]["entity_id"])
        collection = {
            "type": "FeatureCollection",
            "name": f"world-{year}",
            "year": year,
            "year_system": "astronomical",
            "source_ids": [HB_SOURCE_ID],
            "features": features,
        }
        write_json(DIST_SPATIAL_DIR / f"{year}.geojson", collection, compact=True)
        year_counts[year] = len(features)
        log(f"  ✓ {year:>6}: {len(features):>4} features")

    if created:
        log(f"  + created {len(created)} historical entity stubs: {', '.join(sorted(created)[:12])}"
            + (" …" if len(created) > 12 else ""))
    return coverage, year_counts


def build_modern_layer(
    ne_path: Path,
    entities: Dict[str, Dict[str, Any]],
    name_index: Dict[str, str],
    aliases: Dict[str, Any],
    legacy_names: Dict[str, str],
    cache: Dict[str, Any],
    excluded_ids: Set[str],
    excluded_names: Set[str],
) -> Tuple[Dict[str, List[int]], int, Dict[str, Dict[str, str]]]:
    raw = read_json(ne_path)
    grouped: Dict[str, Dict[str, Any]] = {}
    created: List[str] = []
    name_updates: Dict[str, Dict[str, str]] = {}
    name_to_entity = dict(legacy_names)

    def is_excluded(value: str) -> bool:
        return is_excluded_name(value, excluded_ids, excluded_names)

    def resolve(props: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        candidates = [
            (props.get("NAME_EN") or "").strip(),
            (props.get("ADMIN") or "").strip(),
            (props.get("NAME") or "").strip(),
        ]
        candidates = [name for name in candidates if name]
        if not candidates:
            return None
        for name in candidates:
            key = apply_aliases(name, aliases)
            if key in entities:
                return entities[key]
            if name in name_to_entity:
                eid = aliases.get("entity_id_migrations", {}).get(name_to_entity[name], name_to_entity[name])
                if eid not in excluded_ids and eid in entities:
                    return entities[eid]
            slug = slugify(name)
            if slug in entities:
                return entities[slug]
            if slug in name_index and name_index[slug] in entities:
                return entities[name_index[slug]]
        name = next((n for n in candidates if not is_excluded(n)), None)
        if not name:
            return None
        stub = make_modern_stub(props, cache)
        if stub["id"] in excluded_ids:
            return None
        entities[stub["id"]] = stub
        name_to_entity[name] = stub["id"]
        created.append(stub["id"])
        return stub

    for feature in raw.get("features", []):
        props = feature.get("properties", {}) or {}
        entity = resolve(props)
        if not entity:
            continue
        geometry = clean_geometry(feature.get("geometry"))
        if not geometry:
            continue
        eid = entity["id"]
        layer_type = ne_layer_type(props)
        bucket = grouped.setdefault(
            eid,
            {
                "entity": entity,
                "geometries": [],
                "layer_type": layer_type,
                "props": props,
            },
        )
        bucket["geometries"].append(geometry)
        # enrich names with natural earth built-in translations
        canonical = entity.setdefault("names", {}).setdefault("canonical", {})
        for lang, field in NE_NAME_FIELDS.items():
            value = props.get(field)
            if value and not canonical.get(lang):
                canonical[lang] = value
        name_updates[eid] = dict(canonical)

    features: List[Dict[str, Any]] = []
    coverage: Dict[str, List[int]] = collections.defaultdict(list)
    for eid, bucket in sorted(grouped.items()):
        entity = bucket["entity"]
        geometry = merge_geometries(bucket["geometries"])
        if not geometry:
            continue
        props = bucket["props"]
        layer_type = bucket["layer_type"]
        if entity.get("type") in {"dependent_territory", "disputed_territory"}:
            layer_type = entity["type"]
        elif entity.get("type") == "state" and layer_type == "dependent_territory":
            source_type = (props.get("TYPE") or "").strip()
            if source_type in {"Sovereign country", "Sovereignty"} or props.get("ADMIN") == props.get("SOVEREIGNT"):
                layer_type = "sovereign_territory"
        border_precision = 3 if layer_type in {"sovereign_territory", "dependent_territory"} else 2
        boundary_precision = "georeferenced_1_10m"
        confidence = "high" if border_precision == 3 else "medium"
        extra: Dict[str, Any] = {
            "iso_a2": (props.get("ISO_A2") or "").replace("-99", "") or None,
            "iso_a3": (props.get("ISO_A3") or "").replace("-99", "") or None,
            "continent": props.get("CONTINENT") or None,
            "subregion": props.get("SUBREGION") or None,
        }
        sovereign = (props.get("SOVEREIGNT") or "").strip()
        name_en = (props.get("NAME_EN") or "").strip()
        if layer_type == "dependent_territory" and sovereign and sovereign != name_en:
            extra["subject_to"] = sovereign
        feature_props = feature_base_properties(
            entity,
            MODERN_YEAR,
            confidence,
            boundary_precision,
            border_precision,
            [NE_SOURCE_ID],
            layer_type=layer_type,
            extra=extra,
        )
        feature_props["source_type"] = (props.get("TYPE") or "").strip() or None
        bbox = bbox_of(geometry)
        doc = {"type": "Feature", "id": feature_props["id"], "properties": feature_props, "geometry": geometry}
        if bbox:
            doc["bbox"] = bbox
        features.append(doc)
        coverage[eid].append(MODERN_YEAR)

    features.sort(key=lambda item: item["properties"]["entity_id"])
    write_json(
        DIST_SPATIAL_DIR / f"{MODERN_YEAR}.geojson",
        {
            "type": "FeatureCollection",
            "name": f"world-{MODERN_YEAR}",
            "year": MODERN_YEAR,
            "year_system": "astronomical",
            "source_ids": [NE_SOURCE_ID],
            "features": features,
        },
        compact=True,
    )
    if created:
        log(f"  + created {len(created)} modern entity stubs: {', '.join(sorted(created)[:12])}"
            + (" …" if len(created) > 12 else ""))
    log(f"  ✓ {MODERN_YEAR:>6}: {len(features):>4} features (Natural Earth 1:10m)")
    return coverage, len(features), name_updates


def write_source_manifest(hb_paths: Dict[int, Path], ne_path: Path) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "sources": {
            HB_SOURCE_ID: {
                "repository": "https://github.com/aourednik/historical-basemaps",
                "commit": HB_COMMIT,
                "license": "GPL-3.0",
                "files": {
                    str(year): {
                        "url": HB_RAW_URL.format(filename=f"world_{year}.geojson"),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                    for year, path in sorted(hb_paths.items())
                },
            },
            NE_SOURCE_ID: {
                "repository": "https://github.com/nvkelso/natural-earth-vector",
                "version": "v5.1.2",
                "snapshot": "2026-11-05",
                "license": "Public Domain (CC0)",
                "files": {
                    "ne_10m_admin_0_countries.geojson": {
                        "url": NE_URL,
                        "sha256": sha256_file(ne_path),
                        "bytes": ne_path.stat().st_size,
                    }
                },
            },
        },
    }
    write_json(DATA_DIR / "sources" / "manifests" / "cartographic.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hb-dir", type=Path, default=Path("/tmp/opencode/hb"),
                        help="Cache directory for historical-basemaps GeoJSON files")
    parser.add_argument("--ne-path", type=Path, default=Path("/tmp/opencode/ne_10m_admin_0_countries.geojson"),
                        help="Path to Natural Earth 1:10m Admin-0 GeoJSON")
    args = parser.parse_args()

    log("=" * 78)
    log("BUILD SPATIAL LAYERS — historical-basemaps + Natural Earth 1:10m")
    log("=" * 78)

    DIST_SPATIAL_DIR.mkdir(parents=True, exist_ok=True)
    hb_paths, ne_path = ensure_sources(args.hb_dir, args.ne_path)

    entities = load_entities()
    known_entity_ids = set(entities)
    known_entities = len(entities)
    aliases = load_alias_config()
    excluded_ids, excluded_names = load_exclusions()
    name_index = build_name_index(entities)
    legacy_names, extra_sources, extra_props = load_legacy_context()
    cache = read_json(DATA_DIR / "cache" / "multilingual_cache.json")

    log(f"  • {known_entities} existing entities")
    log(f"  • {len(legacy_names)} legacy source-name ↦ entity mappings")
    log(f"  • {len(extra_sources)} years with regional source citations to preserve")

    custom_features = load_custom_features()
    coverage, year_counts = build_historical_layers(
        hb_paths, entities, name_index, aliases, legacy_names,
        extra_sources, extra_props, custom_features, cache,
        excluded_ids, excluded_names
    )
    modern_coverage, modern_count, modern_names = build_modern_layer(
        ne_path, entities, name_index, aliases, legacy_names, cache,
        excluded_ids, excluded_names
    )
    for eid, years in modern_coverage.items():
        coverage[eid].extend(years)

    # persist newly discovered entities so next pipeline step can normalise them
    new_entities = [entity for eid, entity in entities.items() if eid not in known_entity_ids]
    for entity in new_entities:
        write_json(entity_path(entity["id"], entity.get("type", "state")), entity)

    coverage_out = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "years": YEARS + [MODERN_YEAR],
        "year_feature_counts": {str(year): count for year, count in sorted(year_counts.items())},
        "modern_year_feature_count": modern_count,
        "entities": {eid: sorted(set(years)) for eid, years in sorted(coverage.items())},
    }
    write_json(DATA_DIR / "cache" / "spatial-coverage.json", coverage_out)
    write_json(DATA_DIR / "cache" / "modern-names.json", {
        "schema_version": SCHEMA_VERSION,
        "generated_at": TODAY,
        "source_id": NE_SOURCE_ID,
        "names": modern_names,
    })

    write_source_manifest(hb_paths, ne_path)

    log("-" * 78)
    log(f"  Total features: {sum(year_counts.values()) + modern_count}")
    log(f"  Entities with geometry: {len(coverage)}")
    log(f"  New entity stubs written: {len(new_entities)}")
    log("✅ Spatial layers rebuilt with per-feature border precision.")


if __name__ == "__main__":
    main()
