# Data Pipeline

The **World History Atlas data pipeline** compiles, simplifies, color-codes, and validates historical boundary layers from 4000 BCE to 2026 CE.

---

## ⚙️ Overview

The pipeline transforms raw historical GIS data into highly optimized, topologically valid GeoJSON layers ready for instant static delivery in web browsers.

```
data/sources/ (Historical Basemaps + Natural Earth 1:10m)
  │
  ├──► script/spatial.py      ──► data/dist/spatial/by-year/*.geojson (Full Resolution)
  │
  ├──► script/optimize.py     ──► data/dist/spatial/web/*.geojson     (Simplified + 4-Color)
  │                            ──► data/geojson/*.geojson              (Static Web Assets)
  │
  ├──► script/catalog.py      ──► data/dist/catalog/*.json            (Search & Timeline Index)
  │
  └──► script/validate.py     ──► Strict Integrity Report
```

---

## 🔧 Pipeline Scripts

| Script | Purpose | Output |
| :--- | :--- | :--- |
| `script/spatial.py` | Assembles full-resolution spatial layers from source basemaps | `data/dist/spatial/by-year/*.geojson` |
| `script/optimize.py` | Simplifies geometry (Douglas–Peucker), computes 4-color map coloring | `data/geojson/*.geojson`, `data/dist/spatial/web/*.geojson` |
| `script/catalog.py` | Compiles entities index, timeline snapshots, and bibliographic records | `data/dist/catalog/*.json` |
| `script/validate.py` | Validates entity schemas, spatial properties, cross-references, and manifest | Verification report (`--strict`) |
| `script/dynasties.py` | Compiles dynastic succession index and Vietnamese historical chronologies | `data/dist/catalog/dynasties-index.json` |
| `script/migrate.py` | Applies entity ID migrations and alias mergers from `entity-aliases.json` | Updated entity files |
| `script/build.py` | Runs the full pipeline end-to-end in strict dependency order | All distribution artifacts |

---

## 🗺️ Geometry Optimization & Four-Color Theorem

### Douglas–Peucker Simplification
* Preserves coastal contours and border fidelity while reducing coordinate points by ~50%.
* Rings with bounding box area under visible thresholds are safely dropped, while designated historical island polities (e.g. Champa, Vietnam, British Isles, Aegean) are explicitly preserved.

### Four-Color Map Theorem Assignment
* Every feature in a historical snapshot layer is checked against adjacent features sharing boundary vertices or bounding-box intersections.
* A greedy graph-coloring algorithm assigns a palette index (`color_index` from `0` to `3`) such that no two adjacent polities share the same color.
* Eliminates arbitrary or subjective color choices, producing an aesthetically consistent cartographic view.

---

## 🚀 Running the Pipeline

Run the complete pipeline:

```bash
python3 script/build.py
```

Recompile catalog and optimize web layers:

```bash
python3 script/catalog.py
python3 script/optimize.py
```

Execute strict integrity verification:

```bash
python3 script/validate.py --strict
```
