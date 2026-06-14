#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <git-tag> [nuitka-out-dir] [release-out-dir] [appimagetool-path]" >&2
  exit 1
}

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  usage
fi

DIST_ROOT="${2:-dist/nuitka}"
OUT_DIR="${3:-dist/release}"
APPIMAGETOOL="${4:-./appimagetool}"

dist_dir="$(find "$DIST_ROOT" -maxdepth 1 -type d -name '*.dist' | sort | head -1)"
if [[ -z "$dist_dir" ]]; then
  echo "Could not find Nuitka *.dist folder under $DIST_ROOT" >&2
  exit 1
fi

if [[ -x "$dist_dir/cheremsha" ]]; then
  bin_name="cheremsha"
elif [[ -x "$dist_dir/main.bin" ]]; then
  bin_name="main.bin"
else
  echo "Expected cheremsha or main.bin in $dist_dir" >&2
  exit 1
fi

if [[ ! -x "$APPIMAGETOOL" ]]; then
  echo "appimagetool not found or not executable: $APPIMAGETOOL" >&2
  exit 1
fi

appdir="$OUT_DIR/cheremsha.AppDir"
rm -rf "$appdir"
mkdir -p "$appdir/usr"
cp -a "$dist_dir"/. "$appdir/usr/"

cat >"$appdir/AppRun" <<EOF
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
exec "\$HERE/usr/$bin_name" "\$@"
EOF
chmod +x "$appdir/AppRun"

cp scripts/ci/cheremsha.desktop "$appdir/"
cp src/stream_cheremsha/assets/icon.png "$appdir/cheremsha.png"

mkdir -p "$OUT_DIR"
appimage_path="$OUT_DIR/Cheremsha-${TAG}-linux-x86_64.AppImage"
rm -f "$appimage_path"

ARCH=x86_64 "$APPIMAGETOOL" "$appdir" "$appimage_path"

if [[ ! -f "$appimage_path" ]]; then
  echo "AppImage was not created: $appimage_path" >&2
  exit 1
fi

chmod +x "$appimage_path"
echo "Created $appimage_path"
