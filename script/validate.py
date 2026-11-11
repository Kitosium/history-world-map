#!/usr/bin/env python3
"""Validate the dataset and the compiled catalog.

The validator is read-only. It checks the invariants that the rest of the
pipeline relies on:

* entity documents: required fields, chronology, taxonomy membership, source
  references, language keys and confidence consistency;
* spatial layers: GeoJSON structure, geometry validity, unique feature ids,
  one dissolved feature per entity per year, valid years and provenance;
* catalog: timeline layers, feature/entity counts, entity and source indexes,
  statistics and the dataset manifest.

Exit code is non-zero when any error is found. ``--strict`` also treats
warnings as errors.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DATA_DIR,
    DIST_CATALOG_DIR,
    DIST_SPATIAL_DIR,
    SOURCES_DIR,
    entity_path,
    iter_entity_files,
    load_exclusions,
    read_json,
    sha256_file,
)

LANG_KEY = re.compile(r"^[a-z]{2}(-[A-Za-z0-9]+)*$")
ENTITY_ID = re.compile(r"^[^\s/\\]+$")
SOURCE_ID = re.compile(r"^src-[a-z0-9-]+$")
WIKIDATA_ID = re.compile(r"^Q[0-9]+$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

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
FORBIDDEN_DESCRIPTION = (
    "disambiguation",
    "định hướng",
    "wikimedia disambiguation",
    "trang định hướng",
)

ALLOWED_GEOMETRY = {"Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "MultiPoint", "GeometryCollection"}


class Report:
    def __init__(self) -> None:
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        self.counts = collections.Counter()

    def error(self, path: Any, message: str) -> None:
        self.errors.append((str(path), message))

    def warn(self, path: Any, message: str) -> None:
        self.warnings.append((str(path), message))

    def summary(self, strict: bool) -> int:
        print()
        print("=" * 78)
        print("DATA VALIDATION SUMMARY")
        print("=" * 78)
        for label, value in sorted(self.counts.items()):
            print(f"  • {label}: {value}")
        print(f"  • errors: {len(self.errors)}")
        print(f"  • warnings: {len(self.warnings)}")
        if self.errors:
            print("\nERRORS")
            for path, message in self.errors[:200]:
                print(f"  ✗ {path}: {message}")
            if len(self.errors) > 200:
                print(f"  … and {len(self.errors) - 200} more errors")
        if self.warnings:
            print("\nWARNINGS")
            for path, message in self.warnings[:100]:
                print(f"  ! {path}: {message}")
            if len(self.warnings) > 100:
                print(f"  … and {len(self.warnings) - 100} more warnings")
        failed = bool(self.errors) or (strict and bool(self.warnings))
        print()
        print("❌ Validation failed." if failed else "✅ Validation passed.")
        return 1 if failed else 0


def load_taxonomies(report: Report) -> Tuple[Set[str], Dict[str, int], Set[str]]:
    types: Set[str] = set()
    tier_ranks: Dict[str, int] = {}
    layer_types: Set[str] = set()

    path = DATA_DIR / "taxonomies" / "entity-types.json"
    if not path.exists():
        report.error(path, "missing taxonomy file")
    else:
        try:
            types = set((read_json(path).get("types") or {}).keys())
            report.counts["entity types"] = len(types)
        except Exception as exc:
            report.error(path, f"cannot parse taxonomy: {exc}")

    path = DATA_DIR / "taxonomies" / "source-tiers.json"
    if not path.exists():
        report.error(path, "missing taxonomy file")
    else:
        try:
            tiers = read_json(path).get("tiers") or {}
            tier_ranks = {name: int(meta.get("rank", 99)) for name, meta in tiers.items()}
            report.counts["source tiers"] = len(tier_ranks)
        except Exception as exc:
            report.error(path, f"cannot parse taxonomy: {exc}")

    path = DATA_DIR / "taxonomies" / "layer-types.json"
    if not path.exists():
        report.error(path, "missing taxonomy file")
    else:
        try:
            layer_types = set((read_json(path).get("types") or {}).keys())
        except Exception as exc:
            report.error(path, f"cannot parse taxonomy: {exc}")

    return types, tier_ranks, layer_types


def load_sources(report: Report, tier_ranks: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
    sources: Dict[str, Dict[str, Any]] = {}
    for path in sorted(SOURCES_DIR.rglob("*.json")):
        try:
            doc = read_json(path)
        except Exception as exc:
            report.error(path, f"invalid JSON: {exc}")
            continue
        sid = doc.get("id")
        if not sid:
            if path.parent.name != "manifests":
                report.error(path, "missing source id")
            continue
        if not SOURCE_ID.match(sid):
            report.error(path, f"invalid source id: {sid}")
        if sid in sources:
            report.error(path, f"duplicate source id: {sid}")
        sources[sid] = doc

        if not isinstance(doc.get("schema_version"), str):
            report.warn(path, "missing schema_version")
        title = (doc.get("title") or {}).get("canonical") or {}
        if not isinstance(title, dict) or not title:
            report.error(path, "missing title.canonical")
        else:
            for lang in title:
                if not LANG_KEY.match(lang):
                    report.error(path, f"invalid language key: {lang}")

        tier = (doc.get("critique_and_reliability") or {}).get("tier")
        if not tier:
            report.error(path, "missing critique_and_reliability.tier")
        elif tier_ranks and tier not in tier_ranks:
            report.error(path, f"unknown tier: {tier}")

        for entry in doc.get("digital_access", []) or []:
            entry = entry or {}
            url = entry.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                report.error(path, f"invalid digital_access URL: {url!r}")
            for key in ("page_url", "license_url"):
                value = entry.get(key)
                if value and (not isinstance(value, str) or not value.startswith(("http://", "https://"))):
                    report.error(path, f"invalid digital_access.{key}: {value!r}")
            digest = entry.get("sha256")
            if digest and (not isinstance(digest, str) or not SHA256.match(digest)):
                report.error(path, f"invalid digital_access.sha256: {digest!r}")
            size = entry.get("bytes")
            if size is not None and (not isinstance(size, int) or size < 0):
                report.error(path, f"invalid digital_access.bytes: {size!r}")
            local_file = entry.get("local_file")
            if local_file:
                local_path = DATA_DIR.parent / local_file
                if not local_path.exists():
                    report.error(path, f"missing local source file: {local_file}")
                else:
                    if size is not None and local_path.stat().st_size != size:
                        report.error(path, f"local source file size mismatch: {local_file}")
                    if digest and sha256_file(local_path) != digest:
                        report.error(path, f"local source file sha256 mismatch: {local_file}")

        license_info = doc.get("license") or {}
        if not license_info.get("name") and not license_info.get("spdx"):
            report.warn(path, "no license information")

        verified = doc.get("last_verified")
        if verified and not DATE.match(str(verified)):
            report.error(path, f"last_verified is not an ISO date: {verified}")

    report.counts["sources"] = len(sources)
    return sources


def validate_pdf_manifest(report: Report, sources: Dict[str, Dict[str, Any]]) -> None:
    path = SOURCES_DIR / "manifests" / "pdf.json"
    if not path.exists():
        report.warn(path, "missing PDF manifest")
        return
    try:
        doc = read_json(path)
    except Exception as exc:
        report.error(path, f"invalid JSON: {exc}")
        return
    downloads = doc.get("downloads")
    if not isinstance(downloads, list):
        report.error(path, "downloads must be a list")
        return
    seen_ids: Set[str] = set()
    seen_paths: Set[str] = set()
    total_bytes = 0
    for entry in downloads:
        entry = entry or {}
        entry_id = entry.get("id")
        if not entry_id:
            report.error(path, "download entry missing id")
        elif entry_id in seen_ids:
            report.error(path, f"duplicate download id: {entry_id}")
        else:
            seen_ids.add(entry_id)
        source_id = entry.get("source_id")
        if source_id not in sources:
            report.error(path, f"{entry_id}: unknown source_id: {source_id!r}")
        url = entry.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            report.error(path, f"{entry_id}: invalid URL: {url!r}")
        local_file = entry.get("path")
        if not local_file:
            report.error(path, f"{entry_id}: missing path")
            continue
        if local_file in seen_paths:
            report.error(path, f"{entry_id}: duplicate path: {local_file}")
        seen_paths.add(local_file)
        local_path = DATA_DIR.parent / local_file
        if not local_path.exists():
            report.error(path, f"{entry_id}: missing file: {local_file}")
            continue
        size = entry.get("bytes")
        if not isinstance(size, int) or size < 0:
            report.error(path, f"{entry_id}: invalid bytes: {size!r}")
        elif local_path.stat().st_size != size:
            report.error(path, f"{entry_id}: file size mismatch: {local_file}")
        else:
            total_bytes += size
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not SHA256.match(digest):
            report.error(path, f"{entry_id}: invalid sha256: {digest!r}")
        elif sha256_file(local_path) != digest:
            report.error(path, f"{entry_id}: sha256 mismatch: {local_file}")
        pages = entry.get("pages")
        if pages is not None and (not isinstance(pages, int) or pages < 1):
            report.error(path, f"{entry_id}: invalid pages: {pages!r}")
    report.counts["source PDFs"] = len(downloads)
    report.counts["source PDF bytes"] = total_bytes


def validate_language_map(path: Path, label: str, mapping: Any, report: Report) -> None:
    if not isinstance(mapping, dict):
        report.error(path, f"{label} must be an object")
        return
    for lang, value in mapping.items():
        if not LANG_KEY.match(lang):
            report.error(path, f"{label}: invalid language key {lang!r}")
        if not isinstance(value, str) or not value.strip():
            report.error(path, f"{label}.{lang} must be a non-empty string")


def validate_date_point(path: Path, label: str, value: Any, report: Report) -> Optional[int]:
    if not isinstance(value, dict):
        report.error(path, f"{label} must be an object")
        return None
    year = value.get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        report.error(path, f"{label}.year must be an integer")
        return None
    if not -3500 <= year <= 2026:
        report.error(path, f"{label}.year out of range: {year}")
    precision = value.get("precision")
    if precision and precision not in {"year", "month", "day", "decade", "century"}:
        report.warn(path, f"{label}.precision has unusual value: {precision}")
    return year


def check_boilerplate(path: Path, text: Any, report: Report) -> None:
    if not isinstance(text, str) or not text:
        return
    low = text.lower()
    for token in FORBIDDEN_DESCRIPTION:
        if token in low:
            report.error(path, f"forbidden disambiguation text: {token}")
    if len(text) > 80:
        for token in FORBIDDEN_BOILERPLATES:
            if token in low:
                report.error(path, f"forbidden boilerplate text: {token}")


def validate_entity(
    path: Path,
    doc: Dict[str, Any],
    entity_types: Set[str],
    sources: Dict[str, Dict[str, Any]],
    tier_ranks: Dict[str, int],
    snapshot_years: Set[int],
    report: Report,
) -> None:
    eid = doc.get("id")
    if not eid:
        report.error(path, "missing id")
        return
    if path.stem != eid:
        report.error(path, f"id {eid!r} does not match filename")
    if not ENTITY_ID.match(eid):
        report.error(path, f"invalid entity id: {eid!r}")

    etype = doc.get("type")
    if entity_types and etype not in entity_types:
        report.error(path, f"unknown entity type: {etype!r}")
    expected_dir = etype if isinstance(etype, str) else "state"
    if path.parent.name != expected_dir:
        report.error(
            path,
            f"entity is in {path.parent.name!r} but type requires {expected_dir!r}",
        )
    if path != entity_path(eid, expected_dir):
        report.error(path, "entity is not at its canonical type path")

    names = doc.get("names") or {}
    canonical = names.get("canonical")
    validate_language_map(path, "names.canonical", canonical, report)
    if isinstance(canonical, dict) and canonical:
        if not canonical.get("vi") and not canonical.get("en"):
            report.warn(path, "canonical names lack both vi and en")
    aliases = names.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, dict):
            report.error(path, "names.aliases must be an object")
        else:
            for lang, values in aliases.items():
                if not LANG_KEY.match(lang):
                    report.error(path, f"names.aliases: invalid language key {lang!r}")
                if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                    report.error(path, f"names.aliases.{lang} must be a list of strings")

    descriptions = doc.get("descriptions") or {}
    validate_language_map(path, "descriptions", descriptions, report)
    for lang, text in descriptions.items():
        check_boilerplate(path, text, report)

    wikidata_id = doc.get("wikidata_id")
    if wikidata_id and not WIKIDATA_ID.match(str(wikidata_id)):
        report.error(path, f"invalid wikidata_id: {wikidata_id!r}")

    existence = doc.get("existence") or {}
    from_year = validate_date_point(path, "existence.from", existence.get("from"), report)
    to_year = validate_date_point(path, "existence.to", existence.get("to"), report)
    if from_year is not None and to_year is not None and from_year > to_year:
        report.error(path, f"reversed chronology: {from_year} > {to_year}")
    status = existence.get("status")
    if status not in {"historical", "active"}:
        report.error(path, f"invalid existence.status: {status!r}")
    basis = existence.get("basis")
    if basis not in {
        "documented",
        "single_observation",
        "cartographic_observation",
        "cartographic_observation_range",
        "modern_snapshot",
        "unknown",
    }:
        report.error(path, f"invalid existence.basis: {basis!r}")
    for key in ("continuity_asserted", "is_approximate"):
        if key in existence and not isinstance(existence[key], bool):
            report.error(path, f"existence.{key} must be boolean")

    observed = doc.get("observed_periods")
    if not isinstance(observed, list):
        report.error(path, "observed_periods must be a list")
        observed = []
    else:
        if observed != sorted(set(observed)):
            report.error(path, "observed_periods must be sorted and unique")
        for year in observed:
            if not isinstance(year, int):
                report.error(path, f"observed_periods contains non-integer: {year!r}")
            elif snapshot_years and year not in snapshot_years:
                report.error(path, f"observed year has no spatial layer: {year}")

    source_ids = doc.get("source_ids")
    if not isinstance(source_ids, list):
        report.error(path, "source_ids must be a list")
        source_ids = []
    for sid in source_ids:
        if sid not in sources:
            report.error(path, f"unknown source id: {sid}")

    provenance = doc.get("provenance") or {}
    for key in ("names", "existence", "boundaries"):
        values = provenance.get(key, [])
        if not isinstance(values, list):
            report.error(path, f"provenance.{key} must be a list")
            continue
        for sid in values:
            if sid not in sources:
                report.error(path, f"provenance.{key}: unknown source id: {sid}")

    spatial = doc.get("spatial_coverage") or {}
    spatial_years = spatial.get("observed_years", [])
    if not isinstance(spatial_years, list):
        report.error(path, "spatial_coverage.observed_years must be a list")
        spatial_years = []
    if spatial_years:
        if spatial_years != sorted(set(spatial_years)):
            report.error(path, "spatial_coverage.observed_years must be sorted and unique")
        if spatial.get("first_observed_year") != spatial_years[0]:
            report.error(path, "spatial_coverage.first_observed_year is inconsistent")
        if spatial.get("last_observed_year") != spatial_years[-1]:
            report.error(path, "spatial_coverage.last_observed_year is inconsistent")
    if spatial.get("boundary_confidence") not in {"low", "medium", "high", None}:
        report.error(path, f"invalid boundary_confidence: {spatial.get('boundary_confidence')!r}")
    border_precision = spatial.get("border_precision")
    if border_precision is not None and border_precision not in {0, 1, 2, 3}:
        report.error(path, f"invalid border_precision: {border_precision!r}")

    for reference in doc.get("boundary_references", []) or []:
        file_path = (reference or {}).get("file_path")
        if file_path and not (DATA_DIR.parent / file_path).exists():
            report.error(path, f"boundary reference points to a missing file: {file_path}")

    confidence = doc.get("confidence")
    if confidence not in {"low", "medium", "high"}:
        report.error(path, f"invalid confidence: {confidence!r}")
    if not spatial_years and confidence == "high":
        report.error(path, "high confidence without compiled geometry")

    if confidence == "high":
        ranks = []
        for sid in source_ids:
            tier = (sources.get(sid, {}).get("critique_and_reliability") or {}).get("tier")
            if tier in tier_ranks:
                ranks.append(tier_ranks[tier])
        if ranks and min(ranks) > 3:
            report.error(
                path,
                f"high confidence but best source tier rank is {min(ranks)} (needs <= 3)",
            )


def check_geometry(geometry: Any, path: Path, feature_id: str, report: Report) -> None:
    if not isinstance(geometry, dict):
        report.error(path, f"{feature_id}: missing geometry")
        return
    gtype = geometry.get("type")
    if gtype not in ALLOWED_GEOMETRY:
        report.error(path, f"{feature_id}: unsupported geometry type {gtype!r}")
        return
    coords = geometry.get("coordinates")
    if gtype != "GeometryCollection" and not coords:
        report.error(path, f"{feature_id}: empty coordinates")

    def walk(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value[:2]):
                lon, lat = value[0], value[1]
                if not (math.isfinite(lon) and math.isfinite(lat)):
                    report.error(path, f"{feature_id}: non-finite coordinate")
                elif not (-180.000001 <= lon <= 180.000001):
                    report.error(path, f"{feature_id}: longitude out of range: {lon}")
                elif not (-90.000001 <= lat <= 90.000001):
                    report.error(path, f"{feature_id}: latitude out of range: {lat}")
            else:
                for item in value:
                    walk(item)

    walk(coords)

    if gtype == "Polygon":
        polygons = [coords]
    elif gtype == "MultiPolygon":
        polygons = coords
    else:
        polygons = []
    for polygon in polygons:
        if not polygon:
            report.error(path, f"{feature_id}: empty polygon")
            continue
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                report.error(path, f"{feature_id}: ring has fewer than 4 positions")
                continue
            if ring[0] != ring[-1]:
                report.error(path, f"{feature_id}: ring is not closed")


def scan_spatial_layers(
    report: Report,
    entities: Dict[str, Dict[str, Any]],
    sources: Dict[str, Dict[str, Any]],
    layer_types: Set[str],
) -> Tuple[Set[int], Dict[str, Set[int]], Dict[int, Dict[str, Any]]]:
    years: Set[int] = set()
    coverage: Dict[str, Set[int]] = collections.defaultdict(set)
    layer_stats: Dict[int, Dict[str, Any]] = {}

    for path in sorted(DIST_SPATIAL_DIR.glob("*.geojson")):
        try:
            year = int(path.stem)
        except ValueError:
            report.error(path, "layer filename is not a year")
            continue
        years.add(year)
        try:
            doc = read_json(path)
        except Exception as exc:
            report.error(path, f"invalid JSON: {exc}")
            continue
        if doc.get("type") != "FeatureCollection":
            report.error(path, "root type must be FeatureCollection")
        features = doc.get("features")
        if not isinstance(features, list):
            report.error(path, "features must be a list")
            continue

        feature_ids: Set[str] = set()
        entity_ids_in_layer: Dict[str, int] = collections.Counter()
        confidence: Dict[str, int] = collections.Counter()
        for feature in features:
            props = (feature or {}).get("properties") or {}
            fid = props.get("id")
            if not fid:
                report.error(path, "feature is missing properties.id")
                fid = "<unknown>"
            elif fid in feature_ids:
                report.error(path, f"duplicate feature id: {fid}")
            feature_ids.add(fid)

            eid = props.get("entity_id")
            if not eid:
                report.error(path, f"{fid}: missing entity_id")
            elif eid not in entities:
                report.error(path, f"{fid}: entity_id has no entity document: {eid}")
            else:
                entity_ids_in_layer[eid] += 1
                coverage[eid].add(year)
                expected_type = (entities[eid].get("type") or "state")
                if props.get("type") != expected_type:
                    report.error(
                        path,
                        f"{fid}: feature type {props.get('type')!r} != entity type {expected_type!r}",
                    )

            if props.get("valid_year") != year:
                report.error(path, f"{fid}: valid_year {props.get('valid_year')!r} != {year}")

            layer_type = props.get("layer_type")
            if layer_types and layer_type not in layer_types:
                report.warn(path, f"{fid}: unknown layer_type {layer_type!r}")

            source_ids = props.get("source_ids") or []
            if not source_ids:
                report.error(path, f"{fid}: missing source_ids")
            for sid in source_ids:
                if sid not in sources:
                    report.error(path, f"{fid}: unknown source id: {sid}")

            conf = props.get("confidence")
            if conf not in {"low", "medium", "high"}:
                report.error(path, f"{fid}: invalid confidence {conf!r}")
            else:
                confidence[conf] += 1
            if props.get("boundary_confidence") not in {"low", "medium", "high"}:
                report.error(path, f"{fid}: invalid boundary_confidence")
            bp = props.get("border_precision")
            if bp not in {0, 1, 2, 3}:
                report.error(path, f"{fid}: invalid border_precision {bp!r}")

            check_geometry((feature or {}).get("geometry"), path, fid, report)

        duplicates = {eid: count for eid, count in entity_ids_in_layer.items() if count > 1}
        for eid, count in sorted(duplicates.items())[:5]:
            report.error(path, f"entity {eid} appears {count} times (not dissolved)")
        if len(duplicates) > 5:
            report.error(path, f"{len(duplicates) - 5} more undissolved entities")

        layer_stats[year] = {
            "feature_count": len(features),
            "entity_count": len(entity_ids_in_layer),
            "confidence_counts": dict(sorted(confidence.items())),
        }

    report.counts["spatial layers"] = len(layer_stats)
    report.counts["spatial features"] = sum(s["feature_count"] for s in layer_stats.values())
    return years, coverage, layer_stats


def validate_catalog(
    report: Report,
    entity_ids: Set[str],
    source_ids: Set[str],
    years: Set[int],
    layer_stats: Dict[int, Dict[str, Any]],
) -> None:
    entities_path = DIST_CATALOG_DIR / "entities-index.json"
    if not entities_path.exists():
        report.error(entities_path, "missing catalog file")
    else:
        try:
            index = read_json(entities_path)
        except Exception as exc:
            report.error(entities_path, f"invalid JSON: {exc}")
            index = []
        seen: Set[str] = set()
        for item in index:
            eid = item.get("id")
            if eid in seen:
                report.error(entities_path, f"duplicate entity id: {eid}")
            seen.add(eid)
            if eid not in entity_ids:
                report.error(entities_path, f"catalog entity has no document: {eid}")
            declared_path = item.get("path")
            expected_path = entity_path(
                eid, item.get("type", "state")
            ).relative_to(DATA_DIR.parent).as_posix()
            if not declared_path:
                report.error(entities_path, f"{eid}: missing catalog path")
            elif declared_path != expected_path:
                report.error(
                    entities_path,
                    f"{eid}: catalog path {declared_path!r} != canonical {expected_path!r}",
                )
            elif not (DATA_DIR.parent / declared_path).exists():
                report.error(entities_path, f"{eid}: catalog path does not exist: {declared_path}")
            if not item.get("name_vi") or not item.get("name_en"):
                report.error(entities_path, f"{eid}: missing vi/en name")
            if item.get("type") not in {"state", "kingdom", "empire", "civilization",
                                        "dependent_territory", "disputed_territory", "dynasty"}:
                report.warn(entities_path, f"{eid}: unexpected type {item.get('type')!r}")
        missing = entity_ids - seen
        if missing:
            report.error(entities_path, f"{len(missing)} entities missing from catalog")

    sources_path = DIST_CATALOG_DIR / "sources-index.json"
    if not sources_path.exists():
        report.error(sources_path, "missing catalog file")
    else:
        try:
            index = read_json(sources_path)
        except Exception as exc:
            report.error(sources_path, f"invalid JSON: {exc}")
            index = []
        indexed = {item.get("id") for item in index}
        if indexed != source_ids:
            report.error(sources_path, "source index does not match source records")

    timeline_path = DIST_CATALOG_DIR / "timeline.json"
    if not timeline_path.exists():
        report.error(timeline_path, "missing catalog file")
    else:
        try:
            timeline = read_json(timeline_path)
        except Exception as exc:
            report.error(timeline_path, f"invalid JSON: {exc}")
            timeline = []
        timeline_years = set()
        for entry in timeline:
            year = entry.get("year")
            if year not in years:
                report.error(timeline_path, f"timeline year has no layer: {year}")
                continue
            timeline_years.add(year)
            expected = layer_stats.get(year, {})
            if entry.get("feature_count") != expected.get("feature_count"):
                report.error(
                    timeline_path,
                    f"{year}: feature_count {entry.get('feature_count')} != {expected.get('feature_count')}",
                )
            if entry.get("entity_count") != expected.get("entity_count"):
                report.error(
                    timeline_path,
                    f"{year}: entity_count {entry.get('entity_count')} != {expected.get('entity_count')}",
                )
        if timeline_years != years:
            report.error(timeline_path, f"timeline years differ from layers: {sorted(years - timeline_years)}")

    stats_path = DIST_CATALOG_DIR / "stats.json"
    if not stats_path.exists():
        report.error(stats_path, "missing catalog file")
    else:
        try:
            stats = read_json(stats_path)
        except Exception as exc:
            report.error(stats_path, f"invalid JSON: {exc}")
            stats = {}
        if (stats.get("entities") or {}).get("total") != len(entity_ids):
            report.error(stats_path, "entity total does not match documents")
        if (stats.get("spatial") or {}).get("features") != sum(s["feature_count"] for s in layer_stats.values()):
            report.error(stats_path, "spatial feature total does not match layers")

    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        report.error(manifest_path, "missing dataset manifest")
    else:
        try:
            manifest = read_json(manifest_path)
        except Exception as exc:
            report.error(manifest_path, f"invalid JSON: {exc}")
            manifest = {}
        counts = manifest.get("counts") or {}
        if counts.get("entities") != len(entity_ids):
            report.error(manifest_path, "manifest entity count is stale")
        if counts.get("sources") != len(source_ids):
            report.error(manifest_path, "manifest source count is stale")
        if counts.get("spatial_layers") != len(years):
            report.error(manifest_path, "manifest layer count is stale")
        if counts.get("spatial_features") != sum(s["feature_count"] for s in layer_stats.values()):
            report.error(manifest_path, "manifest feature count is stale")
        snapshot = set((manifest.get("temporal_coverage") or {}).get("snapshot_years") or [])
        if snapshot != years:
            report.error(manifest_path, "manifest snapshot years differ from layers")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the historical atlas dataset.")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    report = Report()
    print("=" * 78)
    print("DATA VALIDATION")
    print("=" * 78)

    entity_types, tier_ranks, layer_types = load_taxonomies(report)
    sources = load_sources(report, tier_ranks)
    validate_pdf_manifest(report, sources)

    excluded_ids, _excluded_slugs = load_exclusions()
    entities: Dict[str, Dict[str, Any]] = {}
    entity_files: Dict[str, Path] = {}
    for path in iter_entity_files():
        try:
            doc = read_json(path)
        except Exception as exc:
            report.error(path, f"invalid JSON: {exc}")
            continue
        eid = doc.get("id") or path.stem
        if eid in excluded_ids:
            report.error(path, f"excluded entity was re-created: {eid}")
        if eid in entities:
            report.error(path, f"duplicate entity id across directories: {eid}")
            continue
        entities[eid] = doc
        entity_files[eid] = path

    years, coverage, layer_stats = scan_spatial_layers(
        report, entities, sources, layer_types
    )
    report.counts["entities"] = len(entities)
    report.counts["excluded entities"] = len(excluded_ids)

    for eid, doc in sorted(entities.items()):
        path = entity_files[eid]
        validate_entity(
            path,
            doc,
            entity_types,
            sources,
            tier_ranks,
            years,
            report,
        )
        spatial_years = set((doc.get("spatial_coverage") or {}).get("observed_years") or [])
        compiled_years = coverage.get(eid, set())
        if spatial_years != compiled_years:
            report.error(
                path,
                f"spatial_coverage differs from compiled layers "
                f"(document {sorted(spatial_years)[:5]}…, layers {sorted(compiled_years)[:5]}…)",
            )

    validate_catalog(report, set(entities), set(sources), years, layer_stats)
    return report.summary(args.strict)


if __name__ == "__main__":
    sys.exit(main())
