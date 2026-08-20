#!/bin/bash
set -u
set -o pipefail

export PATH="/Applications/Postgres.app/Contents/Versions/15/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Force PostgreSQL connection via TCP, NOT Unix socket.
# This avoids Postgres.app trust permission dialog issue when running from cron.
export PGHOST="127.0.0.1"
export PGPORT="5432"
export PGUSER="odoo-server"

DATE=$(date +"%Y%m%d_%H%M%S")

DB_NAME="KARUSINDO_200826"

BACKUP_DIR="/Users/odoo-server/Backup"

FILESTORE_BASE="/Users/odoo-server/Library/Application Support/Odoo/filestore"
FILESTORE="$FILESTORE_BASE/$DB_NAME"

EXT_DRIVE="/Volumes/Samsung SSD 870 QVO 2TB"
EXT_BACKUP_DIR="$EXT_DRIVE/Odoo/Backup_HD"

LOG="/Users/odoo-server/odoo-backup/odoo_backup.log"
ERR="/Users/odoo-server/odoo-backup/odoo_backup_error.log"

DB_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.dump"
DB_TMP="$BACKUP_DIR/${DB_NAME}_${DATE}.dump.tmp"

FS_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}_filestore.zip"
FS_TMP="$BACKUP_DIR/${DB_NAME}_${DATE}_filestore.zip.tmp"

LOCKDIR="/tmp/odoo_backup.lockdir"

MIN_DUMP_BYTES=1000000
MIN_ZIP_BYTES=1000000

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG")"
touch "$LOG" "$ERR"

log() {
  echo "$*" | tee -a "$LOG"
}

err() {
  echo "$*" | tee -a "$ERR" >&2
}

# Never print empty: empty breaks `[ "$size" -lt N ]` with
# "integer expression expected", and that failed test is treated as false
# so the script keeps going and hits `mv` on a missing file.
file_bytes() {
  local path="$1"
  local size=""
  if [ ! -f "$path" ]; then
    echo 0
    return 0
  fi
  # Homebrew coreutils `stat` (GNU) does not speak BSD `-f%z`.
  if [ -x /usr/bin/stat ]; then
    size="$(/usr/bin/stat -f%z "$path" 2>/dev/null || true)"
  else
    size="$(stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null || true)"
  fi
  case "$size" in
    ''|*[!0-9]*) echo 0 ;;
    *) echo "$size" ;;
  esac
}

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  err "ERROR: Backup already running. Lock exists: $LOCKDIR"
  exit 1
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

log "===== $(date '+%Y-%m-%d %H:%M:%S') START PG_DUMP + FILESTORE BACKUP ====="
log "Database: $DB_NAME"
log "Dump:     $DB_FILE"

PG_DUMP_BIN="$(command -v pg_dump || true)"
if [ -x "/Applications/Postgres.app/Contents/Versions/15/bin/pg_dump" ]; then
  PG_DUMP_BIN="/Applications/Postgres.app/Contents/Versions/15/bin/pg_dump"
fi
if [ -z "$PG_DUMP_BIN" ]; then
  err "ERROR: pg_dump not found. PATH=$PATH"
  exit 1
fi
log "Using pg_dump: $PG_DUMP_BIN ($("$PG_DUMP_BIN" --version 2>/dev/null | head -n 1))"

log "Checking PostgreSQL via TCP $PGHOST:$PGPORT..."
if ! pg_isready -h "$PGHOST" -p "$PGPORT" 2>&1 | tee -a "$LOG"; then
  err "ERROR: PostgreSQL not ready via $PGHOST:$PGPORT"
  exit 1
fi

log "Checking database $DB_NAME as role $PGUSER..."
if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$DB_NAME" -Atqc 'SELECT 1' >/dev/null; then
  err "ERROR: Cannot connect to database '$DB_NAME' as '$PGUSER' via $PGHOST:$PGPORT."
  err "Available databases:"
  PAGER= psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -P pager=off -c '\l' 2>&1 | tee -a "$ERR" >&2 || true
  exit 1
fi

log "Checking filestore..."
if [ ! -d "$FILESTORE" ]; then
  err "ERROR: Filestore not found: $FILESTORE"
  exit 1
fi

log "Dumping database via TCP..."
rm -f "$DB_TMP" "$DB_FILE"

# Put -f before the database name. Do not redirect pg_dump stdout into the log:
# custom-format output must go to $DB_TMP via -f, not to odoo_backup.log.
"$PG_DUMP_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
  -Fc -f "$DB_TMP" "$DB_NAME" 2>&1 | tee -a "$LOG"
DUMP_RC="${PIPESTATUS[0]}"

if [ "$DUMP_RC" -ne 0 ]; then
  err "ERROR: pg_dump failed (exit $DUMP_RC)."
  rm -f "$DB_TMP"
  exit 1
fi

if [ ! -f "$DB_TMP" ]; then
  err "ERROR: pg_dump did not create $DB_TMP"
  err "If $LOG suddenly grew by hundreds of MB, the dump was written to the log instead of -f."
  exit 1
fi

DB_SIZE="$(file_bytes "$DB_TMP")"
if [ "$DB_SIZE" -lt "$MIN_DUMP_BYTES" ]; then
  err "ERROR: pg_dump file too small: $DB_SIZE bytes (minimum $MIN_DUMP_BYTES)"
  rm -f "$DB_TMP"
  exit 1
fi

mv "$DB_TMP" "$DB_FILE"
log "Database dump created: $DB_FILE ($DB_SIZE bytes)"

log "Zipping filestore..."
rm -f "$FS_TMP" "$FS_FILE"

if ! (
  cd "$FILESTORE_BASE" || exit 1
  zip -rq "$FS_TMP" "$DB_NAME"
); then
  err "ERROR: filestore zip failed"
  rm -f "$FS_TMP"
  exit 1
fi

if [ ! -f "$FS_TMP" ]; then
  err "ERROR: filestore zip did not create $FS_TMP"
  exit 1
fi

FS_SIZE="$(file_bytes "$FS_TMP")"
if [ "$FS_SIZE" -lt "$MIN_ZIP_BYTES" ]; then
  err "ERROR: filestore zip too small: $FS_SIZE bytes (minimum $MIN_ZIP_BYTES)"
  rm -f "$FS_TMP"
  exit 1
fi

mv "$FS_TMP" "$FS_FILE"
log "Filestore backup created: $FS_FILE ($FS_SIZE bytes)"

log "Checking Samsung SSD..."
if [ ! -d "$EXT_DRIVE" ]; then
  err "ERROR: Samsung SSD not mounted: $EXT_DRIVE"
  err "Local backup is complete: $DB_FILE and $FS_FILE"
  exit 1
fi

if [ ! -d "$EXT_BACKUP_DIR" ]; then
  log "Creating external backup folder: $EXT_BACKUP_DIR"
  if ! mkdir -p "$EXT_BACKUP_DIR"; then
    err "ERROR: Cannot create $EXT_BACKUP_DIR"
    err "Local backup is complete: $DB_FILE and $FS_FILE"
    exit 1
  fi
fi

log "Copying DB dump to Samsung SSD..."
if ! /usr/bin/rsync -avh --progress "$DB_FILE" "$EXT_BACKUP_DIR/" 2>&1 | tee -a "$LOG"; then
  err "ERROR: Failed copying DB dump to Samsung SSD"
  err "Local backup is complete: $DB_FILE"
  exit 1
fi

log "Copying filestore zip to Samsung SSD..."
if ! /usr/bin/rsync -avh --progress "$FS_FILE" "$EXT_BACKUP_DIR/" 2>&1 | tee -a "$LOG"; then
  err "ERROR: Failed copying filestore zip to Samsung SSD"
  err "Local backup is complete: $DB_FILE and $FS_FILE"
  exit 1
fi

log "Samsung SSD copy completed."

log "Cleaning local backups older than 7 days..."
find "$BACKUP_DIR" -type f \( \
  -name "${DB_NAME}_*.dump" -o \
  -name "${DB_NAME}_*.dump.tmp" -o \
  -name "${DB_NAME}_*_filestore.zip" -o \
  -name "${DB_NAME}_*_filestore.zip.tmp" \
\) -mtime +7 -print -delete 2>&1 | tee -a "$LOG"

log "Cleaning Samsung SSD backups older than 14 days..."
find "$EXT_BACKUP_DIR" -type f \( \
  -name "${DB_NAME}_*.dump" -o \
  -name "${DB_NAME}_*_filestore.zip" \
\) -mtime +14 -print -delete 2>&1 | tee -a "$LOG"

log "===== $(date '+%Y-%m-%d %H:%M:%S') BACKUP SUCCESS ====="
echo "" >> "$LOG"
