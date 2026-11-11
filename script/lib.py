#!/usr/bin/env python3
"""Shared helpers for the World History Atlas data pipeline.

The module is intentionally dependency-free (Python standard library only) so
that the data can be rebuilt and validated on any machine with Python 3.10+.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ENTITY_ROOT = DATA_DIR / "entities"
# backwards-compatible alias: canonical code should use ENTITY_ROOT / helpers.
ENTITIES_DIR = ENTITY_ROOT
ENTITY_NON_ENTITY_DIRS = {"dynasties"}
SOURCES_DIR = DATA_DIR / "sources"
ALIASES_DIR = DATA_DIR / "aliases"
SCHEMAS_DIR = DATA_DIR / "schemas"
TAXONOMIES_DIR = DATA_DIR / "taxonomies"
DIST_DIR = DATA_DIR / "dist"
DIST_SPATIAL_DIR = DIST_DIR / "spatial" / "by-year"
DIST_CATALOG_DIR = DIST_DIR / "catalog"

TODAY = "2026-11-05"
SCHEMA_VERSION = "1.3.0"

# ---------------------------------------------------------------------------
# canonical source metadata
# ---------------------------------------------------------------------------

SOURCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "src-basemaps": {
        "type": "historical_atlas",
        "tier": "tier_4_scholarly_atlas",
        "title": {
            "vi": "Historical Basemaps: Ranh giới Chính trị Toàn cầu (4000 TCN - 2010 SCN)",
            "en": "Historical Basemaps: Georeferenced Global Political Boundaries (4000 BCE - 2010 CE)",
        },
        "creators": [
            {
                "name": "André Ourednik",
                "role": "cartographer",
                "affiliation": "University of Lausanne / EPFL",
            }
        ],
        "publication": {
            "publisher": "Open Source Historical GIS",
            "year": 2026,
            "edition": "master (commit 4b5039e)",
            "language": "en",
            "volumes": "51 lớp năm, 4000 TCN - 2010 SCN",
            "notes": "GeoJSON theo từng năm; trường NAME, SUBJECTO, PARTOF và BORDERPRECISION (1-3).",
        },
        "digital_access": [
            {
                "label": "GitHub repository",
                "url": "https://github.com/aourednik/historical-basemaps",
                "access_type": "open_access",
                "format": "geojson",
                "provider": "GitHub",
            },
            {
                "label": "Commit 4b5039e (bản dùng trong dataset)",
                "url": "https://github.com/aourednik/historical-basemaps/commit/4b5039e50d8d2464b065bd76ad6086cd4597108d",
                "access_type": "open_access",
                "format": "html",
                "provider": "GitHub",
            },
            {
                "label": "index.json (danh mục lớp theo năm)",
                "url": "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/index.json",
                "access_type": "open_access",
                "format": "json",
                "provider": "GitHub",
            },
        ],
        "license": {
            "name": "GNU General Public License v3.0",
            "spdx": "GPL-3.0",
            "url": "https://www.gnu.org/licenses/gpl-3.0.html",
        },
        "coverage": {
            "temporal": "4000 BCE - 2010 CE",
            "spatial": "global",
            "geometry": "generalised polygons suitable for world/continental scale",
            "border_precision": "BORDERPRECISION 1-3 preserved per feature",
        },
        "notes": (
            "Bản đồ biên giới lịch sử được georeference theo từng mốc năm, "
            "gồm cả các vùng văn hóa và bộ tộc. Dự án tự nhận là work in "
            "progress và yêu cầu đối chiếu với nguồn khác trước khi dùng cho "
            "nghiên cứu. Dataset chỉ dùng các polygon chính trị sau khi đã lọc "
            "các lớp văn hóa/bộ tộc; giấy phép GPL-3.0 áp dụng cho dữ liệu "
            "gốc. Không có PDF chính thức cho bộ dữ liệu này."
        ),
    },
    "src-natural-earth": {
        "type": "authoritative_cartography",
        "tier": "tier_3_authoritative_cartography",
        "title": {
            "vi": "Natural Earth Vector 1:10.000.000 - Ranh giới Quốc gia (bản chụp 2026)",
            "en": "Natural Earth Vector 1:10m Admin-0 Countries (2026 snapshot)",
        },
        "creators": [
            {
                "name": "Natural Earth",
                "role": "compiler",
                "affiliation": "NACIS / North American Cartographic Information Society",
            }
        ],
        "publication": {
            "publisher": "Natural Earth Data",
            "year": 2022,
            "edition": "v5.1.2 (Admin-0, 1:10m)",
            "snapshot_date": "2026-11-05",
            "language": "en",
            "volumes": "Admin-0 countries, 1:10m",
            "notes": "Bản chụp ngày 2026-11-05 từ nhánh master của natural-earth-vector.",
        },
        "digital_access": [
            {
                "label": "Natural Earth Data",
                "url": "https://www.naturalearthdata.com/",
                "access_type": "open_access",
                "format": "html",
                "provider": "Natural Earth",
            },
            {
                "label": "Admin-0 countries, 1:10m",
                "url": "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/",
                "access_type": "open_access",
                "format": "shapefile/geojson",
                "provider": "Natural Earth",
            },
            {
                "label": "natural-earth-vector (GitHub)",
                "url": "https://github.com/nvkelso/natural-earth-vector",
                "access_type": "open_access",
                "format": "geojson",
                "provider": "GitHub",
            },
            {
                "label": "natural-earth-vector releases",
                "url": "https://github.com/nvkelso/natural-earth-vector/releases",
                "access_type": "open_access",
                "format": "html",
                "provider": "GitHub",
            },
        ],
        "license": {
            "name": "Public Domain",
            "spdx": "CC0-1.0",
            "url": "https://www.naturalearthdata.com/about/terms-of-use/",
        },
        "coverage": {
            "temporal": "2026 snapshot (boundary data v5.1.2)",
            "spatial": "global",
            "geometry": "1:10m Admin-0 country polygons",
            "border_precision": "surveyed / international law; disputed units flagged",
        },
        "notes": (
            "Natural Earth là bộ dữ liệu bản đồ public domain, tổng hợp từ "
            "nguồn biên giới quốc gia và quốc tế. Lớp 2026 dùng edition 1:10m "
            "Admin-0. Các đơn vị disputed, lease và indeterminate được giữ "
            "nhưng gắn nhãn riêng. Không có PDF chính thức; dữ liệu được phân "
            "phối dưới dạng shapefile/GeoJSON."
        ),
    },
    "src-wikidata": {
        "type": "linked_open_data",
        "tier": "tier_5_general_reference",
        "title": {
            "vi": "Wikidata: Cơ sở tri thức Lịch sử Đa ngôn ngữ",
            "en": "Wikidata: Multilingual Historical Knowledge Base",
        },
        "creators": [{"name": "Wikimedia Foundation & contributors", "role": "compiler"}],
        "publication": {
            "publisher": "Wikimedia Foundation",
            "year": 2026,
            "edition": "live database (snapshot 2026-11-05)",
            "language": "multilingual",
            "notes": "Cơ sở tri thức mở, cập nhật liên tục; dataset dùng bản chụp ngày 2026-11-05.",
        },
        "digital_access": [
            {
                "label": "Wikidata Query Service (SPARQL)",
                "url": "https://query.wikidata.org/",
                "access_type": "open_access",
                "format": "sparql",
                "provider": "Wikimedia Foundation",
            },
            {
                "label": "Wikidata dumps",
                "url": "https://dumps.wikimedia.org/wikidatawiki/",
                "access_type": "open_access",
                "format": "json",
                "provider": "Wikimedia Foundation",
            },
        ],
        "license": {
            "name": "Creative Commons CC0 1.0",
            "spdx": "CC0-1.0",
            "url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        },
        "coverage": {
            "temporal": "all periods",
            "spatial": "global",
            "geometry": "none (labels, descriptions and identifiers only)",
            "border_precision": "not applicable",
        },
        "notes": (
            "Dùng cho nhãn đa ngôn ngữ, mô tả và Q-identifier. Wikidata là "
            "nguồn tham chiếu mở, không phải thẩm quyền sử liệu sơ cấp; các "
            "niên đại suy ra từ đây được đánh dấu reference-grade. CC0 cho "
            "phần dữ liệu Wikidata; không có PDF."
        ),
    },
}

# vietnamese primary / academic sources keep their existing rich metadata;
# the normaliser only adds provenance and licence blocks where known.
SOURCE_TIER_BY_ID = {
    sid: meta["tier"] for sid, meta in SOURCE_CATALOG.items()
}
TIER_RANK = {
    "tier_1_official_primary": 1,
    "tier_2_contemporary_eyewitness": 2,
    "tier_3_peer_reviewed_academic": 3,
    "tier_3_authoritative_cartography": 3,
    "tier_4_scholarly_atlas": 4,
    "tier_5_general_reference": 5,
}

# ---------------------------------------------------------------------------
# text / identifier helpers
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def transliterate(text: str) -> str:
    """Best-effort ASCII transliteration."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def slugify(text: str, fallback: str = "entity") -> str:
    """Stable ASCII slug used for new entity identifiers."""
    value = transliterate(text).lower()
    value = _NON_ALNUM_RE.sub("-", value).strip("-")
    if not value:
        value = hashlib.sha1((text or fallback).encode("utf-8")).hexdigest()[:10]
    return value


def normalize_lang_key(key: str) -> str:
    """Normalise legacy language keys to BCP-47 style keys used in v1.3."""
    k = (key or "").strip()
    low = k.lower().replace("_", "-")
    mapping = {
        "zh": "zh-CN",
        "zh-cn": "zh-CN",
        "zh-hans": "zh-CN",
        "zh-tw": "zh-TW",
        "zh-hant": "zh-TW",
        "zh-hk": "zh-TW",
        "ja-jp": "ja",
        "vi-vn": "vi",
        "en-us": "en",
    }
    return mapping.get(low, low or k)


def normalize_language_map(mapping: Any) -> Dict[str, Any]:
    """Return a copy of *mapping* with normalised language keys.

    If both ``zh`` and ``zh-CN`` exist, the explicit ``zh-CN`` value wins.
    """
    if not isinstance(mapping, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in mapping.items():
        norm = normalize_lang_key(key)
        if norm not in out or key.lower() in ("zh-cn", "zh-tw"):
            out[norm] = value
    return out


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = _WHITESPACE_RE.sub(" ", str(value)).strip()
    return text or None


# ---------------------------------------------------------------------------
# json helpers
# ---------------------------------------------------------------------------

def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if compact:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def iter_positions(geometry: Any) -> Iterator[Tuple[float, float]]:
    if not isinstance(geometry, dict):
        return
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point":
        if _is_position(coords):
            yield coords[0], coords[1]
    elif gtype in ("MultiPoint", "LineString"):
        for pos in coords or []:
            if _is_position(pos):
                yield pos[0], pos[1]
    elif gtype in ("MultiLineString", "Polygon"):
        for ring in coords or []:
            for pos in ring or []:
                if _is_position(pos):
                    yield pos[0], pos[1]
    elif gtype == "MultiPolygon":
        for polygon in coords or []:
            for ring in polygon or []:
                for pos in ring or []:
                    if _is_position(pos):
                        yield pos[0], pos[1]


def _is_position(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    )


def _clean_ring(ring: Sequence[Sequence[float]]) -> Optional[List[List[float]]]:
    cleaned: List[List[float]] = []
    for pos in ring:
        if not _is_position(pos):
            continue
        lon = float(pos[0])
        lat = float(pos[1])
        if not (math.isfinite(lon) and math.isfinite(lat)):
            continue
        if not (-180.0001 <= lon <= 180.0001 and -90.0001 <= lat <= 90.0001):
            continue
        if cleaned and abs(cleaned[-1][0] - lon) < 1e-12 and abs(cleaned[-1][1] - lat) < 1e-12:
            continue
        cleaned.append([round(lon, 6), round(lat, 6)])
    if len(cleaned) < 3:
        return None
    if cleaned[0] != cleaned[-1]:
        cleaned.append(list(cleaned[0]))
    if len(cleaned) < 4:
        return None
    return cleaned


def clean_geometry(geometry: Any) -> Optional[Dict[str, Any]]:
    """Validate coordinate ranges and ring closure; return a clean geometry."""
    if not isinstance(geometry, dict):
        return None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")

    if gtype == "Polygon":
        rings = [r for r in (_clean_ring(ring) for ring in coords or []) if r]
        if not rings:
            return None
        # drop holes that no longer fit; outer ring is the first one
        return {"type": "Polygon", "coordinates": rings}

    if gtype == "MultiPolygon":
        polygons: List[List[List[List[float]]]] = []
        for polygon in coords or []:
            rings = [r for r in (_clean_ring(ring) for ring in polygon or []) if r]
            if rings:
                polygons.append(rings)
        if not polygons:
            return None
        return {"type": "MultiPolygon", "coordinates": polygons}

    return None


def polygon_rings(geometry: Dict[str, Any]) -> List[List[List[float]]]:
    """Return all polygon ring lists from a Polygon/MultiPolygon geometry."""
    if geometry.get("type") == "Polygon":
        return [geometry.get("coordinates") or []]
    if geometry.get("type") == "MultiPolygon":
        return [polygon for polygon in geometry.get("coordinates") or []]
    return []


def merge_geometries(geometries: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge Polygon/MultiPolygon geometries into a single MultiPolygon."""
    polygons: List[List[List[List[float]]]] = []
    for geometry in geometries:
        if not geometry:
            continue
        polygons.extend(polygon_rings(geometry))
    if not polygons:
        return None
    return {"type": "MultiPolygon", "coordinates": polygons}


def bbox_of(geometry: Dict[str, Any]) -> Optional[List[float]]:
    xs: List[float] = []
    ys: List[float] = []
    for lon, lat in iter_positions(geometry):
        xs.append(lon)
        ys.append(lat)
    if not xs:
        return None
    return [round(min(xs), 6), round(min(ys), 6), round(max(xs), 6), round(max(ys), 6)]


# ---------------------------------------------------------------------------
# temporal and confidence helpers
# ---------------------------------------------------------------------------

def format_year(year: Optional[int], lang: str = "vi") -> str:
    if year is None:
        return "—"
    if year < 0:
        return f"{abs(year)} BCE" if lang == "en" else f"{abs(year)} TCN"
    if year == 0:
        return "1 BCE" if lang == "en" else "1 TCN"
    return f"{year} CE" if lang == "en" else f"{year} SCN"


def border_precision_to_confidence(value: Any) -> Tuple[str, str]:
    """Map upstream BORDERPRECISION to (boundary_precision, confidence)."""
    try:
        precision = int(value)
    except (TypeError, ValueError):
        precision = 0
    if precision == 3:
        return "precise_reconstruction", "high"
    if precision == 2:
        return "moderate_reconstruction", "medium"
    if precision == 1:
        return "approximate_reconstruction", "low"
    return "unknown", "low"


def confidence_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 0)


def min_confidence(values: Iterable[str]) -> str:
    ranks = [confidence_rank(v) for v in values if v]
    if not ranks:
        return "low"
    rank = min(ranks)
    return {1: "low", 2: "medium", 3: "high"}.get(rank, "low")


def max_confidence(values: Iterable[str]) -> str:
    ranks = [confidence_rank(v) for v in values if v]
    if not ranks:
        return "low"
    rank = max(ranks)
    return {1: "low", 2: "medium", 3: "high"}.get(rank, "low")


# ---------------------------------------------------------------------------
# entity helpers
# ---------------------------------------------------------------------------

def entity_type_dir(entity_type: str) -> Path:
    """Return the canonical directory for an entity type."""
    return ENTITY_ROOT / normalize_entity_type(entity_type or "state")


def entity_path(entity_id: str, entity_type: str) -> Path:
    """Return the canonical path for an entity document."""
    return entity_type_dir(entity_type) / f"{entity_id}.json"


def iter_entity_files(include_dynasties: bool = False) -> Iterator[Path]:
    """Yield entity documents from every type directory.

    ``data/entities/dynasties`` uses a different document shape and is excluded
    unless explicitly requested.
    """
    paths = sorted(ENTITY_ROOT.glob("*.json")) + sorted(ENTITY_ROOT.glob("*/*.json"))
    for path in paths:
        if not include_dynasties and path.parent.name in ENTITY_NON_ENTITY_DIRS:
            continue
        yield path


def load_entities(entities_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    paths = sorted(entities_dir.glob("*.json")) if entities_dir else iter_entity_files()
    entities: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        try:
            doc = read_json(path)
        except Exception:
            continue
        ent_id = doc.get("id") or path.stem
        entities[ent_id] = doc
    return entities


def load_exclusions() -> Tuple[Set[str], Set[str]]:
    """Load ids and normalized names that must never be re-created upstream."""
    path = DATA_DIR / "aliases" / "excluded-entities.json"
    if not path.exists():
        return set(), set()
    try:
        doc = read_json(path)
    except Exception:
        return set(), set()
    ids = {value for value in doc.get("ids", []) if isinstance(value, str)}
    slugs: Set[str] = set()
    for value in doc.get("names", []):
        if not isinstance(value, str) or not value.strip():
            continue
        slug = slugify(value)
        if len(slug) >= 3:
            slugs.add(slug)
    return ids, slugs


def is_excluded_name(value: str, excluded_ids: Set[str], excluded_slugs: Set[str]) -> bool:
    """Return True when a name/id belongs to an intentionally removed entity."""
    value = (value or "").strip()
    if not value:
        return False
    if value in excluded_ids:
        return True
    slug = slugify(value)
    if slug in excluded_ids or slug in excluded_slugs:
        return True
    # catch derived names such as "Canaanites" or "Beaker culture"
    return any(len(item) >= 4 and item in slug for item in excluded_slugs)


def entity_names(entity: Dict[str, Any]) -> Dict[str, str]:
    return entity.get("names", {}).get("canonical", {}) or {}


def entity_display_name(entity: Dict[str, Any], lang: str = "vi") -> str:
    names = entity_names(entity)
    return names.get(lang) or names.get("en") or names.get("vi") or entity.get("id", "")


def build_name_index(entities: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Map normalised names/aliases to canonical entity ids.

    Earlier definitions win; canonical ids are inserted first so that exact ids
    are not shadowed by aliases.
    """
    index: Dict[str, str] = {}
    for ent_id in sorted(entities, key=lambda value: (len(value), value)):
        index.setdefault(slugify(ent_id), ent_id)
    for ent_id, entity in sorted(entities.items()):
        names = entity.get("names", {})
        candidates: List[str] = []
        canonical = names.get("canonical", {}) or {}
        candidates.extend(str(v) for v in canonical.values() if v)
        candidates.extend(str(v) for values in (names.get("aliases", {}) or {}).values() for v in (values or []))
        for name in candidates:
            key = slugify(name)
            if key:
                index.setdefault(key, ent_id)
    return index


def load_alias_config(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or (ALIASES_DIR / "entity-aliases.json")
    if path.exists():
        return read_json(path)
    return {"spatial_to_entity": {}, "entity_id_migrations": {}}


def apply_aliases(name_or_slug: str, alias_config: Dict[str, Any]) -> str:
    spatial = alias_config.get("spatial_to_entity", {}) or {}
    if name_or_slug in spatial:
        return spatial[name_or_slug]
    key = slugify(name_or_slug)
    return spatial.get(key, key)


def entity_type_to_layer_type(entity_type: str) -> str:
    if entity_type == "dependent_territory":
        return "dependent_territory"
    if entity_type == "disputed_territory":
        return "disputed_territory"
    return "sovereign_territory"


ENTITY_TYPE_ALIASES = {
    "state": "state",
    "kingdom": "kingdom",
    "kingdoms": "kingdom",
    "empire": "empire",
    "civilization": "civilization",
    "city-state": "city_state",
    "city_state": "city_state",
    "confederation": "confederation",
    "federation": "federation",
    "republic": "republic",
    "protectorate": "protectorate",
    "colony": "colony",
    "khanate": "khanate",
    "chiefdom": "chiefdom",
    "state society": "state",
    "dependent_territory": "dependent_territory",
    "disputed_territory": "disputed_territory",
}


def normalize_entity_type(value: str) -> str:
    key = (value or "state").strip().lower()
    return ENTITY_TYPE_ALIASES.get(key, key.replace(" ", "_"))


def infer_entity_type_from_name(name: str) -> str:
    low = (name or "").lower()
    if any(
        token in low
        for token in (
            "hunter", "gatherer", "forager", "fisher", "nomad",
            "pastoral", "farmer", "farming", "agricultur",
            "culture", "tribe", "tribes", "peoples",
        )
    ):
        return "culture"
    if any(token in low for token in ("empire",)):
        return "empire"
    if any(token in low for token in ("kingdom", "king ")):
        return "kingdom"
    return "state"


# ---------------------------------------------------------------------------
# canonical timeline & historical milestone metadata (dates, months, events)
# ---------------------------------------------------------------------------

HISTORICAL_DATE_METADATA: Dict[int, Dict[str, Any]] = {
    -3500: {
        "valid_from": "-3500-01-01", "valid_to": "-3001-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Khởi nguyên văn minh Sumer (Uruk sơ kỳ) & Ai Cập Tiền Triều đại",
        "event_en": "Rise of early Sumerian civilization (Uruk period) and Predynastic Egypt",
        "era_vi": "Thời kỳ Tiền sử", "era_en": "Prehistory"
    },
    -3000: {
        "valid_from": "-3000-01-01", "valid_to": "-2001-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Vương triều thứ nhất Ai Cập (Narmer thống nhất Thượng - Hạ Ai Cập)",
        "event_en": "First Dynasty of Egypt under Narmer and Early Dynastic Mesopotamia",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -2000: {
        "valid_from": "-2000-01-01", "valid_to": "-1501-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Vương triều Ur thứ ba, Trung Vương quốc Ai Cập & Văn minh Minoan",
        "event_en": "Third Dynasty of Ur, Middle Kingdom of Egypt, and Minoan civilization",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -1500: {
        "valid_from": "-1500-01-01", "valid_to": "-1001-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thời kỳ Tân Vương quốc Ai Cập (Thutmose I) & Đế quốc Hitti Đồ Đồng",
        "event_en": "New Kingdom of Egypt (Thutmose I) and Hittite Empire in the Bronze Age",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -1000: {
        "valid_from": "-1000-01-01", "valid_to": "-0701-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thời đại Đồ Sắt sơ kỳ, Vương quốc Israel thống nhất & Nhà Tây Chu",
        "event_en": "Early Iron Age, United Monarchy of Israel, and Western Zhou Dynasty",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -700: {
        "valid_from": "-0700-01-01", "valid_to": "-0501-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Đế quốc Tân Assyria thời Sennacherib & Thời kỳ Xuân Thu",
        "event_en": "Neo-Assyrian Empire under Sennacherib and Spring and Autumn period",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -500: {
        "valid_from": "-0500-01-01", "valid_to": "-0401-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Đế quốc Achaemenid Ba Tư (Darius Đại đế) & Thành bang Athens Cổ điển",
        "event_en": "Achaemenid Persian Empire under Darius I and Classical Athenian Democracy",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -400: {
        "valid_from": "-0400-01-01", "valid_to": "-0324-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Sau Chiến tranh Peloponnesus & Thời kỳ Chiến Quốc tại Trung Hoa",
        "event_en": "Post-Peloponnesian War era and Warring States period in China",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -323: {
        "valid_from": "-0323-06-10", "valid_to": "-0301-12-31", "precision": "day", "month": 6, "day": 10,
        "event_vi": "10/06/323 TCN: Cái chết của Alexander Đại đế & Phân chia Diadochi",
        "event_en": "June 10, 323 BCE: Death of Alexander the Great and Partition of Babylon",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -300: {
        "valid_from": "-0300-01-01", "valid_to": "-0201-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Các vương quốc Hy Lạp hóa (Seleucid, Ptolemy) & Đế quốc Maurya",
        "event_en": "Hellenistic Kingdoms (Seleucid, Ptolemaic) and Maurya Empire under Chandragupta",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -200: {
        "valid_from": "-0200-01-01", "valid_to": "-0101-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Hán Cao Tổ thành lập nhà Hán & La Mã thắng Chiến tranh Punic 2",
        "event_en": "Founding of Han Dynasty by Liu Bang and Roman victory in Second Punic War",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -100: {
        "valid_from": "-0100-01-01", "valid_to": "-0002-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Cuối thời Cộng hòa La Mã & Hán Vũ Đế mở Con đường Tơ lụa",
        "event_en": "Late Roman Republic and Emperor Wu of Han opening the Silk Road",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    -1: {
        "valid_from": "-0001-01-01", "valid_to": "0099-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "1 TCN: Khởi nguyên Công nguyên & Đế quốc La Mã thời Augustus",
        "event_en": "1 BCE: Dawn of the Common Era and Principate of Augustus",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    100: {
        "valid_from": "0100-01-01", "valid_to": "0199-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Đế quốc La Mã cực thịnh thời Hoàng đế Trajan & Đông Hán",
        "event_en": "Peak territorial extent of Roman Empire under Trajan and Eastern Han",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    200: {
        "valid_from": "0200-01-01", "valid_to": "0299-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Trận Quan Độ, cuối thời Đông Hán & Triều đại Severus tại La Mã",
        "event_en": "Battle of Guandu in China and Severan dynasty in Rome",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    300: {
        "valid_from": "0300-01-01", "valid_to": "0399-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Tứ đầu chế La Mã của Diocletianus & Tây Tấn loạn Bát Vương",
        "event_en": "Diocletian's Tetrarchy and War of the Eight Princes in Jin Dynasty",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    400: {
        "valid_from": "0400-01-01", "valid_to": "0499-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Phân chia Đông - Tây La Mã (395) & Thời kỳ Di cư lớn",
        "event_en": "Division of Roman Empire (395 CE) and Migration Period",
        "era_vi": "Thời kỳ Cổ đại", "era_en": "Ancient History"
    },
    500: {
        "valid_from": "0500-01-01", "valid_to": "0599-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Hậu Tây La Mã, Vương quốc Clovis I của người Frank & Nam Bắc Triều",
        "event_en": "Post-Western Roman kingdoms (Clovis I) and Northern & Southern Dynasties",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    600: {
        "valid_from": "0600-01-01", "valid_to": "0699-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Nhà Tùy thống nhất Trung Hoa & Đế quốc Đông La Mã Byzantine",
        "event_en": "Sui Dynasty reunification of China and Byzantine-Sasanian rivalry",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    700: {
        "valid_from": "0700-01-01", "valid_to": "0799-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Đế quốc Umayyad bành trướng & Nhà Đường thời Võ Tắc Thiên",
        "event_en": "Expansion of the Umayyad Caliphate and Tang Dynasty under Wu Zetian",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    800: {
        "valid_from": "0800-12-25", "valid_to": "0899-12-31", "precision": "day", "month": 12, "day": 25,
        "event_vi": "25/12/800: Charlemagne đăng quang Hoàng đế phương Tây & Nhà Abbasid",
        "event_en": "Dec 25, 800: Coronation of Charlemagne and Golden Age of Abbasid Caliphate",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    900: {
        "valid_from": "0900-01-01", "valid_to": "0999-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thời kỳ Ngũ Đại Thập Quốc & Phân rã Đế quốc Frank",
        "event_en": "Five Dynasties and Ten Kingdoms period and fragmentation of Carolingian Empire",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1000: {
        "valid_from": "1000-01-01", "valid_to": "1099-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Chuyển giao Thiên niên kỷ 1000: Nhà Tống, Otto III & Đại Cồ Việt",
        "event_en": "Millennium year 1000: Song Dynasty, Holy Roman Empire of Otto III, and Dai Co Viet",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1100: {
        "valid_from": "1100-01-01", "valid_to": "1199-12-31", "precision": "month", "month": 1, "day": 1,
        "event_vi": "Sau Cuộc Thập tự chinh thứ nhất & Thành lập các Công quốc Thập tự",
        "event_en": "Aftermath of First Crusade and establishment of Crusader States",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1200: {
        "valid_from": "1200-01-01", "valid_to": "1278-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thế giới trước cuộc bành trướng Mông Cổ & Đệ tứ Thập tự chinh",
        "event_en": "World on the eve of Mongol conquests and Fourth Crusade",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1279: {
        "valid_from": "1279-03-19", "valid_to": "1299-12-31", "precision": "day", "month": 3, "day": 19,
        "event_vi": "19/03/1279: Trận Nhai Môn, Nam Tống diệt vong, Nhà Nguyên thống nhất",
        "event_en": "March 19, 1279: Battle of Yamen and Yuan Dynasty conquest of Song China",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1300: {
        "valid_from": "1300-01-01", "valid_to": "1399-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thành lập Đế quốc Ottoman (Osman I) & 4 Hãn quốc Mông Cổ",
        "event_en": "Foundation of Ottoman Empire under Osman I and Mongol successor khanates",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1400: {
        "valid_from": "1400-01-01", "valid_to": "1491-12-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Đế chế Timurid của Timur Đại đế & Nhà Minh thời Vĩnh Lạc",
        "event_en": "Timurid Empire under Timur and Ming Dynasty under the Yongle Emperor",
        "era_vi": "Thời kỳ Trung đại", "era_en": "Middle Ages"
    },
    1492: {
        "valid_from": "1492-10-12", "valid_to": "1499-12-31", "precision": "day", "month": 10, "day": 12,
        "event_vi": "12/10/1492: Columbus tới châu Mỹ; Hoàn thành Reconquista tại Granada",
        "event_en": "Oct 12, 1492: Columbus lands in Americas and completion of Reconquista in Granada",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1500: {
        "valid_from": "1500-04-22", "valid_to": "1529-12-31", "precision": "day", "month": 4, "day": 22,
        "event_vi": "22/04/1500: Cabral tới Brazil & Thời đại Khám phá Địa lý",
        "event_en": "April 22, 1500: Pedro Alvares Cabral discovers Brazil in Age of Discovery",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1530: {
        "valid_from": "1530-02-24", "valid_to": "1599-12-31", "precision": "day", "month": 2, "day": 24,
        "event_vi": "24/02/1530: Đăng quang Karl V tại Bologna & Bá quyền Habsburg",
        "event_en": "Feb 24, 1530: Coronation of Charles V in Bologna and Habsburg dominance",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1600: {
        "valid_from": "1600-10-21", "valid_to": "1648-10-23", "precision": "day", "month": 10, "day": 21,
        "event_vi": "21/10/1600: Trận Sekigahara, Mạc phủ Tokugawa & Thành lập EIC Anh",
        "event_en": "Oct 21, 1600: Battle of Sekigahara in Japan and founding of British East India Company",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1650: {
        "valid_from": "1648-10-24", "valid_to": "1699-12-31", "precision": "day", "month": 10, "day": 24,
        "event_vi": "24/10/1648: Hòa ước Westphalia & Xác lập Trật tự Chủ quyền Quốc gia",
        "event_en": "Oct 24, 1648: Peace of Westphalia establishing the modern sovereign state system",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1700: {
        "valid_from": "1700-01-01", "valid_to": "1715-08-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Chiến tranh Kế vị Tây Ban Nha & Đại chiến Bắc Âu",
        "event_en": "War of the Spanish Succession and Great Northern War",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1715: {
        "valid_from": "1715-09-01", "valid_to": "1783-09-02", "precision": "day", "month": 9, "day": 1,
        "event_vi": "01/09/1715: Louis XIV qua đời & Trật tự Hòa ước Utrecht",
        "event_en": "Sept 1, 1715: Death of Louis XIV and European order under the Treaty of Utrecht",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1783: {
        "valid_from": "1783-09-03", "valid_to": "1799-12-31", "precision": "day", "month": 9, "day": 3,
        "event_vi": "03/09/1783: Hiệp ước Paris công nhận nền Độc lập của Hoa Kỳ",
        "event_en": "Sept 3, 1783: Treaty of Paris recognizing American Independence",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1800: {
        "valid_from": "1800-01-01", "valid_to": "1815-06-08", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Kỷ nguyên Napoleon sau Cuộc đảo chính 18 Sương mù & Đại Việt",
        "event_en": "Napoleonic Wars era after 18 Brumaire and Vietnam's unification under Nguyen Dynasty",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1815: {
        "valid_from": "1815-06-09", "valid_to": "1878-07-12", "precision": "day", "month": 6, "day": 9,
        "event_vi": "09/06/1815: Định ước Hội nghị Vienna & Kết thúc Chiến tranh Napoleon",
        "event_en": "June 9, 1815: Final Act of Congress of Vienna and Post-Napoleonic European balance",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1878: {
        "valid_from": "1878-07-13", "valid_to": "1879-12-31", "precision": "day", "month": 7, "day": 13,
        "event_vi": "13/07/1878: Hòa ước Berlin tái phân chia vùng Balkan & Đông Âu",
        "event_en": "July 13, 1878: Treaty of Berlin settling the Eastern Crisis",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1880: {
        "valid_from": "1880-07-03", "valid_to": "1899-12-31", "precision": "day", "month": 7, "day": 3,
        "event_vi": "03/07/1880: Hội nghị Madrid & Khởi đầu Tranh giành châu Phi",
        "event_en": "July 3, 1880: Conference of Madrid and Scramble for Africa",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1900: {
        "valid_from": "1900-01-01", "valid_to": "1914-07-31", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Khởi đầu Thế kỷ 20, Khủng hoảng Nghĩa Hòa Đoàn & Chiến tranh Boer",
        "event_en": "Dawn of the 20th Century, Boxer Rebellion, and Second Boer War",
        "era_vi": "Thời kỳ Cận đại", "era_en": "Early Modern Period"
    },
    1914: {
        "valid_from": "1914-08-01", "valid_to": "1919-12-31", "precision": "day", "month": 8, "day": 1,
        "event_vi": "01/08/1914: Bùng nổ Chiến tranh thế giới thứ nhất",
        "event_en": "Aug 1, 1914: Outbreak of World War I",
        "era_vi": "Chiến tranh Thế giới thứ nhất", "era_en": "World War I"
    },
    1920: {
        "valid_from": "1920-01-10", "valid_to": "1929-12-31", "precision": "day", "month": 1, "day": 10,
        "event_vi": "10/01/1920: Hòa ước Versailles có hiệu lực & Thành lập Hội Quốc Liên",
        "event_en": "Jan 10, 1920: Treaty of Versailles enters into force and founding of League of Nations",
        "era_vi": "Giai đoạn Giữa hai cuộc thế chiến", "era_en": "Interwar Period"
    },
    1930: {
        "valid_from": "1930-01-01", "valid_to": "1938-09-29", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thời kỳ Đại suy thoái kinh tế toàn cầu & Khủng hoảng Mãn Châu",
        "event_en": "Great Depression era and geopolitical realignment",
        "era_vi": "Giai đoạn Giữa hai cuộc thế chiến", "era_en": "Interwar Period"
    },
    1938: {
        "valid_from": "1938-09-30", "valid_to": "1945-09-01", "precision": "day", "month": 9, "day": 30,
        "event_vi": "30/09/1938: Hiệp ước Munich & Ngưỡng cửa Thế chiến II",
        "event_en": "Sept 30, 1938: Munich Agreement on the eve of World War II",
        "era_vi": "Giai đoạn Giữa hai cuộc thế chiến", "era_en": "Interwar Period"
    },
    1945: {
        "valid_from": "1945-09-02", "valid_to": "1959-12-31", "precision": "day", "month": 9, "day": 2,
        "event_vi": "02/09/1945: Kết thúc Thế chiến II & Tuyên ngôn Độc lập Việt Nam",
        "event_en": "Sept 2, 1945: End of World War II and Proclamation of Independence of Vietnam",
        "era_vi": "Chiến tranh Thế giới thứ hai", "era_en": "World War II"
    },
    1960: {
        "valid_from": "1960-01-01", "valid_to": "1994-04-26", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Năm châu Phi (17 nước độc lập) & Cao trào Chiến tranh Lạnh",
        "event_en": "Year of Africa (17 newly independent states) and Cold War era",
        "era_vi": "Thời kỳ Chiến tranh Lạnh", "era_en": "Cold War Era"
    },
    1994: {
        "valid_from": "1994-04-27", "valid_to": "1999-12-31", "precision": "day", "month": 4, "day": 27,
        "event_vi": "27/04/1994: Bầu cử dân chủ Nam Phi chấm dứt Apartheid & Hậu Xô Viết",
        "event_en": "April 27, 1994: Post-Apartheid South Africa election and post-Cold War order",
        "era_vi": "Thời kỳ Hậu Chiến tranh Lạnh", "era_en": "Post-Cold War Era"
    },
    2000: {
        "valid_from": "2000-01-01", "valid_to": "2009-12-31", "precision": "day", "month": 1, "day": 1,
        "event_vi": "01/01/2000: Chuyển giao Thiên niên kỷ mới 2000",
        "event_en": "Jan 1, 2000: Turn of the Millennium",
        "era_vi": "Thời kỳ Hiện đại", "era_en": "Contemporary Period"
    },
    2010: {
        "valid_from": "2010-01-01", "valid_to": "2026-11-02", "precision": "year", "month": 1, "day": 1,
        "event_vi": "Thập niên 2010: Ranh giới quốc tế trước hiện đại",
        "event_en": "2010s international boundaries before current updates",
        "era_vi": "Thời kỳ Hiện đại", "era_en": "Contemporary Period"
    },
    2026: {
        "valid_from": "2026-11-03", "valid_to": "2026-12-31", "precision": "day", "month": 11, "day": 3,
        "event_vi": "03/11/2026: Ranh giới Hiện đại Toàn cầu Chuẩn Natural Earth 50m",
        "event_en": "Nov 3, 2026: Contemporary Global Boundaries (Natural Earth 50m survey)",
        "era_vi": "Thời kỳ Hiện đại", "era_en": "Contemporary Period"
    }
}

