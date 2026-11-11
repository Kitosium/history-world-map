Interactive spatiotemporal historical atlas from 3500 BCE to 2026 CE, built with Next.js, TypeScript, and verified academic cartography.

---

## ⚙️ Installation

### Prerequisites
* **Node.js**: v20 or higher
* **Python**: v3.10 or higher (for compiling and validating data)

### Clone & Setup
```bash
# Clone the repository
git clone https://github.com/Kitosium/history-world-map.git
cd history-world-map

# Install dependencies and sync static data
npm install
```

---

## 🚀 Quick Usage

### Start Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build
```bash
npm run build
npm run start
```

### Static Data Synchronization
```bash
npm run sync-data
```

### TypeScript Validation
```bash
npm run typecheck
```

---

## 📂 Project Structure

```text
history-world-map/
├── data/                      # Canonical data source of truth
│   ├── aliases/               # ID migrations, merges, and spatial name mappings
│   ├── cache/                 # Pipeline build and coordinate caches
│   ├── dist/                  # Compiled distribution output (catalog & spatial)
│   ├── entities/              # Entity JSON documents categorized by type
│   ├── geography/             # Custom geographical features
│   ├── geojson/               # 51 historical GeoJSON layers + land background
│   ├── i18n/                  # Multi-language translation dictionaries
│   ├── schemas/               # JSON Schema validation definitions
│   ├── sources/               # Source metadata, manifests, and reference PDFs
│   ├── taxonomies/            # Entity and source tier taxonomies
│   └── manifest.json          # Dataset metadata and temporal coverage
├── docs/                      # Technical documentation
│   ├── architecture.md        # Web application architecture & rendering engine
│   └── pipeline.md            # Data compilation pipeline & geometry optimization
├── script/                    # Python data pipeline utilities
│   ├── build.py               # End-to-end pipeline orchestrator
│   ├── catalog.py             # Public catalog compiler
│   ├── optimize.py            # Geometry simplification & 4-color map coloring
│   ├── spatial.py             # Spatial layer builder
│   └── validate.py            # Strict schema and referential integrity validator
└── web/                       # Next.js 16 web application
    ├── app/                   # App Router pages, layout, and global styles
    ├── components/            # Modular React components (Canvas, Timeline, etc.)
    ├── lib/                   # Client utilities (data fetching, i18n, geo, colors)
    └── public/                # Static assets served directly by Next.js
```

---

## 🔧 CLI & Pipeline Scripts

| Command | Description |
| :--- | :--- |
| `python3 script/build.py` | Runs the full pipeline from raw data to web layers |
| `python3 script/optimize.py` | Simplifies geometry and computes 4-color assignment |
| `python3 script/catalog.py` | Generates search indices and timeline metadata |
| `python3 script/validate.py --strict` | Executes complete integrity audit (0 errors, 0 warnings) |
| `python3 script/dynasties.py` | Rebuilds Vietnamese dynastic succession records |
| `npm run sync-data` | Copies compiled distributions into `web/public/data/` |

---

## 🗺️ GeoJSON & 4-Color Map Theorem

All historical layers are stored in `data/geojson/<year>.geojson`. Each `Feature` adheres to the following specification:

```json
{
  "type": "Feature",
  "id": "feat-1945-vietnam",
  "properties": {
    "entity_id": "vietnam",
    "name": "Việt Nam",
    "subjecto": "vietnam",
    "partof": "vietnam",
    "valid_year": 1945,
    "color_index": 2
  },
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": [...]
  }
}
```

* `color_index`: Integer from `0` to `3` computed by graph coloring to prevent adjacent features from sharing colors.
* `valid_year`: The historical year represented by this layer snapshot.
* `entity_id`: Normalized slug referencing the canonical entity document in `data/entities/`.

---

## 🌐 Dynamic Internationalization (i18n)

Languages are defined dynamically in `web/lib/i18n.ts`:

```typescript
export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: "en", label: "English", badge: "EN" },
  { code: "vi", label: "Tiếng Việt", badge: "VI" }
];

export const LOCALES: Record<string, LocaleFormat> = {
  en: {
    formatDate: (year, month, day) => (day ? `${month}/${day}/${year}` : `${month}/${year}`),
    formatYear: (year) => (year < 0 ? `${Math.abs(year)} BCE` : `${year} CE`),
    eraSuffix: { bce: " BCE", ce: " CE" },
    wikiPrefix: "https://en.wikipedia.org/wiki/"
  },
  vi: {
    formatDate: (year, month, day) => (day ? `${day}/${month}/${year}` : `${month}/${year}`),
    formatYear: (year) => (year < 0 ? `${Math.abs(year)} TCN` : `${year}`),
    eraSuffix: { bce: " TCN", ce: "" },
    wikiPrefix: "https://vi.wikipedia.org/wiki/"
  }
};
```
No component modifications or hard-coded conditional branches are required.

---

## 📜 Data Sources & Academic Tiers

Data provenance is strictly categorized according to academic authority:

| Tier | Classification | Primary Sources |
| :---: | :--- | :--- |
| **Tier 1** | Official Primary Sources | *Đại Việt sử ký toàn thư*, *Đại Nam nhất thống chí*, *Records of the Grand Historian (Shiji)* |
| **Tier 2** | Secondary Scholarly Monographs | Đào Duy Anh, Lương Ninh, George Coedès, Vietnamese Institute of Archaeology |
| **Tier 3** | Authoritative Cartography | Natural Earth Vector (Admin-0 v5.1.2) |
| **Tier 4** | Scholarly Historical Atlases | Historical Basemaps (André Ourednik, EPFL / Lausanne) |
| **Tier 5** | General Reference & LOD | Wikidata, Wikipedia Linked Open Data |

---

## 📖 Documentation

* [Data Pipeline & Geometry Optimization](docs/pipeline.md)
* [Application Architecture & Rendering Engine](docs/architecture.md)

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE). Cartographic datasets retain their respective upstream licenses (Natural Earth Public Domain, Historical Basemaps CC BY-NC-SA 4.0).
