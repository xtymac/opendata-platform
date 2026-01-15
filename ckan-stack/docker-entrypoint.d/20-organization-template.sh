#!/bin/bash

OLD_OPTS=$(set +o)
set -euo pipefail
trap 'eval "$OLD_OPTS"' RETURN

TEMPLATE="/srv/app/src/ckan/ckan/templates/organization/snippets/organization_item.html"
ORIGINAL_CALL="{{ h.markdown_extract(organization.description, extract_length=80) }}"
INTERIM_CALL="{{ h.snippet_text(organization.description, length=80, whole_word=False) }}"
REPLACEMENT_CALL="{{ h.truncate(h.markdown_extract(organization.description, extract_length=0), length=80, whole_word=False) }}"

if [ ! -f "$TEMPLATE" ]; then
  echo "[custom-entrypoint] organization snippet template not found at $TEMPLATE; skipping." >&2
  exit 0
fi

python - <<'PY'
from pathlib import Path
import sys

path = Path("/srv/app/src/ckan/ckan/templates/organization/snippets/organization_item.html")
original = "{{ h.markdown_extract(organization.description, extract_length=80) }}"
interim = "{{ h.snippet_text(organization.description, length=80, whole_word=False) }}"
replacement = "{{ h.truncate(h.markdown_extract(organization.description, extract_length=0), length=80, whole_word=False) }}"

text = path.read_text()

if replacement in text:
    print("[custom-entrypoint] organization snippet template already uses truncate-based summary; skipping.")
    raise SystemExit(0)

for needle in (interim, original):
    if needle in text:
        path.write_text(text.replace(needle, replacement))
        print("[custom-entrypoint] Updated organization snippet template to use truncate-based summary.")
        break
else:
    print(
        "[custom-entrypoint] expected description snippet call not found in template; skipping.",
        file=sys.stderr,
    )
PY
