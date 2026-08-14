:banner: banners/db_premise.png

.. _db_restore:

==================
Restore a database
==================

Restoring an on-premise Odoo backup requires **both** the PostgreSQL dump and the
**filestore**. The dump holds the records; the filestore holds uploaded files and the
compiled CSS/JavaScript bundles that style the interface.

If only the database is restored, Odoo still serves the HTML of :file:`/web/login`,
but the page looks like a plain, unstyled form: black text on a white background,
broken website logo, and a working *Powered by Odoo* footer image (that last file
comes from the source addons, not from the filestore).

.. note::
   Always test a restore on a copy. Do not overwrite a production database until the
   copy loads with a complete interface.

Download a backup
=================

Open the database manager at :file:`/web/database/manager` and download a backup.

Choose **zip (includes filestore)** as the format. A dump without the filestore
(``.sql``, ``dump.sql``, or *zip without filestore*) is not enough to rebuild the
interface or to keep attachments (product images, invoice PDFs, website media).

You need the server master password. If the manager is disabled, ask the
administrator who deployed Odoo, or restore with the same tools used for the usual
server backups.

.. seealso::
   - :ref:`On-premises database management <db_premise>`
   - :doc:`Import a backup into Odoo.sh <../odoo_sh/getting_started/create>`

Restore a backup
================

#. Install the **same Odoo version** as the source database (for example, 14.0 with
   14.0). A dump from another major version cannot be restored this way; it must be
   :ref:`upgraded <upgrade_button>` first.
#. Install the **same extra addons** (Website themes, custom modules, OCA modules)
   and point ``addons_path`` at them.
#. Open :file:`/web/database/manager` and click **Restore Database**.
#. Upload the zip, set a database name, and confirm.

If the backup is a PostgreSQL dump only, restore it with ``pg_restore`` or ``psql``,
then copy the filestore directory next to it (see :ref:`restore-filestore` below).

After a restore on a new host, set **web.base.url** to the URL you actually use
(for example ``http://localhost:8069``). With :doc:`Developer mode
<../general/developer_mode/activate>` enabled, go to :menuselection:`Settings -->
Technical --> Parameters --> System Parameters` and edit the parameter. For a
website, also check the website domain in :menuselection:`Website --> Configuration
--> Settings`.

Incomplete interface after restore
==================================

The login page, backend, or website renders as unstyled HTML. Menus, the database
selector, and the *Log in* button are still there, but layout, colors, and many
images are missing.

That happens when Odoo still has ``ir.attachment`` rows for compiled asset bundles
(``web.assets_common``, ``web.assets_frontend``, ``web.assets_backend``, …) while
the files those rows point to are absent from the filestore.

Confirm the symptom
-------------------

#. Open the login page, then open the browser developer tools (``F12``) and reload.
   Failed requests to :file:`/web/content/...css` or :file:`/web/content/...js`
   (404 or 500) confirm missing or unreadable asset files.
#. Append ``?debug=assets`` to the URL (for example
   ``http://localhost:8069/web/login?debug=assets``). If the interface suddenly
   looks correct, the source addons are fine and only the **cached bundles** are
   broken.
#. Check the Odoo server log for ``FileNotFoundError`` under ``filestore``.

.. tip::
   ``?debug=assets`` is a diagnostic. After the filestore or the bundles are
   repaired, open the site without that parameter so visitors get the normal
   minified assets.

.. _restore-filestore:

Restore the filestore
---------------------

The filestore directory name **must match the database name**. Typical locations:

* Packaged Linux install: :file:`/var/lib/odoo/filestore/<database_name>`
* Source install: :file:`~/.local/share/Odoo/filestore/<database_name>`
* Custom path: the ``data_dir`` value in the Odoo configuration file, plus
  :file:`filestore/<database_name>`

If the original filestore still exists (on the old server, in a zip, or next to a
manual dump):

#. Stop Odoo.
#. Copy the directory into the location above, using the **new** database name if
   you renamed the database during restore.
#. Give ownership to the user that runs Odoo, for example:

   .. code-block:: bash

      sudo chown -R odoo:odoo /var/lib/odoo/filestore/<database_name>

#. Start Odoo and do a hard refresh in the browser (``Ctrl+Shift+R``).

Regenerating assets restores **layout**. It does **not** restore uploaded files:
the website logo, product images, chatter attachments, or signed documents. Those
only come back with the original filestore.

Regenerate CSS and JavaScript assets
------------------------------------

Use this when the filestore is missing and you cannot copy it, or when the
filestore is present but the cached bundles still point at old checksums.

The login form still submits, but the backend JavaScript may be too broken to use
**Regenerate Assets Bundles** from the debug menu. Delete the bundle attachments
from PostgreSQL instead:

.. code-block:: bash

   sudo -u postgres psql <database_name>

.. code-block:: sql

   DELETE FROM ir_attachment
    WHERE res_model = 'ir.ui.view'
      AND name LIKE '%assets_%';

Restart the Odoo service, then reload :file:`/web/login` without using the
browser cache. The first load is slower: Odoo compiles the bundles again and
writes them to the filestore.

From an Odoo shell the same cleanup is:

.. code-block:: bash

   ./odoo-bin shell -c /etc/odoo/odoo.conf -d <database_name>

.. code-block:: python

   env['ir.attachment'].search([
       ('res_model', '=', 'ir.ui.view'),
       ('name', 'like', 'assets_'),
   ]).unlink()
   env.cr.commit()

.. warning::
   Do not ``DELETE FROM ir_attachment`` without a filter. That removes every
   attachment in the database, not only the cached CSS/JS bundles.

Other checks
------------

If the interface is still incomplete after the filestore and the asset bundles
are repaired:

* **Permissions** — the Odoo process must be able to read and write the
  filestore. A restore run as ``root`` often leaves files that the ``odoo``
  service user cannot open.
* **Missing compiler** — Odoo 14 compiles SCSS with the Python ``libsass``
  package. If it is missing, install it in the Odoo environment and restart:

  .. code-block:: bash

     pip3 install libsass

* **Missing addons** — every module that was installed on the source database
  must be on ``addons_path``. A missing website theme or custom module makes
  asset compilation fail; the server log then shows import or file errors.
* **Workers** — if ``workers`` is greater than ``0``, restart the whole
  service so every process drops the old in-memory cache.

Prevent the issue
=================

* Download **zip (includes filestore)** from the database manager, not a raw SQL
  dump, unless you also archive :file:`filestore/<database_name>` yourself.
* Restore with the **same major version** and the **same extra modules**.
* After a restore, open :file:`/web/login` once and confirm that the layout, the
  website logo, and the backend theme load before you point users at the copy.
