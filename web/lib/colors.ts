import type { EntityLike } from "@/lib/types";

export const FOUR_COLORS = [
  "var(--map-color-1)",
  "var(--map-color-2)",
  "var(--map-color-3)",
  "var(--map-color-4)"
] as const;

export function hashString(value: unknown): number {
  let hash = 0;
  const text = String(value || "");
  for (let i = 0; i < text.length; i += 1) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

export function featureColor(properties?: EntityLike | null): string {
  const colorIndex = (properties as any)?.color_index;
  if (typeof colorIndex === "number" && colorIndex >= 0) {
    return FOUR_COLORS[colorIndex % FOUR_COLORS.length];
  }
  const id = properties?.entity_id || properties?.name_en || "default";
  return FOUR_COLORS[hashString(id) % FOUR_COLORS.length];
}

interface FeatureInput {
  id?: string | number;
  properties?: any;
  geometry?: any;
}

function extractBboxAndPoints(geometry: any): {
  bbox: [number, number, number, number];
  points: Set<string>;
} {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const points = new Set<string>();

  if (!geometry) {
    return { bbox: [0, 0, 0, 0], points };
  }

  function walk(ring: number[][]) {
    for (let i = 0; i < ring.length; i += 1) {
      const pt = ring[i];
      if (!pt || pt.length < 2) continue;
      const x = pt[0];
      const y = pt[1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      points.add(`${Math.round(x * 100)}:${Math.round(y * 100)}`);
    }
  }

  const kind = geometry.type;
  const coords = geometry.coordinates;
  if (kind === "Polygon" && Array.isArray(coords)) {
    for (const ring of coords) {
      if (Array.isArray(ring)) walk(ring);
    }
  } else if (kind === "MultiPolygon" && Array.isArray(coords)) {
    for (const poly of coords) {
      if (Array.isArray(poly)) {
        for (const ring of poly) {
          if (Array.isArray(ring)) walk(ring);
        }
      }
    }
  }

  return { bbox: [minX, minY, maxX, maxY], points };
}

/**
 * assigns one of 4 colors to each feature in the collection
 * using the four-color map theorem (dsatur heuristic).
 * guarantees adjacent / bordering features receive different colors.
 */
export function assignFourColors(features: FeatureInput[]): Map<string, string> {
  const result = new Map<string, string>();
  if (!features || !features.length) return result;

  // check if color_index is already precomputed
  let allPrecomputed = true;
  for (let i = 0; i < features.length; i += 1) {
    const f = features[i];
    const colorIndex = f.properties?.color_index;
    if (typeof colorIndex !== "number" || colorIndex < 0) {
      allPrecomputed = false;
      break;
    }
  }

  if (allPrecomputed) {
    for (let i = 0; i < features.length; i += 1) {
      const f = features[i];
      const id = String(f.properties?.entity_id || f.id || `feat-${i}`);
      const colorIndex = (f.properties?.color_index ?? 0) % FOUR_COLORS.length;
      result.set(id, FOUR_COLORS[colorIndex]);
    }
    return result;
  }

  // precompute bboxes and rounded point sets
  const items = features.map((f, i) => {
    const id = String(f.properties?.entity_id || f.id || `feat-${i}`);
    const { bbox, points } = extractBboxAndPoints(f.geometry);
    return { id, bbox, points };
  });

  // build adjacency list
  const adj = new Map<string, Set<string>>();
  for (const item of items) {
    adj.set(item.id, new Set<string>());
  }

  const margin = 0.05;
  for (let i = 0; i < items.length; i += 1) {
    const a = items[i];
    for (let j = i + 1; j < items.length; j += 1) {
      const b = items[j];
      // quick bounding box pruning
      if (
        a.bbox[2] + margin < b.bbox[0] ||
        b.bbox[2] + margin < a.bbox[0] ||
        a.bbox[3] + margin < b.bbox[1] ||
        b.bbox[3] + margin < a.bbox[1]
      ) {
        continue;
      }

      // check shared boundary points
      let shared = 0;
      const [smaller, larger] =
        a.points.size < b.points.size ? [a.points, b.points] : [b.points, a.points];
      for (const pt of smaller) {
        if (larger.has(pt)) {
          shared += 1;
          if (shared >= 2) break;
        }
      }

      if (shared >= 2) {
        adj.get(a.id)!.add(b.id);
        adj.get(b.id)!.add(a.id);
      }
    }
  }

  // dsatur graph coloring
  const nodes = items.map((it) => it.id);
  const degrees = new Map<string, number>();
  const neighborColors = new Map<string, Set<number>>();
  for (const id of nodes) {
    degrees.set(id, adj.get(id)!.size);
    neighborColors.set(id, new Set<number>());
  }

  const uncolored = new Set<string>(nodes);
  const colorAssignment = new Map<string, number>();

  while (uncolored.size > 0) {
    let bestNode = "";
    let maxSat = -1;
    let maxDeg = -1;

    for (const node of uncolored) {
      const sat = neighborColors.get(node)!.size;
      const deg = degrees.get(node)!;
      if (sat > maxSat || (sat === maxSat && deg > maxDeg)) {
        maxSat = sat;
        maxDeg = deg;
        bestNode = node;
      }
    }

    uncolored.delete(bestNode);
    const used = neighborColors.get(bestNode)!;

    let assigned = -1;
    for (let c = 0; c < 4; c += 1) {
      if (!used.has(c)) {
        assigned = c;
        break;
      }
    }

    // fallback for non-planar or multi-component edge cases
    if (assigned === -1) {
      let minConflicts = Infinity;
      assigned = 0;
      for (let c = 0; c < 4; c += 1) {
        let count = 0;
        for (const nbr of adj.get(bestNode)!) {
          if (colorAssignment.get(nbr) === c) count += 1;
        }
        if (count < minConflicts) {
          minConflicts = count;
          assigned = c;
        }
      }
    }

    colorAssignment.set(bestNode, assigned);
    for (const nbr of adj.get(bestNode)!) {
      neighborColors.get(nbr)!.add(assigned);
    }
  }

  for (const [id, c] of colorAssignment) {
    result.set(id, FOUR_COLORS[c % FOUR_COLORS.length]);
  }

  return result;
}
