#!/usr/bin/env bash
# Restore dump KJ ke database PostgreSQL baru untuk KMS (Odoo 16 CE).
# Usage:
#   ./restore_db.sh /path/to/kj.dump kms
#   ./restore_db.sh /path/to/kj.sql kms
#   DB_USER=odoo DB_HOST=localhost ./restore_db.sh kj.dump kms
#
# Opsional filestore:
#   FILESTORE_SRC=/path/to/filestore/kj FILESTORE_DST=/var/lib/odoo/filestore/kms ./restore_db.sh kj.dump kms

set -euo pipefail

DUMP_PATH="${1:-}"
NEW_DB="${2:-kms}"
DB_USER="${DB_USER:-odoo}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
PSQL=(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER")
CREATEDB=(createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER")
DROPDB=(dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER")
PG_RESTORE=(pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER")

if [[ -z "$DUMP_PATH" || ! -f "$DUMP_PATH" ]]; then
  echo "Usage: $0 /path/to/kj.dump|kj.sql <new_db_name>"
  exit 1
fi

echo "==> Target database: ${NEW_DB}"
echo "==> Dump file: ${DUMP_PATH}"

if "${PSQL[@]}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${NEW_DB}'" | grep -q 1; then
  echo "Database ${NEW_DB} already exists."
  read -r -p "Drop and recreate? [y/N] " ans
  if [[ "${ans:-}" != "y" && "${ans:-}" != "Y" ]]; then
    echo "Aborted."
    exit 1
  fi
  "${DROPDB[@]}" --if-exists "$NEW_DB"
fi

echo "==> Creating database ${NEW_DB}"
"${CREATEDB[@]}" -O "$DB_USER" -T template0 -E UTF8 "$NEW_DB"

case "$DUMP_PATH" in
  *.sql)
    echo "==> Restoring SQL dump"
    "${PSQL[@]}" -d "$NEW_DB" -v ON_ERROR_STOP=1 -f "$DUMP_PATH"
    ;;
  *.dump|*.backup|*.fc)
    echo "==> Restoring custom-format dump"
    # --no-owner/--no-acl: aman saat role PG berbeda antara sumber dan target
    "${PG_RESTORE[@]}" --no-owner --no-acl -d "$NEW_DB" "$DUMP_PATH"
    ;;
  *)
    # Deteksi format pg_dump
    if file "$DUMP_PATH" | grep -qi 'PostgreSQL custom'; then
      "${PG_RESTORE[@]}" --no-owner --no-acl -d "$NEW_DB" "$DUMP_PATH"
    else
      "${PSQL[@]}" -d "$NEW_DB" -v ON_ERROR_STOP=1 -f "$DUMP_PATH"
    fi
    ;;
esac

if [[ -n "${FILESTORE_SRC:-}" && -n "${FILESTORE_DST:-}" ]]; then
  echo "==> Copying filestore: ${FILESTORE_SRC} -> ${FILESTORE_DST}"
  mkdir -p "$(dirname "$FILESTORE_DST")"
  rsync -a --delete "${FILESTORE_SRC%/}/" "${FILESTORE_DST%/}/"
fi

echo "==> Done. Next steps:"
echo "    1. Pastikan odoo.conf addons_path mencakup modul custom KJ."
echo "    2. Start Odoo / update: odoo-bin -d ${NEW_DB} -u base --stop-after-init"
echo "    3. Edit kms_from_kj/company_kms.json"
echo "    4. odoo-bin shell -d ${NEW_DB} < kms_from_kj/sanitize_kms.py"
echo "    ATAU: odoo-bin shell -d ${NEW_DB} -c odoo.conf <<'PY'"
echo "    exec(open('kms_from_kj/sanitize_kms.py').read())"
echo "    PY"
