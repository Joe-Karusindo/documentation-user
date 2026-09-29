#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifikasi cepat setelah sanitize_kms.py.
Jalankan di odoo-bin shell -d kms.
"""

assert "env" in dir()


def c(model):
    if model not in env:
        return "N/A"
    return env[model].sudo().with_context(active_test=False).search_count([])


company = env.company
print("Company:", company.name)
print("VAT/NPWP:", company.vat)
print("Partner:", company.partner_id.display_name)
print("DB UUID:", env["ir.config_parameter"].sudo().get_param("database.uuid"))
print("--- masters ---")
for m in (
    "account.account",
    "account.tax",
    "account.journal",
    "res.partner",
    "product.template",
    "stock.warehouse",
    "stock.location",
):
    print(" %s: %s" % (m, c(m)))
print("--- transactions (expect 0) ---")
for m in (
    "account.move",
    "account.payment",
    "sale.order",
    "purchase.order",
    "stock.picking",
    "stock.move",
    "stock.quant",
    "stock.valuation.layer",
):
    print(" %s: %s" % (m, c(m)))

# Saldo kasar COA via account move lines — harus 0 jika bersih
if "account.move.line" in env:
    env.cr.execute(
        """
        SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0)
        FROM account_move_line
        """
    )
    debit, credit = env.cr.fetchone()
    print("Sum debit/credit move lines:", debit, credit)
