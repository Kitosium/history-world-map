#!/usr/bin/env python3
"""Move entity documents into per-type directories.

Layout::

    data/entities/<type>/<id>.json

``<type>`` is the normalized value from ``data/taxonomies/entity-types.json``
(for example ``state``, ``kingdom``, ``empire``, ``civilization``).
The ``dynasties`` directory is left untouched
because dynasty documents have a different shape.

The script is idempotent: files already in the right directory are skipped.
Use ``--dry-run`` to preview the moves.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    ENTITY_NON_ENTITY_DIRS,
    ENTITY_ROOT,
    entity_path,
    iter_entity_files,
    read_json,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print planned moves only")
    args = parser.parse_args()

    moves: Dict[Path, Path] = {}
    duplicates: Dict[str, list[Path]] = collections.defaultdict(list)
    counts = collections.Counter()

    for source in iter_entity_files():
        try:
            doc = read_json(source)
        except Exception as exc:
            print(f"  ✗ cannot read {source}: {exc}")
            continue
        eid = doc.get("id") or source.stem
        duplicates[eid].append(source)
        target = entity_path(eid, doc.get("type", "state"))
        counts[target.parent.name] += 1
        if source.resolve() != target.resolve():
            moves[source] = target

    if duplicates:
        shared = {eid: paths for eid, paths in duplicates.items() if len(paths) > 1}
        if shared:
            print("Duplicate entity ids found; resolve before moving:")
            for eid, paths in sorted(shared.items()):
                print(f"  ! {eid}: {', '.join(str(p) for p in paths)}")
            return 1

    print(f"  • {sum(counts.values())} entity documents")
    print(f"  • {len(moves)} files need to move")

    if args.dry_run:
        for source, target in sorted(moves.items()):
            print(f"  → {source.relative_to(ENTITY_ROOT.parent)} → {target.relative_to(ENTITY_ROOT.parent)}")
        return 0

    moved = 0
    for source, target in sorted(moves.items()):
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"  ✗ target already exists: {target}")
            return 1
        source.rename(target)
        moved += 1

    # remove now-empty type directories, but never the source root itself.
    for directory in sorted(ENTITY_ROOT.iterdir()):
        if not directory.is_dir() or directory.name in ENTITY_NON_ENTITY_DIRS:
            continue
        if not any(directory.iterdir()):
            directory.rmdir()
            print(f"  – removed empty directory {directory.name}/")

    print(f"  ✓ moved {moved} files")
    for folder, count in sorted(counts.items()):
        print(f"    {folder}/: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
