#!/bin/sh
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}
SLEEP_SECONDS=${BACKUP_INTERVAL_SECONDS:-86400}

mkdir -p "$BACKUP_DIR"

send_slack_alert() {
  if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    message=$1
    payload=$(printf '{"text":"%s"}' "$message")
    curl -sS -X POST -H "Content-Type: application/json" --data "$payload" "$SLACK_WEBHOOK_URL" >/dev/null || true
  fi
}

while true; do
  stamp=$(date -u +"%Y%m%dT%H%M%SZ")
  output_file="$BACKUP_DIR/${POSTGRES_DB}_${stamp}.dump"

  if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$output_file"; then
    echo "backup_ok file=$output_file"
  else
    echo "backup_failed" >&2
    send_slack_alert "Basket Monitor backup failed for database ${POSTGRES_DB}"
  fi

  find "$BACKUP_DIR" -name '*.dump' -type f -mtime +"$RETENTION_DAYS" -delete
  sleep "$SLEEP_SECONDS"
done