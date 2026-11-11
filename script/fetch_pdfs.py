#!/usr/bin/env python3
"""Download and verify public source PDFs listed in ``data/sources/manifests/pdf.json``.

Only files explicitly marked ``access_type: open_access`` in the manifest are
downloaded. Copyrighted sources stay as links in their source records and are
never copied into the repository.

Examples::

    python3 script/fetch_pdfs.py --check
    python3 script/fetch_pdfs.py
    python3 script/fetch_pdfs.py --source src-dai-viet --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "data" / "sources" / "manifests" / "pdf.json"
USER_AGENT = "history-world-map/1.0 (+source-pdf-fetch)"


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else BASE_DIR / path


def describe(entry: Dict[str, Any]) -> str:
    return entry.get("label") or entry.get("id") or entry.get("path") or "pdf"


def verify(entry: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    path = resolve(entry["path"])
    if not path.exists():
        return [f"missing file: {path}"]
    size = path.stat().st_size
    expected_size = entry.get("bytes")
    if expected_size is not None and size != expected_size:
        problems.append(f"size {size} != {expected_size}")
    expected_hash = entry.get("sha256")
    if expected_hash and sha256_file(path) != expected_hash:
        problems.append("sha256 mismatch")
    return problems


def download(entry: Dict[str, Any], timeout: int, retries: int) -> None:
    url = entry["url"]
    destination = resolve(entry["path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response, open(partial, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            expected_size = entry.get("bytes")
            actual_size = partial.stat().st_size
            if expected_size is not None and actual_size != expected_size:
                raise ValueError(f"downloaded {actual_size} bytes, expected {expected_size}")
            expected_hash = entry.get("sha256")
            if expected_hash and sha256_file(partial) != expected_hash:
                raise ValueError("sha256 mismatch")
            os.replace(partial, destination)
            return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"download failed after {retries} attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify local files without downloading")
    parser.add_argument("--force", action="store_true", help="replace valid local files")
    parser.add_argument("--source", help="only process one source_id")
    parser.add_argument("--timeout", type=int, default=180, help="download timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="download attempts")
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"missing manifest: {MANIFEST_PATH}", file=sys.stderr)
        return 1
    manifest = read_json(MANIFEST_PATH)
    downloads = manifest.get("downloads") or []
    if args.source:
        downloads = [item for item in downloads if item.get("source_id") == args.source]
    if not downloads:
        print("no matching downloads", file=sys.stderr)
        return 1

    failures = 0
    downloaded = 0
    verified = 0
    for entry in downloads:
        label = describe(entry)
        if entry.get("access_type") not in (None, "open_access"):
            print(f"  skip  {label} (access_type={entry.get('access_type')})")
            continue
        problems = verify(entry)
        if not problems and not args.force:
            print(f"  ok    {label}")
            verified += 1
            continue
        if args.check:
            print(f"  FAIL  {label}: {', '.join(problems) or 'forced re-check'}")
            failures += 1
            continue
        print(f"  get   {label}")
        try:
            download(entry, args.timeout, args.retries)
            problems = verify(entry)
            if problems:
                raise RuntimeError("; ".join(problems))
            downloaded += 1
            print(f"  ok    {label}")
        except Exception as exc:  # noqa: BLE001 - report per-file failure
            print(f"  FAIL  {label}: {exc}")
            failures += 1

    print(
        f"\n{verified} verified, {downloaded} downloaded, {failures} failed "
        f"({len(downloads)} entries)"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
