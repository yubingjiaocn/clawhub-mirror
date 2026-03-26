#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
BUILD_DIR="$PROJECT_ROOT/build"
ZIP_FILE="$BUILD_DIR/lambda.zip"

echo "==> Cleaning build directory"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/package"

echo "==> Installing dependencies"
pip install \
    --target "$BUILD_DIR/package" \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    -r "$BACKEND_DIR/requirements.txt" \
    --quiet

echo "==> Copying application code"
cp -r "$BACKEND_DIR/app" "$BUILD_DIR/package/app"
cp "$BACKEND_DIR/handler.py" "$BUILD_DIR/package/handler.py"

echo "==> Creating deployment zip"
cd "$BUILD_DIR/package"
zip -r "$ZIP_FILE" . -x "*.pyc" "__pycache__/*" "*.dist-info/*" --quiet

echo "==> Build complete: $ZIP_FILE"
ls -lh "$ZIP_FILE"
