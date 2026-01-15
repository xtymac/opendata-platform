#!/bin/bash

if [ -z "${CKAN_INI:-}" ]; then
  echo "CKAN_INI is not set; skipping custom config tooling" >&2
  return 0 2>/dev/null || exit 0
fi

update_setting() {
  local key="$1"
  local value="$2"
  if [ -n "$value" ]; then
    ckan config-tool "$CKAN_INI" "$key=$value"
  fi
}

update_setting "SECRET_KEY" "${CKAN__SECRET_KEY:-}"
update_setting "WTF_CSRF_SECRET_KEY" "${CKAN__WTF__CSRF__SECRET_KEY:-}"
update_setting "api_token.jwt.encode.secret" "${CKAN__API_TOKEN__JWT__ENCODE__SECRET:-}"
update_setting "api_token.jwt.decode.secret" "${CKAN__API_TOKEN__JWT__DECODE__SECRET:-}"
update_setting "ckan.datapusher.api_token" "${CKAN__DATAPUSHER__API_TOKEN:-}"
update_setting "mlit.api_key" "${CKAN__MLIT__API_KEY:-}"
update_setting "content_security_policy" "${CKAN__CONTENT__SECURITY__POLICY:-}"
update_setting "ckan.locale_default" "${CKAN__LOCALE__DEFAULT:-}"
update_setting "ckan.locales_offered" "${CKAN__LOCALES__OFFERED:-}"

echo "[custom-entrypoint] Applied CKAN config overrides from environment."
