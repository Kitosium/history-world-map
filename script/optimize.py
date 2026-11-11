#!/usr/bin/env python3
"""Build lightweight web copies of the yearly GeoJSON layers.

The validation dataset keeps the full-resolution geometry.  The browser only
needs enough detail for a world/continental view, so this stage:

* simplifies every ring with Douglas–Peucker;
* drops islands smaller than the visible threshold;
* rounds coordinates to three decimals; and
* keeps only the properties used by the map UI.

Output: ``data/dist/spatial/web/<year>.geojson``.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import DIST_SPATIAL_DIR, DIST_DIR, DATA_DIR, HISTORICAL_DATE_METADATA  # noqa: E402

WEB_DIR = DIST_DIR / "spatial" / "web"
TOLERANCE = 0.02  # degrees, roughly 2 km at the equator
MIN_RING_AREA = 0.0004  # square degrees
PRESERVE_ISLANDS_ENTITIES = {
    "vietnam",
    "south-vietnam",
    "dai-nam",
    "đại-việt",
    "dang-ngoai",
    "dang-trong",
    "mac-dynasty",
    "nguyen-gia-dinh",
    "ha-tien",
    "tinh-hai-quan",
    "dai-co-viet",
    "dai-ngu",
    "van-lang",
    "au-lac",
    "van-xuan",
    "nam-viet",
    "french-indochina",
    "cochin-china",
    "champa",
    "champa-city-states",
    "hoan-vuong",
    "funan",
    "chen-la",
    "lam-ap",
    "singapore",
    "brunei",
    "hong-kong",
    "macau",
}

HIGH_PRECISION_ASIA_ENTITIES = {
    "china",
    "taiwan",
    "laos",
    "cambodia",
    "thailand",
    "siam",
    "rattanakosin-kingdom",
    "ayutthaya",
    "sukhothai",
    "kingdom-of-sukhotai",
    "lan-na",
    "laotian-states",
    "khmer-empire",
    "mon-state",
    "mon-khmer",
    "thai",
    "thai-kingdoms",
    "myanmar",
    "burma",
    "burmese-kingdoms",
    "pagan",
    "pegu",
    "toungoo",
    "konbaung",
    "shan-states",
    "malaysia",
    "malaya",
    "malacca",
    "indonesia",
    "philippines",
    "timor-leste",
    "srivijaya-empire",
    "majapahit",
    "mataram",
    "aceh",
    "banten",
    "johor",
    "sulu",
    "maguindanao",
    "japan",
    "imperial-japan",
    "japan-usa",
    "japan-warring-states",
    "shogun-japan-kamakura",
    "north-korea",
    "south-korea",
    "korea",
    "korea-usa",
    "korea-ussr",
    "koryo",
    "silla",
    "koguryo",
    "paekche",
    "mongolia",
    "qin",
    "han",
    "jin",
    "jin-empire",
    "sui-empire",
    "tang-empire",
    "song-empire",
    "great-khanate",
    "ming-empire",
    "ming-chinese-empire",
    "qing-empire",
    "manchu-empire",
    "post-ming-warlords",
    "chinese-warlords",
    "nan-chao",
    "hainan",
    "bhutan",
    "bangladesh",
    "nepal",
}
KEEP = (
    "entity_id",
    "name_en",
    "name_vi",
    "type",
    "layer_type",
    "border_precision",
    "confidence",
    "source_ids",
    "wikidata_id",
    "valid_year",
    "valid_month",
    "valid_day",
    "valid_from",
    "valid_to",
    "precision",
    "color_index",
)


def ring_area(points: Sequence[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def point_line_distance(point: Tuple[float, float], start: Tuple[float, float], end: Tuple[float, float]) -> float:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def douglas_peucker(points: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
    if len(points) <= 2:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        furthest = -1.0
        index = -1
        for i in range(start + 1, end):
            distance = point_line_distance(points[i], points[start], points[end])
            if distance > furthest:
                furthest = distance
                index = i
        if index != -1 and furthest > tolerance:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [point for point, flag in zip(points, keep) if flag]


def simplify_ring(
    raw: Iterable[Sequence[float]],
    tolerance: float,
    min_area: float = MIN_RING_AREA,
    decimals: int = 3,
) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for item in raw:
        if len(item) < 2:
            continue
        point = (round(float(item[0]), decimals), round(float(item[1]), decimals))
        if not points or point != points[-1]:
            points.append(point)

    if len(points) < 4:
        return []
    closed = points[0] == points[-1]
    if closed:
        points = points[:-1]
    if len(points) < 3:
        return []

    # split the closed ring at its most distant point so that the usual
    # open-polyline Douglas–Peucker pass never receives a degenerate segment.
    first = points[0]
    split = max(range(1, len(points)), key=lambda i: math.hypot(points[i][0] - first[0], points[i][1] - first[1]))
    left = douglas_peucker(points[: split + 1], tolerance)
    right = douglas_peucker(points[split:] + [first], tolerance)
    result = left[:-1] + right[:-1]
    if len(result) < 3:
        return []
    result.append(result[0])
    if ring_area(result) < min_area:
        return []
    return result


def simplify_polygon(
    rings: List[List[Tuple[float, float]]],
    preserve_small: bool = False,
    high_precision: bool = False,
) -> List[List[Tuple[float, float]]]:
    if not rings:
        return []
    if preserve_small:
        tol = 0.0015
        min_area = 0.0
        decimals = 4
    elif high_precision:
        tol = 0.002
        min_area = 0.00003
        decimals = 4
    else:
        tol = TOLERANCE
        min_area = MIN_RING_AREA
        decimals = 3
    exterior = simplify_ring(rings[0], tol, min_area=min_area, decimals=decimals)
    if not exterior:
        return []
    holes = []
    for ring in rings[1:]:
        simplified = simplify_ring(ring, tol, min_area=min_area, decimals=decimals)
        if simplified:
            holes.append(simplified)
    return [exterior, *holes]


def simplify_geometry(
    geometry: dict[str, Any],
    preserve_small: bool = False,
    high_precision: bool = False,
) -> dict[str, Any] | None:
    kind = geometry.get("type")
    if kind == "Polygon":
        polygons = [
            simplify_polygon(
                geometry.get("coordinates", []),
                preserve_small=preserve_small,
                high_precision=high_precision,
            )
        ]
    elif kind == "MultiPolygon":
        polygons = [
            simplify_polygon(
                polygon,
                preserve_small=preserve_small,
                high_precision=high_precision,
            )
            for polygon in geometry.get("coordinates", [])
        ]
    else:
        return None
    polygons = [polygon for polygon in polygons if polygon]
    if not polygons:
        return None
    if kind == "Polygon" and len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def extract_feature_points_and_bbox(geometry: dict[str, Any]) -> tuple[tuple[float, float, float, float], set[tuple[float, float]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    points = set()

    def walk(ring: list[list[float]]) -> None:
        nonlocal min_x, min_y, max_x, max_y
        for pt in ring:
            if len(pt) < 2:
                continue
            x, y = pt[0], pt[1]
            if x < min_x: min_x = x
            if x > max_x: max_x = x
            if y < min_y: min_y = y
            if y > max_y: max_y = y
            points.add((round(x, 2), round(y, 2)))

    if kind == "Polygon":
        for ring in coords:
            walk(ring)
    elif kind == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                walk(ring)
    return (min_x, min_y, max_x, max_y), points


def assign_four_colors(features: list[dict[str, Any]]) -> dict[str, int]:
    import random
    data = []
    for f in features:
        fid = f.get("id") or f.get("properties", {}).get("entity_id")
        bbox, pts = extract_feature_points_and_bbox(f.get("geometry") or {})
        data.append((fid, bbox, pts))

    n = len(data)
    adj = {d[0]: set() for d in data}
    adj_weights: dict[str, dict[str, int]] = {d[0]: {} for d in data}
    margin = 0.05
    for i in range(n):
        id1, b1, pts1 = data[i]
        for j in range(i + 1, n):
            id2, b2, pts2 = data[j]
            if (
                b1[2] + margin < b2[0]
                or b2[2] + margin < b1[0]
                or b1[3] + margin < b2[1]
                or b2[3] + margin < b1[1]
            ):
                continue
            shared = len(pts1.intersection(pts2))
            if shared >= 2:
                adj[id1].add(id2)
                adj[id2].add(id1)
                adj_weights[id1][id2] = shared
                adj_weights[id2][id1] = shared

    nodes = [d[0] for d in data]
    degrees = {u: len(adj[u]) for u in nodes}

    best_colors: dict[str, int] = {}
    min_conflict_weight = float("inf")

    for attempt in range(40):
        random.seed(attempt)
        colors: dict[str, int] = {}
        neighbor_colors = {u: set() for u in nodes}
        uncolored = list(nodes)

        while uncolored:
            max_sat = max(len(neighbor_colors[u]) for u in uncolored)
            candidates = [u for u in uncolored if len(neighbor_colors[u]) == max_sat]
            max_deg = max(degrees[u] for u in candidates)
            best_nodes = [u for u in candidates if degrees[u] == max_deg]
            node = random.choice(best_nodes)
            uncolored.remove(node)

            avail = [c for c in range(4) if c not in neighbor_colors[node]]
            if avail:
                c = random.choice(avail)
            else:
                weights = [
                    sum(adj_weights[node].get(nbr, 1) for nbr in adj[node] if colors.get(nbr) == col)
                    for col in range(4)
                ]
                c = min(range(4), key=lambda col: weights[col])

            colors[node] = c
            for nbr in adj[node]:
                neighbor_colors[nbr].add(c)

        total_conflict_weight = sum(
            adj_weights[u].get(v, 1)
            for u in nodes
            for v in adj[u]
            if u < v and colors[u] == colors[v]
        )
        if total_conflict_weight == 0:
            return colors
        if total_conflict_weight < min_conflict_weight:
            min_conflict_weight = total_conflict_weight
            best_colors = colors

    return best_colors


def optimize_file(source: Path, target: Path) -> tuple[int, int]:
    data = json.loads(source.read_text(encoding="utf-8"))
    features = []
    before = 0
    after = 0
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        eid = properties.get("entity_id", "")
        before += count_points(geometry)
        simplified = simplify_geometry(
            geometry,
            preserve_small=(eid in PRESERVE_ISLANDS_ENTITIES),
            high_precision=(eid in HIGH_PRECISION_ASIA_ENTITIES),
        )
        if not simplified:
            continue
        after += count_points(simplified)
        feat_props = {key: properties[key] for key in KEEP if key in properties}
        v_year = properties.get("valid_year")
        if v_year in HISTORICAL_DATE_METADATA:
            meta = HISTORICAL_DATE_METADATA[v_year]
            if "valid_from" in meta and meta["valid_from"]:
                feat_props["valid_from"] = meta["valid_from"]
            if "valid_to" in meta and meta["valid_to"]:
                feat_props["valid_to"] = meta["valid_to"]
            if "precision" in meta and meta["precision"]:
                feat_props["precision"] = meta["precision"]
            if "month" in meta and meta["month"]:
                feat_props["valid_month"] = meta["month"]
            if "day" in meta and meta["day"]:
                feat_props["valid_day"] = meta["day"]
        features.append(
            {
                "type": "Feature",
                "id": feature.get("id") or f"feat-{properties.get('valid_year')}-{properties.get('entity_id')}",
                "properties": feat_props,
                "geometry": simplified,
            }
        )

    # compute 4-color map coloring for web layer
    color_map = assign_four_colors(features)
    for feat in features:
        feat_id = feat.get("id") or feat["properties"].get("entity_id")
        feat["properties"]["color_index"] = color_map.get(feat_id, 0)

    target.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return before, after


def count_points(geometry: dict[str, Any]) -> int:
    kind = geometry.get("type")
    if kind == "Polygon":
        return sum(len(ring) for ring in geometry.get("coordinates", []))
    if kind == "MultiPolygon":
        return sum(len(ring) for polygon in geometry.get("coordinates", []) for ring in polygon)
    return 0


def main() -> int:
    import shutil

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    geojson_dir = DATA_DIR / "geojson"
    geojson_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(DIST_SPATIAL_DIR.glob("*.geojson"), key=lambda path: path.name)
    total_before = total_after = 0
    for source in sources:
        target = WEB_DIR / source.name
        before, after = optimize_file(source, target)
        total_before += before
        total_after += after

        # copy optimized file directly to data/geojson/
        shutil.copyfile(target, geojson_dir / source.name)
        print(f"  {source.name:>12}  {before:>7,} → {after:>7,} points")

    # copy land background directly to data/geojson/
    land_src = Path(__file__).resolve().parent.parent / "web" / "public" / "geo" / "land.geojson"
    if land_src.exists():
        shutil.copyfile(land_src, geojson_dir / "land.geojson")

    size = sum(path.stat().st_size for path in WEB_DIR.glob("*.geojson"))
    print(
        f"✓ {len(sources)} web layers · {total_before:,} → {total_after:,} points "
        f"({size / 1024 / 1024:.1f} MB)"
    )

    # synchronize data into web/public/data for direct static delivery
    public_data = Path(__file__).resolve().parent.parent / "web" / "public" / "data"
    public_dist = public_data / "dist"
    public_geojson = public_data / "geojson"
    public_dist.mkdir(parents=True, exist_ok=True)
    public_geojson.mkdir(parents=True, exist_ok=True)

    shutil.copytree(DIST_DIR, public_dist, dirs_exist_ok=True)
    shutil.copytree(geojson_dir, public_geojson, dirs_exist_ok=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
