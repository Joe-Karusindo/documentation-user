:banner: banners/db_premise.png

.. _db_backup_local:

======================================
Local dump backup (pg_dump + filestore)
======================================

A custom-format dump (``.dump``) and a filestore zip are two halves of the same
backup. The dump holds the records; the filestore zip holds uploaded files and
compiled assets.

The Mac Mini wrapper ``/Users/odoo-server/odoo-backup/run_backup.sh`` archives
**KARUSINDO_200826** (that name is correct for this backup). It writes a
``.dump.tmp``, checks the size, then ``mv`` to ``.dump``.

.. _backup-integer-expression:

``[: : integer expression expected`` and missing ``.dump.tmp``
==============================================================

A run that looks like this:

.. code-block:: text

   /Users/odoo-server/odoo-backup/run_backup.sh: line 76: [: : integer expression expected
   mv: rename /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump.tmp \
     to /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump: No such file or directory

is **not** two separate bugs, and it is **not** the wrong database name. Line 76
of the wrapper is:

.. code-block:: bash

   DB_SIZE=$(stat -f%z "$DB_TMP" 2>> "$ERR")

   if [ "$DB_SIZE" -lt 1000000 ]; then
     echo "ERROR: pg_dump file too small: $DB_SIZE bytes" >> "$ERR"
     rm -f "$DB_TMP"
     exit 1
   fi

   mv "$DB_TMP" "$DB_FILE"

``pg_dump`` never created ``KARUSINDO_200826_…dump.tmp``. ``stat`` printed
nothing, so ``DB_SIZE`` was empty. ``[ "" -lt 1000000 ]`` prints *integer
expression expected* and returns status **2**.

An ``if`` treats that as false, so the script **does not** take the "too small,
exit 1" branch. It falls through to ``mv`` of a file that is not there.

``pg_dump`` stderr was appended only to ``odoo_backup_error.log``, which is why
the terminal showed only these two bash lines. Read that log (and
``odoo_backup.log``) for the Postgres message.

What to check
-------------

.. code-block:: bash

   tail -n 50 /Users/odoo-server/odoo-backup/odoo_backup_error.log
   tail -n 50 /Users/odoo-server/odoo-backup/odoo_backup.log
   ls -lh /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump*
   export PATH="/Applications/Postgres.app/Contents/Versions/15/bin:$PATH"
   pg_isready -h 127.0.0.1 -p 5432
   psql -h 127.0.0.1 -p 5432 -U odoo-server -d KARUSINDO_200826 -c 'SELECT 1'

Typical causes of a missing ``.tmp`` with this wrapper:

* ``pg_dump`` could not connect as ``odoo-server`` on TCP ``127.0.0.1:5432``
  (password / ``pg_hba.conf``). The original script still treated a later empty
  size as "not too small".
* stdout of ``pg_dump`` was redirected into ``odoo_backup.log`` (``>> "$LOG"``).
  If ``-f`` did not take effect, the dump lands in the **log** (the log file
  jumps by hundreds of MB) and no ``.dump.tmp`` is created, while ``pg_dump``
  still exits 0.
* Homebrew GNU ``stat`` is ahead of ``/usr/bin/stat`` on ``PATH``. GNU
  ``stat -f%z`` does not print a byte size, so ``DB_SIZE`` is empty even when
  the dump exists. Use ``/usr/bin/stat -f%z``.

Fix
---

* Require the ``.tmp`` file to exist before comparing size.
* Default a missing size to ``0`` so ``[`` never sees an empty string.
* Put ``-f "$DB_TMP"`` **before** the database name; do not redirect dump
  stdout into the log.
* Print ``pg_dump`` / ``psql`` errors on the terminal as well as the log.

:file:`scripts/run_backup.sh` next to this page is a drop-in replacement that
keeps TCP, the lock, the Samsung SSD copy, and 7/14-day cleanup, still for
**KARUSINDO_200826**:

.. code-block:: bash

   cp db_management/scripts/run_backup.sh /Users/odoo-server/odoo-backup/run_backup.sh
   chmod +x /Users/odoo-server/odoo-backup/run_backup.sh
   /Users/odoo-server/odoo-backup/run_backup.sh

.. seealso::
   :ref:`On-premises database management <db_premise>`
