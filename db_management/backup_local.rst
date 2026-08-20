:banner: banners/db_premise.png

.. _db_backup_local:

======================================
Local dump backup (pg_dump + filestore)
======================================

A custom-format dump (``.dump``) and a filestore zip are two halves of the same
backup. The dump holds the records; the filestore zip holds uploaded files and
compiled assets.

This page explains a common failure of a wrapper script that writes the dump to a
``.tmp`` file and then renames it.

.. _backup-integer-expression:

``[: : integer expression expected`` and missing ``.dump.tmp``
==============================================================

A run that looks like this:

.. code-block:: text

   /Users/odoo-server/odoo-backup/run_backup.sh: line 76: [: : integer expression expected
   mv: rename /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump.tmp \
     to /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump: No such file or directory

is **not** two separate bugs. The dump file was never created. The size check and
``mv`` are follow-on errors from the same script continuing after ``pg_dump``
failed.

What each line means
--------------------

``line 76: [: : integer expression expected``
    Bash ``[`` was asked to compare a number, but the value was **empty**. Typical
    code around that line:

    .. code-block:: bash

       DUMP_SIZE=$(stat -c%s "$DUMP_TMP" 2>/dev/null)
       if [ "$DUMP_SIZE" -gt 0 ]; then
           mv "$DUMP_TMP" "$DUMP_FILE"
       fi

    When ``$DUMP_TMP`` does not exist (or when GNU ``stat -c%s`` is used on
    macOS), ``DUMP_SIZE`` is empty. ``[ "" -gt 0 ]`` prints *integer expression
    expected* and returns status **2**.

    An ``if`` treats that as false. The "dump looks good" branch is skipped,
    **and** the "dump failed, exit 1" branch is also skipped. The script keeps
    going.

``mv: ...dump.tmp ... No such file or directory``
    ``pg_dump -Fc -f file.dump.tmp`` never wrote that path. ``mv`` then tries to
    rename a file that is not there. On macOS, that message means the **source**
    ``.tmp`` is missing.

The real failure is therefore **before line 76**: ``pg_dump`` did not produce a
dump. Scroll up in the same terminal for the Postgres error. Common causes:

* ``pg_dump`` is not on ``PATH`` (Postgres.app's ``bin`` directory is missing).
* PostgreSQL is not running.
* The database name in the script does not exist (here:
  ``KARUSINDO_200826``).
* The role used to connect (often ``postgres`` or the macOS user) cannot connect.
* The backup directory is not writable, so ``-f`` cannot create the file.

Confirm on the Mac Mini
-----------------------

Print the size check and the ``mv`` around line 76:

.. code-block:: bash

   sed -n '60,90p' /Users/odoo-server/odoo-backup/run_backup.sh

Then check the tools and the database the dump name refers to:

.. code-block:: bash

   export PATH="/Applications/Postgres.app/Contents/Versions/15/bin:$PATH"
   command -v pg_dump
   pg_dump --version
   psql -U postgres -d postgres -c '\l'
   ls -lh /Users/odoo-server/Backup/KARUSINDO_200826_20260820_141727.dump*

If ``\l`` does not list ``KARUSINDO_200826``, the wrapper is pointing at the
wrong database. If ``pg_dump`` is missing, the dump step never runs.

Fix the wrapper
---------------

Do **not** treat an empty size as "not too small". Test that the file exists,
force a numeric size (default ``0``), and only then ``mv``:

.. code-block:: bash

   if [ ! -f "$DUMP_TMP" ]; then
     echo "ERROR: pg_dump did not create $DUMP_TMP"
     exit 1
   fi

   DUMP_SIZE=$(stat -f%z "$DUMP_TMP")   # macOS; GNU is stat -c%s
   : "${DUMP_SIZE:=0}"
   if [ "$DUMP_SIZE" -lt 1048576 ]; then
     echo "ERROR: dump too small ($DUMP_SIZE bytes)"
     exit 1
   fi

   mv "$DUMP_TMP" "$DUMP_FILE"

Use ``stat -f%z`` on macOS. ``stat -c%s`` is Linux and yields an empty size on
a Mac even when the dump **did** succeed.

A drop-in script that sets the Postgres.app ``PATH``, checks that the database
exists, refuses to ``mv`` a missing ``.tmp``, and also zips the filestore is
:file:`scripts/run_backup.sh` next to this page. Copy it over the wrapper:

.. code-block:: bash

   cp db_management/scripts/run_backup.sh /Users/odoo-server/odoo-backup/run_backup.sh
   chmod +x /Users/odoo-server/odoo-backup/run_backup.sh
   /Users/odoo-server/odoo-backup/run_backup.sh KARUSINDO_200826

Pass the production name (``KARUSINDO_110826``) when that is the database you
intend to archive. The dump file name is ``<database>_<timestamp>.dump``; the
timestamp in the error (``20260820_141727``) is when the failed run started, not
proof that a dump was written.

.. seealso::
   :ref:`On-premises database management <db_premise>`
