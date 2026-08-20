#!/bin/bash
# Local Odoo backup for the Mac Mini (dump + filestore zip).
# Usage:
#   ./run_backup.sh
#   ./run_backup.sh KARUSINDO_200826
#   ODOO_DB=KARUSINDO_110826 ./run_backup.sh
set -u

export PATH="/Applications/Postgres.app/Contents/Versions/15/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

BACKUP_DIR="${BACKUP_DIR:-/Users/odoo-server/Backup}"
FILESTORE_BASE="${FILESTORE_BASE:-/Users/odoo-server/Library/Application Support/Odoo/filestore}"
DB_NAME="${1:-${ODOO_DB:-KARUSINDO_200826}}"
PG_ADMIN="${PG_ADMIN:-postgres}"
# Custom-format dumps of a real Odoo DB should be well over 1 MiB.
MIN_DUMP_BYTES="${MIN_DUMP_BYTES:-1048576}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
STEM="${DB_NAME}_${TIMESTAMP}"
DUMP_FILE="${BACKUP_DIR}/${STEM}.dump"
DUMP_TMP="${DUMP_FILE}.tmp"
FS_ZIP="${BACKUP_DIR}/${STEM}_filestore.zip"
FS_SRC="${FILESTORE_BASE}/${DB_NAME}"

file_size_bytes() {
  local path="$1"
  local size=""
  if [ ! -e "$path" ]; then
    echo 0
    return 0
  fi
  # macOS/BSD first, GNU as fallback.
  size="$(stat -f%z "$path" 2>/dev/null || true)"
  if [ -z "$size" ]; then
    size="$(stat -c%s "$path" 2>/dev/null || true)"
  fi
  case "$size" in
    ''|*[!0-9]*) echo 0 ;;
    *) echo "$size" ;;
  esac
}

echo "=== Odoo backup ==="
echo "Database : $DB_NAME"
echo "Dump     : $DUMP_FILE"
echo "Filestore: $FS_ZIP"
echo ""

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump not found."
  echo "Install Postgres.app or add its bin directory to PATH."
  echo "PATH=$PATH"
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql not found."
  exit 1
fi

mkdir -p "$BACKUP_DIR"

DB_OK="$(psql -X -U "$PG_ADMIN" -d postgres -Atq --set=db="$DB_NAME" <<'SQL'
SELECT 1 FROM pg_database WHERE datname = :'db';
SQL
)"
if [ "${DB_OK:-}" != "1" ]; then
  echo "ERROR: Database '$DB_NAME' does not exist (or Postgres is not reachable as role '$PG_ADMIN')."
  echo "Available databases:"
  PAGER= psql -X -U "$PG_ADMIN" -d postgres -P pager=off -c '\l' || true
  exit 1
fi

if [ ! -d "$FS_SRC" ]; then
  echo "ERROR: Filestore directory not found:"
  echo "  $FS_SRC"
  exit 1
fi

rm -f "$DUMP_TMP"
echo "Dumping database with pg_dump -Fc ..."
if ! pg_dump -U "$PG_ADMIN" -Fc --no-owner -f "$DUMP_TMP" "$DB_NAME"; then
  echo "ERROR: pg_dump failed. No dump file was written."
  rm -f "$DUMP_TMP"
  exit 1
fi

if [ ! -f "$DUMP_TMP" ]; then
  echo "ERROR: pg_dump exited 0 but did not create:"
  echo "  $DUMP_TMP"
  exit 1
fi

DUMP_SIZE="$(file_size_bytes "$DUMP_TMP")"
if [ "$DUMP_SIZE" -lt "$MIN_DUMP_BYTES" ]; then
  echo "ERROR: Dump is too small (${DUMP_SIZE} bytes). Minimum is ${MIN_DUMP_BYTES}."
  echo "The file was left at: $DUMP_TMP"
  exit 1
fi

mv "$DUMP_TMP" "$DUMP_FILE"
echo "Dump OK ($DUMP_SIZE bytes): $DUMP_FILE"

echo "Zipping filestore ..."
if [ "$(uname -s)" = Darwin ] && command -v ditto >/dev/null 2>&1; then
  if ! ditto -c -k --sequesterRsrc --keepParent "$FS_SRC" "$FS_ZIP"; then
    echo "ERROR: ditto failed while creating the filestore zip."
    rm -f "$DUMP_FILE" "$FS_ZIP"
    exit 1
  fi
else
  if ! command -v zip >/dev/null 2>&1; then
    echo "ERROR: zip not found."
    rm -f "$DUMP_FILE"
    exit 1
  fi
  if ! (cd "$FILESTORE_BASE" && zip -r -q "$FS_ZIP" "$DB_NAME"); then
    echo "ERROR: zip failed while creating the filestore archive."
    rm -f "$DUMP_FILE" "$FS_ZIP"
    exit 1
  fi
fi

if [ ! -f "$FS_ZIP" ]; then
  echo "ERROR: Filestore zip was not created: $FS_ZIP"
  exit 1
fi

ZIP_SIZE="$(file_size_bytes "$FS_ZIP")"
echo ""
echo "=== BACKUP DONE ==="
echo "Dump      : $DUMP_FILE  ($DUMP_SIZE bytes)"
echo "Filestore : $FS_ZIP  ($ZIP_SIZE bytes)"
echo "Database  : $DB_NAME"
