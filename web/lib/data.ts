import type {
  Catalog,
  EntityDocument,
  EntityIndex,
  FeatureCollection,
  TimelineEntry
} from "@/lib/types";

const API_ROOT = "/api/static";
const DB_NAME = "hm-atlas-cache-v3";
const STORE_NAME = "kv";
const MAX_LAYER_MEMORY_CACHE = 16;

const memoryLayerCache = new Map<number, FeatureCollection>();
const memoryJsonCache = new Map<string, unknown>();
const inflightRequests = new Map<string, Promise<unknown>>();

function encodePath(path: string) {
  return String(path)
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

function openCacheDb(): Promise<IDBDatabase | null> {
  if (typeof window === "undefined" || !("indexedDB" in window)) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    try {
      const request = window.indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME);
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function idbGet<T>(key: string): Promise<T | null> {
  const db = await openCacheDb();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readonly");
      const req = tx.objectStore(STORE_NAME).get(key);
      req.onsuccess = () => resolve((req.result as T) ?? null);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function idbSet<T>(key: string, value: T): Promise<void> {
  const db = await openCacheDb();
  if (!db) return;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    } catch {
      resolve();
    }
  });
}

function setMemoryLayer(year: number, data: FeatureCollection) {
  if (memoryLayerCache.has(year)) {
    memoryLayerCache.delete(year);
  } else if (memoryLayerCache.size >= MAX_LAYER_MEMORY_CACHE) {
    const oldestKey = memoryLayerCache.keys().next().value;
    if (oldestKey !== undefined) {
      memoryLayerCache.delete(oldestKey);
    }
  }
  memoryLayerCache.set(year, data);
}

export function getCachedLayer(year: number): FeatureCollection | null {
  const hit = memoryLayerCache.get(year);
  if (!hit) return null;
  // refresh lru order
  memoryLayerCache.delete(year);
  memoryLayerCache.set(year, hit);
  return hit;
}

export async function fetchJson<T = unknown>(path: string, useCache = true): Promise<T> {
  if (useCache && memoryJsonCache.has(path)) {
    return memoryJsonCache.get(path) as T;
  }

  const existing = inflightRequests.get(path);
  if (existing) return existing as Promise<T>;

  const task = (async () => {
    if (useCache) {
      const cached = await idbGet<T>(`json:${path}`);
      if (cached) {
        memoryJsonCache.set(path, cached);
        return cached;
      }
    }

    // directly fetch static assets, falling back to api route if necessary
    const directUrl = `/${encodePath(path)}`;
    let response: Response;
    try {
      response = await fetch(directUrl, {
        headers: { Accept: "application/json, application/geo+json" }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch {
      response = await fetch(`${API_ROOT}/${encodePath(path)}`, {
        headers: { Accept: "application/json" }
      });
    }
    if (!response.ok) {
      throw new Error(`Could not load ${path} (${response.status})`);
    }
    const data = (await response.json()) as T;
    if (useCache) {
      memoryJsonCache.set(path, data);
      void idbSet(`json:${path}`, data);
    }
    return data;
  })();

  inflightRequests.set(path, task);
  try {
    return await task;
  } finally {
    inflightRequests.delete(path);
  }
}

export async function fetchLayer(entry: TimelineEntry): Promise<FeatureCollection> {
  if (!entry) throw new Error("No layer selected");
  const memoryHit = getCachedLayer(entry.year);
  if (memoryHit) return memoryHit;

  const idbKey = `layer:${entry.year}`;
  const idbHit = await idbGet<FeatureCollection>(idbKey);
  if (idbHit) {
    setMemoryLayer(entry.year, idbHit);
    return idbHit;
  }

  // fetch geojson directly from data/geojson/${year}.geojson
  let data: FeatureCollection;
  try {
    data = await fetchJson<FeatureCollection>(`data/geojson/${entry.year}.geojson`, false);
  } catch {
    data = await fetchJson<FeatureCollection>(
      entry.file_path || `data/dist/spatial/web/${entry.year}.geojson`,
      false
    );
  }
  setMemoryLayer(entry.year, data);
  void idbSet(idbKey, data);
  return data;
}

export function prefetchAdjacentLayers(timeline: TimelineEntry[], currentIndex: number) {
  if (typeof window === "undefined" || !timeline.length) return;
  const schedule =
    "requestIdleCallback" in window
      ? (cb: () => void) => window.requestIdleCallback(cb, { timeout: 1200 })
      : (cb: () => void) => window.setTimeout(cb, 120);

  schedule(() => {
    for (const offset of [1, -1, 2, -2]) {
      const neighbour = timeline[currentIndex + offset];
      if (neighbour && !memoryLayerCache.has(neighbour.year)) {
        fetchLayer(neighbour).catch(() => {});
      }
    }
  });
}

export async function fetchEntityDetail(item: EntityIndex): Promise<EntityDocument> {
  const path = item.path || `data/entities/${item.type}/${item.id}.json`;
  return fetchJson<EntityDocument>(path, true);
}

export async function fetchLand(): Promise<FeatureCollection> {
  const idbKey = "geo:land";
  const cached = await idbGet<FeatureCollection>(idbKey);
  if (cached) return cached;

  // fetch land background directly from data/geojson/land.geojson
  let data: FeatureCollection;
  try {
    data = await fetchJson<FeatureCollection>("data/geojson/land.geojson", false);
  } catch {
    const response = await fetch("/geo/land.geojson");
    if (!response.ok) throw new Error("Could not load the land background");
    data = (await response.json()) as FeatureCollection;
  }
  void idbSet(idbKey, data);
  return data;
}

export async function fetchCatalog(): Promise<Catalog> {
  const [timeline, rawEntities, sources] = await Promise.all([
    fetchJson<Catalog["timeline"]>("data/dist/catalog/timeline.json", false),
    fetchJson<Catalog["entities"]>("data/dist/catalog/entities-summary.json").catch(() =>
      fetchJson<Catalog["entities"]>("data/dist/catalog/entities-index.json")
    ),
    fetchJson<Catalog["sources"]>("data/dist/catalog/sources-index.json")
  ]);

  const entities = (rawEntities || []).map((item) => ({
    ...item,
    path: item.path || `data/entities/${item.type}/${item.id}.json`,
    observed_year_count:
      item.observed_year_count ??
      (Array.isArray(item.observed_years) ? item.observed_years.length : undefined)
  }));

  return { timeline, entities, sources };
}
