#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.0.0}"
APP_NAME="CI-Nurse"
PKG_NAME="ci-nurse"
ARCH="$(dpkg --print-architecture)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_ROOT="$ROOT/package_root"
OUT_DIR="$ROOT/installer"

cd "$ROOT"

rm -rf "$PKG_ROOT"
mkdir -p "$OUT_DIR"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/opt/ci-nurse"
mkdir -p "$PKG_ROOT/usr/share/applications"

cp "$ROOT/dist/$APP_NAME" "$PKG_ROOT/opt/ci-nurse/$APP_NAME"
chmod +x "$PKG_ROOT/opt/ci-nurse/$APP_NAME"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: CI Nurse
Description: CI Nurse desktop client
EOF

cat > "$PKG_ROOT/usr/share/applications/ci-nurse.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CI Nurse
Comment=CI Nurse desktop client
Exec=/opt/ci-nurse/CI-Nurse
Terminal=false
Categories=Development;Utility;
EOF

chmod 644 "$PKG_ROOT/usr/share/applications/ci-nurse.desktop"

dpkg-deb --build \
  "$PKG_ROOT" \
  "$OUT_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
