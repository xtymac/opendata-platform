#!/bin/bash

set -euo pipefail

EXTENSION_PATH="/srv/app/src/ckanext-reclineview"

if [ -d "$EXTENSION_PATH" ]; then
  echo "[custom-entrypoint] Installing ckanext-reclineview from $EXTENSION_PATH"
  pip install --no-deps --editable "$EXTENSION_PATH"
else
  echo "[custom-entrypoint] ckanext-reclineview not found at $EXTENSION_PATH" >&2
fi
