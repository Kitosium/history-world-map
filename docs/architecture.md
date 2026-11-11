# Architecture

**World History Atlas** is built with Next.js 16 (App Router), React 19, TypeScript, and Tailwind CSS, engineered for 60 FPS vector map rendering and zero-overhead static asset delivery.

---

## ⚙️ Core Architecture

```
Browser Client
  ├── MapCanvas (SVG Vector Projection + Mercator Transform)
  ├── Timeline (Interactive Scrubbing + Era Snapping)
  ├── SearchBox (Instant In-Memory Substring Index)
  └── DetailCard (Dynamic Entity Metadata & Wikipedia Links)
        │
        ├── Two-Tier Cache (Memory LRU Map + IndexedDB 'hm-atlas-cache-v3')
        │
        └── Direct Static Assets (/data/geojson/*.geojson, /data/dist/catalog/*.json)
```

---

## 🚀 Key Systems

### 1. Direct Static GeoJSON Delivery
* Layer files are located in `/data/geojson/<year>.geojson` and served directly by Next.js static file handling.
* Zero server-side API computation or runtime JSON parsing overhead.
* Idle prefetching automatically loads adjacent historical layers in the background via `requestIdleCallback`.

### 2. SVG Vector Canvas Engine
* Custom Mercator projection (`project(lon, lat)`) transforms spherical coordinates directly into SVG viewport coordinates.
* Label sizes are fixed uniformly across all political entities (`10px` compact, `11px` standard) to ensure clean readability without scale-induced text overlapping.
* Selected and hovered entities are highlighted using contrasting stroke ink and font-weight styles without triggering canvas layout shifts.

### 3. Extensible Multi-Language (i18n) Engine
* Language configuration is decoupled from UI components via `web/lib/i18n.ts`.
* Component code uses dynamic dictionary lookups (`getLocale(lang)`), completely avoiding hard-coded condition branches (`lang === "vi"`).
* New languages can be added simply by declaring a locale entry in `LOCALES` with date formatters, era names, and UI labels.

### 4. Two-Tier Client Caching
* **L1 Memory Cache**: Instant in-memory LRU map holding active and pre-fetched layers.
* **L2 IndexedDB Cache**: Persistent browser storage (`hm-atlas-cache-v3`) ensuring instant reloads across page sessions without network roundtrips.

---

## 📂 Component Directory

| Component | Path | Responsibility |
| :--- | :--- | :--- |
| `Atlas` | `web/components/Atlas.tsx` | Main application shell, state orchestration, keyboard shortcuts |
| `MapCanvas` | `web/components/MapCanvas.tsx` | SVG viewport, Mercator rendering, gestures (pan/zoom), labels |
| `Timeline` | `web/components/Timeline.tsx` | Multi-era timeline slider, playback controls, tick marks |
| `SearchBox` | `web/components/SearchBox.tsx` | Instant search for historical polities, dynasties, and aliases |
| `DetailCard` | `web/components/DetailCard.tsx` | Entity metadata, time range, territorial status, external sources |
| `Controls` | `web/components/Controls.tsx` | Theme toggle (Light/Dark/System), dynamic language picker, reset view |
