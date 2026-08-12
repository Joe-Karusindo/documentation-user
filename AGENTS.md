# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This repository is primarily the **Odoo 14.0 end-user documentation** — a static
[Sphinx](https://www.sphinx-doc.org/) site written in reStructuredText (`.rst`), with a heavily
customized theme/extensions under `_extensions/`. Building the docs (`make html`) is the main
"application" here; there is no runtime server, database, lint config, or automated test suite.

A second, unrelated deliverable, the `container_deposit_management/` Odoo 16 addon, also lives in
this repo. It is **out of scope** for local dev here: it only runs inside a full Odoo 16 + PostgreSQL
stack and depends on six custom modules (`custom_import`, `ab_foreign_trade`, `custom_reports`,
`ab_accounting`, `sequence_reset_period`, `od_journal_sequence`) that are **not present** in this
repo, so it cannot be installed/tested from here alone.

### Environment gotchas (non-obvious)
- **Python 3.8 is required for the docs build, NOT the system Python 3.12.** The old `conf.py`
  calls `app.add_stylesheet` / `app.add_javascript` / `html_add_permalinks`, which were removed in
  Sphinx 4.0/5.0, so Sphinx must stay on the 3.x line. But Sphinx 3.x fails to import on Python
  3.10+ (`from types import Union`). The working combination is **Python 3.8 + Sphinx 3.5.4**. A
  Python 3.8 venv lives at `.venv` (gitignored) and is (re)created by the startup update script via
  [uv](https://docs.astral.sh/uv/).
- Do **not** run `pip install -r requirements.txt` — it only pins `Sphinx>=2.4.0` and would pull an
  incompatible modern Sphinx. Use the pinned versions from the update script instead.
- `uv` (`~/.local/bin`) and the LESS compiler `lessc` (`~/.npm-global/bin`, installed globally via
  npm) are provisioned in the VM image. `~/.bashrc` adds both to `PATH`; a fresh non-login shell may
  need `source ~/.bashrc` (or use the explicit paths).
- `make html` has an implicit `lessc` dependency: it rebuilds `_extensions/odoo/static/style.css`
  from `.less` sources. The compiled `style.css` is already committed, so `make html` normally skips
  the LESS step unless a `.less` file changes.

### Build / run the docs
Activate the venv (so `sphinx-build` is on `PATH`) then build, from the repo root:

```bash
source .venv/bin/activate      # or: export PATH="/workspace/.venv/bin:$PATH"
make html                      # outputs to _build/html/
```

The build emits ~35 non-fatal warnings (legacy content); a successful run ends with
`build succeeded` / `The HTML pages are in _build/html.`

To view/serve the rendered site locally:

```bash
python3 -m http.server 8000 --directory _build/html
# open http://localhost:8000/index.html
```

### "Lint" / "test"
There is no linter and no automated test suite. The effective check is a clean `make html` build.
`make linkcheck` exists but hits the network (slow/flaky) and is not part of normal dev.
