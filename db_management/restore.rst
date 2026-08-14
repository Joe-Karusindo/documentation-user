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
   Failed requests to :file:`/web/content/...css`, :file:`/web/content/...js`, or
   :file:`/web/image/website/1/logo/...` (404 or 500) confirm missing files.
#. Append ``?debug=assets`` to the URL (for example
   ``http://localhost:8069/web/login?debug=assets``). If the interface suddenly
   looks correct, the source addons are fine and only the **cached bundles** are
   broken.
#. Check the Odoo server log. A missing filestore file looks like this:

   .. code-block:: text

      FileNotFoundError: [Errno 2] No such file or directory:
      '.../filestore/<database_name>/f4/f4df3e6c...'
      GET /web/image/website/1/logo/My%20Website ... 500

   The hash after ``filestore/<database_name>/`` is the attachment's
   ``store_fname``. Odoo still has the ``ir.attachment`` row; the file on disk
   is gone. The *Powered by Odoo* footer image can still load, because that
   file comes from the addon source, not from the filestore.

   If the hashed file exists somewhere else on the machine (another
   ``data_dir``, an unzipped backup), copy that whole ``filestore`` directory
   into the path from the log:

   .. code-block:: bash

      find "$HOME" -name 'f4df3e6ca8f978a524d655084dfeede1578b845c' 2>/dev/null

.. tip::
   ``?debug=assets`` is a diagnostic. After the filestore or the bundles are
   repaired, open the site without that parameter so visitors get the normal
   minified assets.

.. _restore-filestore:

Restore the filestore
---------------------

The filestore directory name **must match the database name**. Typical locations:

* macOS source install: :file:`~/Library/Application Support/Odoo/filestore/<database_name>`
* Linux source install: :file:`~/.local/share/Odoo/filestore/<database_name>`
* Packaged Linux install: :file:`/var/lib/odoo/filestore/<database_name>`
* Custom path: the ``data_dir`` value in the Odoo configuration file, plus
  :file:`filestore/<database_name>`

The log line already prints the full path Odoo expects. If that folder exists but
the hashed file inside it does not, the restore was a dump **without** the
matching filestore (or the zip was extracted to a different ``data_dir``).

If the original filestore still exists (on the old server, in a zip, or next to a
manual dump):

#. Stop Odoo.
#. From a backup zip, the files sit under :file:`filestore/` next to
   :file:`dump.sql`. Copy them into the location above, using the **new**
   database name if you renamed the database during restore:

   .. code-block:: bash

      unzip backup.zip -d /tmp/odoo-restore
      cp -R /tmp/odoo-restore/filestore/* \
        "<filestore_path>/<database_name>/"

#. Give ownership to the user that runs Odoo (Linux packages):

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
**Regenerate Assets Bundles** from the debug menu. Delete the cached bundles,
then restart Odoo.

Do **not** paste SQL into the Odoo shell (the ``>>>`` prompt). SQL belongs in
``psql``. If you are already in the Odoo shell, use the Python block below.

In PostgreSQL:

.. code-block:: bash

   psql <database_name>

On Linux packages you may need ``sudo -u postgres psql <database_name>``.

.. code-block:: sql

   DELETE FROM ir_attachment
    WHERE res_model = 'ir.ui.view'
      AND name LIKE '%assets_%';

In an Odoo shell (``>>>``), paste this instead:

.. code-block:: python

   exec("""
   env['ir.attachment'].search([
       ('res_model', '=', 'ir.ui.view'),
       ('name', 'like', 'assets_'),
   ]).unlink()
   env.cr.commit()
   """)

Then ``exit()`` the shell, restart Odoo, and hard refresh the browser. The first
load is slower: Odoo compiles the bundles again and writes them to the
filestore.

Clear a broken website logo
---------------------------

A ``GET /web/image/website/1/logo/... 500`` with ``FileNotFoundError`` means the
**Website** logo attachment points at a missing file. That is the broken image
next to the website name on the login page. It is **not** the CSS; fix the
bundles as above for the unstyled layout.

If you cannot copy the original filestore, drop the broken pointer so Odoo
falls back to the default logo. You can re-upload the logo later under
:menuselection:`Website --> Configuration --> Settings`.

Match the hash from the log (the part after ``filestore/<database_name>/``):

.. code-block:: sql

   DELETE FROM ir_attachment
    WHERE store_fname = 'f4/f4df3e6ca8f978a524d655084dfeede1578b845c';

To drop every website logo pointer (when several companies or websites exist):

.. code-block:: sql

   DELETE FROM ir_attachment
    WHERE res_model = 'website'
      AND res_field = 'logo';

To list **all** attachments whose files are missing from disk, use an Odoo
shell. Unlink only the rows you intend to drop (assets regenerate; logos and
images do not).

.. code-block:: python

   import os
   from odoo.tools import config

   filestore = config.filestore(env.cr.dbname)
   missing = env['ir.attachment'].search([
       ('store_fname', '!=', False),
   ]).filtered(
       lambda rec: not os.path.isfile(
           os.path.join(filestore, rec.store_fname)
       )
   )
   for rec in missing:
       print(rec.id, rec.res_model, rec.res_field, rec.name, rec.store_fname)

.. warning::
   Do not ``DELETE FROM ir_attachment`` without a filter. That removes every
   attachment in the database, not only the cached CSS/JS bundles or one
   missing logo.

Other checks
------------

If the interface is still incomplete after the filestore and the asset bundles
are repaired:

* **Permissions** — the Odoo process must be able to read and write the
  filestore. A restore run as ``root`` often leaves files that the ``odoo``
  service user cannot open.
* **Missing compiler** — Odoo 11 and later compile SCSS with the Python
  ``libsass`` package. If it is missing, install it in the Odoo environment
  and restart:

  .. code-block:: bash

     pip3 install libsass

* **Missing addons** — every module that was installed on the source database
  must be on ``addons_path``. A missing website theme or custom module makes
  asset compilation fail; the server log then shows import or file errors.
* **Workers** — if ``workers`` is greater than ``0``, restart the whole
  service so every process drops the old in-memory cache.

.. _restore-backend-theme:

Backend theme and app icons
---------------------------

After the default backend loads, a third-party web theme can still look wrong:
identical generic app icons in the sidebar, stock grey/green colors, and no
theme logo or apps-menu background. That is common with a backend theme such as
**MuK Web Theme** (``muk_web_theme``).

The theme's JavaScript (the left apps bar) can load while **icons** and
**compiled theme SCSS** do not. Menu icons are stored as ``web_icon_data``
attachments in the filestore. Regenerating CSS does not rebuild those icons.

#. Confirm the **same major version** of the theme is on ``addons_path`` (MuK
   16.0 with Odoo 16, for example):

   .. code-block:: bash

      find "$HOME" -type d -name 'muk_web_theme' 2>/dev/null

   The folder must appear in the ``addons_path`` used to start Odoo. Restart
   after changing ``addons_path``.

#. Check that the module is installed:

   .. code-block:: sql

      SELECT name, state FROM ir_module_module
       WHERE name LIKE 'muk%';

   ``state`` must be ``installed``. If the row is missing or ``uninstalled``,
   add the addon path, update the apps list, and install the theme.

#. Upgrade the theme so its SCSS is compiled into ``web.assets_backend``.
   Use the same ``-c`` configuration file as the running server:

   .. code-block:: bash

      ./odoo-bin -d <database_name> -u muk_web_theme --stop-after-init

#. Rebuild menu icons from each module's :file:`static/description/icon.png`
   (this does not need the original filestore). In an Odoo shell, paste **one**
   block. The interactive ``>>>`` prompt needs a blank line to end a ``for``
   loop before ``env.cr.commit()``; wrapping the script avoids that:

   .. code-block:: python

      exec("""
      menus = env['ir.ui.menu'].search([('web_icon', '!=', False)])
      for menu in menus:
          data = menu._compute_web_icon_data(menu.web_icon)
          if data:
              menu.write({'web_icon_data': data})
      env.cr.commit()
      print('updated', len(menus), 'menus')
      """)

#. Still in the Odoo shell (``>>>``), delete the cached asset bundles. Do not
   paste SQL here:

   .. code-block:: python

      exec("""
      env['ir.attachment'].search([
          ('res_model', '=', 'ir.ui.view'),
          ('name', 'like', 'assets_'),
      ]).unlink()
      env.cr.commit()
      print('asset bundles deleted')
      """)

   Then ``exit()``, restart Odoo, and hard refresh the browser.

Company-specific theme images (backend logo, apps-menu background) live in the
filestore. If those files are gone, the theme falls back to defaults until you
copy the filestore or re-upload the images in the theme settings.

.. warning::
   If you regenerated assets **before** the theme folder was on
   ``addons_path``, the bundles were compiled without the theme. Upgrade the
   module and regenerate assets again after the path is correct.

   A log line such as ``Could not get content for /muk_web_theme/static/...``
   means Odoo still cannot read the theme files.

Prevent the issue
=================

* Download **zip (includes filestore)** from the database manager, not a raw SQL
  dump, unless you also archive :file:`filestore/<database_name>` yourself.
* Restore with the **same major version** and the **same extra modules**,
  including any backend theme, **before** the first asset regeneration.
* After a restore, open :file:`/web/login` once and confirm that the layout, the
  website logo, and the backend theme load before you point users at the copy.
