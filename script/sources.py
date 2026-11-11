#!/usr/bin/env python3
"""Normalise source records and attach licence, coverage and provenance metadata.

Only verifiable metadata is added. Unknown licences are left absent rather than
guessed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    SCHEMA_VERSION,
    SOURCE_CATALOG,
    SOURCES_DIR,
    TODAY,
    clean_text,
    normalize_language_map,
    read_json,
    write_json,
)

# metadata for regional / academic records, kept separately for auditability
ACADEMIC_METADATA: Dict[str, Dict[str, Any]] = {
    "src-dai-viet": {
        "type": "primary_chronicle",
        "license": {"name": "Public domain (historical text)", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "2879 BCE - 1675 CE (recorded narrative)",
            "spatial": "Đại Việt and neighbouring polities",
            "geometry": "descriptive narrative; no surveyed coordinates",
        },
    },
    "src-shiji": {
        "type": "primary_chronicle",
        "license": {"name": "Public domain (historical text)", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "c. 2600 BCE - 94 BCE (recorded narrative)",
            "spatial": "Han China, Nanyue and Inner Asia",
            "geometry": "descriptive narrative; no surveyed coordinates",
        },
    },
    "src-dai-nam": {
        "type": "primary_chronicle",
        "license": {"name": "Public domain (historical text)", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "19th century (Nguyễn dynasty)",
            "spatial": "Vietnam",
            "geometry": "administrative gazetteer descriptions",
        },
    },
    "src-dao-duy-anh": {
        "type": "academic_monograph",
        "license": {"name": "In copyright", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "prehistory - 19th century",
            "spatial": "Vietnam",
            "geometry": "historical-geographical reconstruction",
        },
    },
    "src-coedes": {
        "type": "academic_monograph",
        "license": {"name": "In copyright", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "1st - 15th century CE",
            "spatial": "Southeast Asia",
            "geometry": "historical-geographical synthesis",
        },
    },
    "src-luong-ninh": {
        "type": "academic_monograph",
        "license": {"name": "In copyright", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "2nd - 19th century CE",
            "spatial": "central and southern Vietnam",
            "geometry": "historical-geographical synthesis",
        },
    },
    "src-khao-co": {
        "type": "academic_monograph",
        "license": {"name": "In copyright", "spdx": "NOASSERTION"},
        "coverage": {
            "temporal": "Neolithic - 1st millennium CE",
            "spatial": "Vietnam",
            "geometry": "archaeological site locations and culture areas",
        },
    },
    "src-wikidata": {
        "type": "linked_open_data",
        "license": {"name": "Creative Commons CC0 1.0", "spdx": "CC0-1.0",
                    "url": "https://www.wikidata.org/wiki/Wikidata:Licensing"},
        "coverage": {
            "temporal": "all periods",
            "spatial": "global",
            "geometry": "none (labels, descriptions and identifiers only)",
        },
    },
}


def normalize_urls(existing: Any) -> List[Dict[str, Any]]:
    if isinstance(existing, dict):
        existing = existing.get("urls", [])
    urls: List[Dict[str, Any]] = []
    for item in existing or []:
        if isinstance(item, str):
            urls.append({"url": item, "access_type": "open_access"})
        elif isinstance(item, dict) and item.get("url"):
            urls.append(dict(item))
    return urls


def normalise_source(doc: Dict[str, Any]) -> Dict[str, Any]:
    sid = doc.get("id")
    catalog = SOURCE_CATALOG.get(sid, {})
    academic = ACADEMIC_METADATA.get(sid, {})

    doc["schema_version"] = SCHEMA_VERSION
    doc["type"] = catalog.get("type") or academic.get("type") or doc.get("type") or "unknown"
    title = doc.setdefault("title", {})
    canonical = normalize_language_map(title.get("canonical", {}))
    for lang, value in (catalog.get("title") or {}).items():
        canonical[lang] = value
    title["canonical"] = canonical

    if catalog.get("creators"):
        doc["creators"] = catalog["creators"]
    if catalog.get("publication"):
        publication = doc.setdefault("publication", {})
        for key, value in catalog["publication"].items():
            publication[key] = value

    urls = normalize_urls(doc.get("digital_access", {}))
    if catalog.get("digital_access"):
        existing_urls = {item.get("url") for item in urls}
        for item in catalog["digital_access"]:
            if item.get("url") not in existing_urls:
                urls.append(dict(item))
    if urls:
        doc["digital_access"] = urls

    if catalog.get("license") or academic.get("license"):
        doc["license"] = catalog.get("license") or academic.get("license")
    if catalog.get("coverage") or academic.get("coverage"):
        coverage = doc.setdefault("coverage", {})
        for key, value in (catalog.get("coverage") or academic.get("coverage") or {}).items():
            coverage[key] = value

    critique = doc.setdefault("critique_and_reliability", {})
    if catalog.get("tier"):
        critique["tier"] = catalog["tier"]
    if catalog.get("notes"):
        critique["historiographical_notes"] = catalog["notes"]
    if academic.get("coverage") and not critique.get("spatial_precision_rating"):
        critique["spatial_precision_rating"] = academic["coverage"].get("geometry", "descriptive")
    critique.setdefault("spatial_precision_rating", "not_applicable")

    doc["last_verified"] = TODAY

    order = [
        "id", "schema_version", "type", "title", "creators", "publication",
        "digital_access", "license", "coverage", "critique_and_reliability",
        "citation_formats", "last_verified",
    ]
    ordered = {key: doc[key] for key in order if key in doc}
    for key, value in doc.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def main() -> None:
    print("=" * 78)
    print("NORMALISE SOURCE RECORDS")
    print("=" * 78)
    count = 0
    for path in sorted(SOURCES_DIR.rglob("*.json")):
        doc = read_json(path)
        # skip generated manifests (they are not source records)
        if path.parent.name == "manifests":
            continue
        normalised = normalise_source(doc)
        write_json(path, normalised)
        count += 1
        print(f"  ✓ {normalised.get('id')} [{normalised.get('type')}]")
    print(f"✅ Normalised {count} source records.")


if __name__ == "__main__":
    main()
