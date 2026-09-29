#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanitize DB hasil restore KJ menjadi database KMS (Odoo 16 Community).

Jalankan HANYA pada database COPY (bukan KJ produksi), misalnya:

    odoo-bin shell -d kms -c /etc/odoo/odoo.conf

lalu:

    exec(open('/path/to/kms_from_kj/sanitize_kms.py', encoding='utf-8').read())

Atau non-interaktif:

    odoo-bin shell -d kms -c /etc/odoo/odoo.conf < sanitize_kms.py

Environment opsional:
    KMS_COMPANY_JSON=/path/to/company_kms.json
    KMS_DRY_RUN=1          # hanya laporan, tidak commit
    KMS_SKIP_COMPANY=1     # jangan ubah res.company
"""

from __future__ import print_function

import json
import os
import uuid

# Odoo shell menyediakan: env, self (kadang)
assert "env" in dir(), "Jalankan skrip ini di dalam `odoo-bin shell`."

DRY_RUN = os.environ.get("KMS_DRY_RUN", "").strip() in ("1", "true", "True", "yes")
SKIP_COMPANY = os.environ.get("KMS_SKIP_COMPANY", "").strip() in ("1", "true", "True", "yes")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DEFAULT_JSON = os.path.join(SCRIPT_DIR, "company_kms.json")
COMPANY_JSON = os.environ.get("KMS_COMPANY_JSON", DEFAULT_JSON)


def log(msg):
    print("[KMS] %s" % msg)


def model_exists(name):
    return name in env


def safe_search(model_name, domain=None):
    if not model_exists(model_name):
        return env["res.partner"].browse()  # empty-like; callers check model_exists
    return env[model_name].sudo().with_context(active_test=False).search(domain or [])


def count(model_name, domain=None):
    if not model_exists(model_name):
        return 0
    return env[model_name].sudo().with_context(active_test=False).search_count(domain or [])


def unlink_all(model_name, domain=None, chunk=200):
    """Hapus record dengan chunk agar tidak OOM; lewati jika model tidak ada."""
    if not model_exists(model_name):
        log("SKIP (model tidak terpasang): %s" % model_name)
        return 0
    Model = env[model_name].sudo().with_context(
        active_test=False,
        tracking_disable=True,
        mail_notrack=True,
        mail_create_nolog=True,
        prefetch_fields=False,
    )
    total = 0
    while True:
        recs = Model.search(domain or [], limit=chunk)
        if not recs:
            break
        n = len(recs)
        if DRY_RUN:
            log("DRY-RUN would unlink %s x %s" % (n, model_name))
            total += n
            break
        try:
            recs.unlink()
        except Exception as e:
            # Fallback: hapus satu per satu bila constraint memblok batch
            log("WARN batch unlink %s gagal (%s); coba per-record" % (model_name, e))
            for rec in recs:
                try:
                    rec.unlink()
                    total += 1
                except Exception as e2:
                    log("ERROR unlink %s id=%s: %s" % (model_name, rec.id, e2))
            env.cr.commit()
            continue
        total += n
        env.cr.commit()
        log("unlinked %s from %s (running total %s)" % (n, model_name, total))
    if total:
        log("DONE %s: removed ~%s" % (model_name, total))
    else:
        log("OK %s: already empty or dry-run sampled" % model_name)
    return total


def load_company_config():
    path = COMPANY_JSON
    if not os.path.isfile(path):
        log("WARN: company JSON tidak ditemukan: %s — skip update company detail" % path)
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return data


def update_company(cfg):
    if SKIP_COMPANY or not cfg:
        log("SKIP company update")
        return
    company = env.company.sudo()
    partner = company.partner_id.sudo()
    Country = env["res.country"].sudo()
    State = env["res.country.state"].sudo()
    Currency = env["res.currency"].sudo()

    vals_company = {"name": cfg.get("name") or company.name}
    vals_partner = {"name": vals_company["name"]}

    for field in ("street", "street2", "city", "zip", "phone", "mobile", "email", "website", "vat"):
        if cfg.get(field) not in (None, ""):
            vals_partner[field] = cfg[field]
            if field in company._fields:
                vals_company[field] = cfg[field]

    if cfg.get("company_registry") and "company_registry" in company._fields:
        vals_company["company_registry"] = cfg["company_registry"]

    if cfg.get("country_code"):
        country = Country.search([("code", "=", cfg["country_code"])], limit=1)
        if country:
            vals_partner["country_id"] = country.id
            vals_company["country_id"] = country.id
            if cfg.get("state_code"):
                state = State.search(
                    [("code", "=", cfg["state_code"]), ("country_id", "=", country.id)],
                    limit=1,
                )
                if state:
                    vals_partner["state_id"] = state.id
                    if "state_id" in company._fields:
                        vals_company["state_id"] = state.id

    if cfg.get("currency_code") and "currency_id" in company._fields:
        currency = Currency.search([("name", "=", cfg["currency_code"])], limit=1)
        if currency:
            vals_company["currency_id"] = currency.id

    log("Update company %s -> %s" % (company.name, vals_company.get("name")))
    if not DRY_RUN:
        partner.write(vals_partner)
        company.write(vals_company)

        # Bank accounts perusahaan (opsional)
        banks = cfg.get("bank_accounts") or []
        PartnerBank = env["res.partner.bank"].sudo() if model_exists("res.partner.bank") else None
        ResBank = env["res.bank"].sudo() if model_exists("res.bank") else None
        if PartnerBank is not None:
            # Hapus rekening lama milik company partner (hasil copy KJ)
            old = PartnerBank.search([("partner_id", "=", partner.id)])
            if old:
                old.unlink()
            for b in banks:
                acc = (b.get("acc_number") or "").strip()
                if not acc:
                    continue
                bank_id = False
                bank_name = (b.get("bank_name") or "").strip()
                if bank_name and ResBank is not None:
                    bank = ResBank.search([("name", "=", bank_name)], limit=1)
                    if not bank:
                        bank = ResBank.create({"name": bank_name})
                    bank_id = bank.id
                PartnerBank.create(
                    {
                        "partner_id": partner.id,
                        "acc_number": acc,
                        "bank_id": bank_id,
                        "acc_holder_name": b.get("acc_holder_name") or vals_company["name"],
                        "company_id": company.id if "company_id" in PartnerBank._fields else False,
                    }
                )
        env.cr.commit()
    log("Company update done")


def reset_sequences(prefix_hint="KMS"):
    """Reset nomor sequence agar dokumen KMS mulai dari awal.
    Tidak mengubah kode sequence secara agresif; hanya number_next / number_next_actual.
    """
    if not model_exists("ir.sequence"):
        return
    Seq = env["ir.sequence"].sudo().with_context(active_test=False)
    seqs = Seq.search([])
    log("Reset %s sequences (number_next -> 1)" % len(seqs))
    if DRY_RUN:
        return
    for seq in seqs:
        vals = {}
        if "number_next" in seq._fields:
            vals["number_next"] = 1
        if "number_next_actual" in seq._fields:
            # computed di beberapa versi; set number_next saja biasanya cukup
            pass
        if vals:
            try:
                seq.write(vals)
            except Exception as e:
                log("WARN sequence id=%s code=%s: %s" % (seq.id, seq.code, e))
    # Date-range sequences (Odoo)
    if model_exists("ir.sequence.date_range"):
        ranges = env["ir.sequence.date_range"].sudo().search([])
        for r in ranges:
            try:
                r.write({"number_next": 1})
            except Exception as e:
                log("WARN sequence date_range id=%s: %s" % (r.id, e))
    env.cr.commit()
    log("Sequences reset. Prefix hint (manual review): %s" % prefix_hint)


def refresh_database_uuid():
    Param = env["ir.config_parameter"].sudo()
    old = Param.get_param("database.uuid")
    new = str(uuid.uuid4())
    log("database.uuid %s -> %s" % (old, new))
    if not DRY_RUN:
        Param.set_param("database.uuid", new)
        # Optional: clear enterprise/subscription leftovers if any
        for key in ("database.secret", "database.create_date"):
            # keep create_date; rotate secret for safety on cloned DB
            pass
        Param.set_param("database.secret", str(uuid.uuid4()))
        env.cr.commit()


def clear_transactional_data():
    """Urutan penting: anak transaksi dulu, lalu dokumen, lalu accounting & stock valuation."""
    log("=== Clearing transactional data ===")

    # --- Payments & reconcile ---
    unlink_all("account.partial.reconcile")
    unlink_all("account.payment")
    # Full reconcile (jika ada)
    unlink_all("account.full.reconcile")

    # --- Bank statements ---
    unlink_all("account.bank.statement.line")
    unlink_all("account.bank.statement")

    # --- Account moves (invoices, bills, entries, opening balances) ---
    # Draft dulu, lalu posted: unlink posted di Odoo 16 biasanya butuh cancel/button_draft
    if model_exists("account.move"):
        Move = env["account.move"].sudo().with_context(
            tracking_disable=True,
            mail_notrack=True,
            force_delete=True,
        )
        posted = Move.search([("state", "=", "posted")])
        log("Resetting %s posted account.move -> draft/cancel" % len(posted))
        if not DRY_RUN:
            for move in posted:
                try:
                    if hasattr(move, "button_draft"):
                        move.button_draft()
                    elif hasattr(move, "button_cancel"):
                        move.button_cancel()
                except Exception as e:
                    log("WARN button_draft move %s: %s" % (move.id, e))
            env.cr.commit()
        unlink_all("account.move")

    # --- Analytic ---
    unlink_all("account.analytic.line")

    # --- Sales / Purchase ---
    unlink_all("sale.order.line")
    unlink_all("sale.order")
    unlink_all("purchase.order.line")
    unlink_all("purchase.order")

    # --- CRM opsional ---
    unlink_all("crm.lead")

    # --- Inventory transactions ---
    unlink_all("stock.valuation.layer")
    unlink_all("stock.move.line")
    unlink_all("stock.move")
    unlink_all("stock.picking")
    unlink_all("stock.scrap")
    unlink_all("stock.landed.cost")  # jika ada
    unlink_all("stock.quant")  # on-hand qty → 0
    # Lot/serial: biasanya master; biarkan. Hapus jika ingin bersih total:
    # unlink_all("stock.lot")

    # --- MRP ---
    unlink_all("mrp.unbuild")
    unlink_all("mrp.production")

    # --- POS ---
    unlink_all("pos.payment")
    unlink_all("pos.order.line")
    unlink_all("pos.order")
    unlink_all("pos.session")

    # --- Expenses / sheets ---
    unlink_all("hr.expense.sheet")
    unlink_all("hr.expense")

    # --- Approvals / documents transaksi umum lain ---
    unlink_all("account.asset")  # hati-hati: jika asset master ingin dipertahankan, comment baris ini
    unlink_all("account.asset.line")

    log("=== Transactional clear finished ===")


def report_masters():
    log("=== Master data counts (should remain) ===")
    for name in (
        "account.account",
        "account.tax",
        "account.fiscal.position",
        "account.journal",
        "res.partner",
        "product.template",
        "product.product",
        "stock.warehouse",
        "stock.location",
        "product.category",
    ):
        log("  %s: %s" % (name, count(name)))
    log("=== Transaction counts (should be 0) ===")
    for name in (
        "account.move",
        "account.payment",
        "sale.order",
        "purchase.order",
        "stock.picking",
        "stock.move",
        "stock.quant",
        "stock.valuation.layer",
    ):
        log("  %s: %s" % (name, count(name)))


def main():
    db_name = env.cr.dbname
    log("Database: %s | company: %s | DRY_RUN=%s" % (db_name, env.company.name, DRY_RUN))
    if db_name.lower() in ("kj", "karunia", "karunia_jasindo", "production", "prod"):
        raise SystemExit(
            "REFUSE: nama DB '%s' terlihat seperti produksi KJ. "
            "Rename/restore ke DB khusus KMS dulu." % db_name
        )

    cfg = load_company_config()
    clear_transactional_data()
    update_company(cfg or {})
    prefix = (cfg or {}).get("sequence_prefix_hint") or "KMS"
    reset_sequences(prefix)
    refresh_database_uuid()
    report_masters()

    if DRY_RUN:
        log("DRY-RUN complete — tidak ada commit perubahan utama (sebagian langkah mungkin sudah di-skip).")
        env.cr.rollback()
    else:
        env.cr.commit()
        log("SUCCESS: DB siap dipakai sebagai KMS. Lakukan verifikasi checklist di README.md")


main()
