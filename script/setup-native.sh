#!/usr/bin/env bash
# stage native node modules on a mmap-capable filesystem.
#
# android shared storage (/mnt/sdcard) cannot map native .node binaries, so
# lightningcss fails and next/swc falls back to wasm. this helper stages
# native packages on the root filesystem (both persistent storage and /tmp),
# which npm scripts expose through NODE_PATH. it ensures native binaries
# persist across system reboots.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PERSIST="/root/.local/share/native-node-modules"
DEST="${NODE_PATH:-/tmp/opencode/native}"
mkdir -p "$PERSIST" "$DEST/@next"

can_load() {
  (cd "$ROOT" && env -u NODE_PATH node -e "require('$1')" >/dev/null 2>&1)
}

# 1. if lightningcss-linux-arm64-gnu is in node_modules, copy to persistent storage and remove
if [ -d "$ROOT/node_modules/lightningcss-linux-arm64-gnu" ]; then
  mkdir -p "$PERSIST/lightningcss-linux-arm64-gnu"
  cp -a "$ROOT/node_modules/lightningcss-linux-arm64-gnu/." "$PERSIST/lightningcss-linux-arm64-gnu/"
  rm -rf "$ROOT/node_modules/lightningcss-linux-arm64-gnu"
  echo "synced lightningcss-linux-arm64-gnu -> $PERSIST"
fi

# 2. ensure both persistent storage and /tmp destination are populated
if [ -d "$PERSIST/lightningcss-linux-arm64-gnu" ]; then
  mkdir -p "$DEST/lightningcss-linux-arm64-gnu"
  cp -a "$PERSIST/lightningcss-linux-arm64-gnu/." "$DEST/lightningcss-linux-arm64-gnu/"
fi

# 3. next swc lockfile uses an unsupported syscall here, keep out of resolution path
if [ -d "$ROOT/node_modules/@next/swc-linux-arm64-gnu" ]; then
  rm -rf "$DEST/@next/swc-linux-arm64-gnu.disabled"
  mv "$ROOT/node_modules/@next/swc-linux-arm64-gnu" "$DEST/@next/swc-linux-arm64-gnu.disabled" 2>/dev/null || rm -rf "$ROOT/node_modules/@next/swc-linux-arm64-gnu"
fi

echo "native modules ready in $PERSIST and $DEST"
