#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <organization-slug-or-id> [ckan-sysadmin-user]" >&2
  exit 1
fi

ORG_ID="$1"
CKAN_SYSADMIN_USER="${2:-admin}"

if [[ -z "$ORG_ID" ]]; then
  echo "Organization identifier is required" >&2
  exit 1
fi

DOCKER_CMD=${DOCKER_CMD:-"sudo docker"}

${DOCKER_CMD} exec -i \
  -e CKAN_PURGE_ORG="$ORG_ID" \
  -e CKAN_PURGE_USER="$CKAN_SYSADMIN_USER" \
  ckan ckan shell <<'PY'
import os
from ckan.plugins import toolkit
from ckan import model

org_id = os.environ['CKAN_PURGE_ORG']
user_name = os.environ['CKAN_PURGE_USER']

context = {
    'model': model,
    'session': model.Session,
    'user': user_name,
    'ignore_auth': True,
}

toolkit.get_action('organization_purge')(context, {'id': org_id})
print(f'Organization "{org_id}" purged successfully.')
PY
