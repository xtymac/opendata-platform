#!/bin/bash

set -euo pipefail

EXTENSION_PATH="/srv/app/src/ckanext-cesium_viewer"

if [ -d "$EXTENSION_PATH" ]; then
  echo "[custom-entrypoint] Installing ckanext-cesium_viewer from $EXTENSION_PATH"
  pip install --no-deps --editable "$EXTENSION_PATH"
else
  echo "[custom-entrypoint] ckanext-cesium_viewer not found at $EXTENSION_PATH" >&2
fi
