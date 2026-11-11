import type {
  FeatureMetrics,
  GeoGeometry,
  Position,
  Transform,
  View
} from "@/lib/types";

export const WORLD_SIZE = 1000;
export const MAX_LAT = 85;

export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function project(lon: number, lat: number): Position {
  const safeLat = clamp(lat, -MAX_LAT, MAX_LAT);
  const x = ((lon + 180) / 360) * WORLD_SIZE;
  const radians = (safeLat * Math.PI) / 180;
  const y = ((1 - Math.log(Math.tan(Math.PI / 4 + radians / 2)) / Math.PI) / 2) * WORLD_SIZE;
  return [x, y];
}

export function unproject(x: number, y: number): Position {
  const lon = (x / WORLD_SIZE) * 360 - 180;
  const lat = ((2 * Math.atan(Math.exp((1 - (2 * y) / WORLD_SIZE) * Math.PI)) - Math.PI / 2) * 180) / Math.PI;
  return [lon, lat];
}

export function geometryToPath(geometry: GeoGeometry | null | undefined) {
  if (!geometry) return "";
  const polygons =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];
  const parts: string[] = [];
  for (const polygon of polygons) {
    for (const ring of polygon) {
      if (!ring || ring.length < 3) continue;
      for (let i = 0; i < ring.length; i += 1) {
        const point = ring[i];
        const [x, y] = project(point[0], point[1]);
        parts.push(`${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`);
      }
      parts.push("Z");
    }
  }
  return parts.join("");
}

function ringMetrics(ring: Position[]): FeatureMetrics {
  let area = 0;
  let cx = 0;
  let cy = 0;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (let i = 0; i < ring.length; i += 1) {
    const [lon, lat] = ring[i];
    const [x, y] = project(lon, lat);
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    const next = ring[(i + 1) % ring.length];
    const [nx, ny] = project(next[0], next[1]);
    const cross = x * ny - nx * y;
    area += cross;
    cx += (x + nx) * cross;
    cy += (y + ny) * cross;
  }

  area /= 2;
  if (Math.abs(area) < 1e-9) {
    return {
      area: 0,
      cx: (minX + maxX) / 2,
      cy: (minY + maxY) / 2,
      bbox: [minX, minY, maxX, maxY]
    };
  }
  cx /= 6 * area;
  cy /= 6 * area;
  return { area: Math.abs(area), cx, cy, bbox: [minX, minY, maxX, maxY] };
}

export function featureMetrics(geometry: GeoGeometry | null | undefined): FeatureMetrics {
  if (!geometry) {
    return { area: 0, cx: 0, cy: 0, bbox: [0, 0, 0, 0] };
  }
  const polygons =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];
  let totalArea = 0;
  let best: FeatureMetrics | null = null;
  let bbox: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const polygon of polygons) {
    const exterior = polygon[0];
    if (!exterior || exterior.length < 3) continue;
    const metrics = ringMetrics(exterior);
    totalArea += metrics.area;
    if (!best || metrics.area > best.area) best = metrics;
    bbox = [
      Math.min(bbox[0], metrics.bbox[0]),
      Math.min(bbox[1], metrics.bbox[1]),
      Math.max(bbox[2], metrics.bbox[2]),
      Math.max(bbox[3], metrics.bbox[3])
    ];
  }
  if (!best) {
    return { area: 0, cx: 0, cy: 0, bbox: [0, 0, 0, 0] };
  }
  return { area: totalArea, cx: best.cx, cy: best.cy, bbox };
}

/**
 * single-pass geometry processor: projects each coordinate once to produce both
 * the svg path string and the polygon centroid/area/bounding-box metrics.
 */
export function processFeatureGeometry(geometry: GeoGeometry | null | undefined): {
  path: string;
  metrics: FeatureMetrics;
} {
  if (!geometry) {
    return {
      path: "",
      metrics: { area: 0, cx: 0, cy: 0, bbox: [0, 0, 0, 0] }
    };
  }
  const polygons =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];

  const parts: string[] = [];
  let totalArea = 0;
  let best: FeatureMetrics | null = null;
  let bbox: [number, number, number, number] = [Infinity, Infinity, -Infinity, -Infinity];

  for (const polygon of polygons) {
    for (let r = 0; r < polygon.length; r += 1) {
      const ring = polygon[r];
      if (!ring || ring.length < 3) continue;

      const projected: Position[] = new Array(ring.length);
      for (let i = 0; i < ring.length; i += 1) {
        const pt = project(ring[i][0], ring[i][1]);
        projected[i] = pt;
        parts.push(`${i === 0 ? "M" : "L"}${pt[0].toFixed(2)} ${pt[1].toFixed(2)}`);
      }
      parts.push("Z");

      if (r === 0) {
        let area = 0;
        let cx = 0;
        let cy = 0;
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        for (let i = 0; i < projected.length; i += 1) {
          const [x, y] = projected[i];
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
          const [nx, ny] = projected[(i + 1) % projected.length];
          const cross = x * ny - nx * y;
          area += cross;
          cx += (x + nx) * cross;
          cy += (y + ny) * cross;
        }

        area /= 2;
        const ringMetric: FeatureMetrics =
          Math.abs(area) < 1e-9
            ? {
                area: 0,
                cx: (minX + maxX) / 2,
                cy: (minY + maxY) / 2,
                bbox: [minX, minY, maxX, maxY]
              }
            : {
                area: Math.abs(area),
                cx: cx / (6 * area),
                cy: cy / (6 * area),
                bbox: [minX, minY, maxX, maxY]
              };

        totalArea += ringMetric.area;
        if (!best || ringMetric.area > best.area) best = ringMetric;
        bbox = [
          Math.min(bbox[0], minX),
          Math.min(bbox[1], minY),
          Math.max(bbox[2], maxX),
          Math.max(bbox[3], maxY)
        ];
      }
    }
  }

  return {
    path: parts.join(""),
    metrics: best
      ? { area: totalArea, cx: best.cx, cy: best.cy, bbox }
      : { area: 0, cx: 0, cy: 0, bbox: [0, 0, 0, 0] }
  };
}

export function isBboxVisible(
  bbox: [number, number, number, number],
  transform: Transform,
  width: number,
  height: number,
  margin = 40
) {
  const minX = bbox[0] * transform.scale + transform.tx;
  const minY = bbox[1] * transform.scale + transform.ty;
  const maxX = bbox[2] * transform.scale + transform.tx;
  const maxY = bbox[3] * transform.scale + transform.ty;
  return (
    maxX >= -margin &&
    minX <= width + margin &&
    maxY >= -margin &&
    minY <= height + margin
  );
}

export function viewToTransform(view: View, width: number, height: number): Transform {
  const scale = (width * view.zoom) / WORLD_SIZE;
  const [cx, cy] = project(view.lon, view.lat);
  return {
    scale,
    tx: width / 2 - cx * scale,
    ty: height / 2 - cy * scale
  };
}

export function worldToScreen(x: number, y: number, transform: Transform): Position {
  return [x * transform.scale + transform.tx, y * transform.scale + transform.ty];
}

export function screenToWorld(x: number, y: number, transform: Transform): Position {
  return [(x - transform.tx) / transform.scale, (y - transform.ty) / transform.scale];
}

export function clampView(view: View): View {
  return {
    lon: clamp(view.lon, -180, 180),
    lat: clamp(view.lat, -72, 72),
    zoom: clamp(view.zoom, 1, 42)
  };
}

export function fitView(
  bbox: [number, number, number, number],
  width: number,
  height: number,
  padding = 0.9
): View {
  const [x1, y1] = project(bbox[0], bbox[3]);
  const [x2, y2] = project(bbox[2], bbox[1]);
  const boxWidth = Math.max(1, Math.abs(x2 - x1));
  const boxHeight = Math.max(1, Math.abs(y2 - y1));
  const scale = Math.max(width / boxWidth, height / boxHeight) * padding;
  const zoom = (scale * WORLD_SIZE) / width;
  const [lon, lat] = unproject((x1 + x2) / 2, (y1 + y2) / 2);
  return clampView({ lon, lat, zoom });
}

export function panView(view: View, dx: number, dy: number, width: number): View {
  const scale = (width * view.zoom) / WORLD_SIZE;
  const [cx, cy] = project(view.lon, view.lat);
  const [lon, lat] = unproject(cx - dx / scale, cy - dy / scale);
  return clampView({ ...view, lon, lat });
}

export function zoomViewAt(
  view: View,
  factor: number,
  anchorX: number,
  anchorY: number,
  width: number,
  height: number
): View {
  const transform = viewToTransform(view, width, height);
  const [wx, wy] = screenToWorld(anchorX, anchorY, transform);
  const zoom = clamp(view.zoom * factor, 1, 42);
  const scale = (width * zoom) / WORLD_SIZE;
  const cx = (width / 2 - (anchorX - wx * scale)) / scale;
  const cy = (height / 2 - (anchorY - wy * scale)) / scale;
  const [lon, lat] = unproject(cx, cy);
  return clampView({ lon, lat, zoom });
}

export function niceDistance(value: number) {
  if (!Number.isFinite(value) || value <= 0) return 100;
  const exponent = Math.floor(Math.log10(value));
  const base = 10 ** exponent;
  const fraction = value / base;
  let nice: number;
  if (fraction < 1.5) nice = 1;
  else if (fraction < 3.5) nice = 2;
  else if (fraction < 7.5) nice = 5;
  else nice = 10;
  return nice * base;
}

export function scaleBarMetrics(view: View, width: number) {
  const transform = viewToTransform(view, width, 1);
  const kmPerWorldUnit = (111.32 * Math.cos((view.lat * Math.PI) / 180) * 360) / WORLD_SIZE;
  const kmPerPixel = kmPerWorldUnit / transform.scale;
  const target = Math.min(150, Math.max(64, width * 0.16));
  const km = niceDistance(target * kmPerPixel);
  return { km, pixels: km / kmPerPixel };
}

export function graticulePath() {
  const parts: string[] = [];
  for (let lon = -180; lon <= 180; lon += 30) {
    const [x, y1] = project(lon, -80);
    const [, y2] = project(lon, 80);
    parts.push(`M${x.toFixed(1)} ${y1.toFixed(1)}L${x.toFixed(1)} ${y2.toFixed(1)}`);
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const [x1, y] = project(-180, lat);
    const [x2] = project(180, lat);
    parts.push(`M${x1.toFixed(1)} ${y.toFixed(1)}L${x2.toFixed(1)} ${y.toFixed(1)}`);
  }
  return parts.join("");
}

export function isVisible(
  [x, y]: Position,
  transform: Transform,
  width: number,
  height: number,
  margin = 80
) {
  const [sx, sy] = worldToScreen(x, y, transform);
  return sx > -margin && sx < width + margin && sy > -margin && sy < height + margin;
}
