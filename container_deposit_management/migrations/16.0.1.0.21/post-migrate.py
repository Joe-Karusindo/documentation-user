# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Backfill FTM and vendor-bill links on existing container landed costs."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    LandedCost = env['stock.landed.cost'].sudo()
    costs = LandedCost.search([('container_deposit_id', '!=', False)])

    for cost in costs:
        deposit = cost.container_deposit_id
        vendor_bills = deposit.deposit_line_ids.mapped('vendor_bill_id')
        vals = {}
        if deposit.ftm_id and 'custom_declaration_import_id' in cost._fields:
            vals['custom_declaration_import_id'] = deposit.ftm_id.id
        if vendor_bills and 'vendor_bill_id' in cost._fields:
            vals['vendor_bill_id'] = vendor_bills[0].id
        if 'vendor_bill_ids' in cost._fields:
            vals['vendor_bill_ids'] = [(6, 0, vendor_bills.ids)]
        if vals:
            cost.write(vals)
