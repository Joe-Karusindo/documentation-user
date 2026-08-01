# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Align CD sequence prefix to roman month and keep date-range monthly reset."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env['ir.sequence'].search([('code', '=', 'import.container.deposit')], limit=1)
    if not sequence:
        return
    vals = {
        'prefix': 'CD/%(year)s/%(rom_month)s/',
        'padding': 5,
        'use_date_range': True,
    }
    if 'range_reset' in sequence._fields:
        vals['range_reset'] = 'monthly'
    sequence.write(vals)
