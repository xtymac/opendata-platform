#!/bin/bash

set -euo pipefail

EXTENSION_PATH="/srv/app/src/ckanext-timeseries"

if [ -d "$EXTENSION_PATH" ]; then
  echo "[custom-entrypoint] Installing ckanext-timeseries from $EXTENSION_PATH"
  pip install --no-deps --editable "$EXTENSION_PATH"
  # Ensure runtime dependencies installed
  pip install iso8601 PasteDeploy
else
  echo "[custom-entrypoint] ckanext-timeseries not found at $EXTENSION_PATH" >&2
fi
