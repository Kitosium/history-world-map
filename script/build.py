#!/usr/bin/env python3
"""Run the full data pipeline in the correct order.

Stages
------
1. ``migrate.py``   – apply canonical id migrations/merges;
2. ``sources.py``   – normalize bibliographic source records;
3. ``spatial.py``   – rebuild every yearly GeoJSON layer;
4. ``entities.py``  – normalize entities and attach provenance;
5. ``catalog.py``   – compile catalog, statistics and manifest;
6. ``optimize.py``  – write lightweight web GeoJSON copies;
7. ``validate.py``  – validate the result.

Examples
--------
    python3 script/build.py
    python3 script/build.py --hb-dir /tmp/hb --ne-path /tmp/ne10m.geojson
    python3 script/build.py --skip-download --strict
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(name: str, args: list[str], cwd: Path) -> None:
    print()
    print("=" * 78)
    print(f"▶ {name}")
    print("=" * 78, flush=True)
    started = time.monotonic()
    result = subprocess.run([PYTHON, str(SCRIPTS_DIR / name), *args], cwd=cwd)
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        raise SystemExit(f"✗ {name} failed with exit code {result.returncode} after {elapsed:.1f}s")
    print(f"✓ {name} finished in {elapsed:.1f}s", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild and validate the historical atlas dataset.")
    parser.add_argument("--hb-dir", type=Path, default=Path("/tmp/opencode/hb"),
                        help="Cache directory for historical-basemaps GeoJSON files")
    parser.add_argument("--ne-path", type=Path,
                        default=Path("/tmp/opencode/ne_10m_admin_0_countries.geojson"),
                        help="Path to the Natural Earth 1:10m Admin-0 GeoJSON")
    parser.add_argument("--skip-download", action="store_true",
                        help="Do not download missing upstream files (fail instead)")
    parser.add_argument("--skip-migrate", action="store_true",
                        help="Skip entity id migrations (useful for small data edits)")
    parser.add_argument("--skip-check", action="store_true",
                        help="Skip the final validation stage")
    parser.add_argument("--strict", action="store_true",
                        help="Treat validation warnings as errors")
    args = parser.parse_args()

    root = SCRIPTS_DIR.parent
    hb_dir = args.hb_dir
    ne_path = args.ne_path

    if args.skip_download:
        if not hb_dir.exists():
            raise SystemExit(f"✗ historical-basemaps cache not found: {hb_dir}")
        if not ne_path.exists():
            raise SystemExit(f"✗ Natural Earth file not found: {ne_path}")

    started = time.monotonic()
    if not args.skip_migrate:
        run("migrate.py", [], root)
    run("sources.py", [], root)
    run("spatial.py", ["--hb-dir", str(hb_dir), "--ne-path", str(ne_path)], root)
    run("entities.py", [], root)
    run("catalog.py", [], root)
    run("optimize.py", [], root)
    if not args.skip_check:
        run("validate.py", ["--strict"] if args.strict else [], root)

    print()
    print("=" * 78)
    print(f"✅ Pipeline complete in {time.monotonic() - started:.1f}s")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
