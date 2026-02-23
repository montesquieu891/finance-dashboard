#!/usr/bin/env sh
set -eu

: "${PORT:=80}"
: "${API_INTERNAL_URL:=api:8000}"

envsubst '${PORT} ${API_INTERNAL_URL}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
