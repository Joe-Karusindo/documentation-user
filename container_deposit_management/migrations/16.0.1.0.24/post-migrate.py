# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Fix CD sequence prefix: rom_month is not supported by od_journal_sequence."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env['ir.sequence'].search([('code', '=', 'import.container.deposit')], limit=1)
    if sequence and 'rom_month' in (sequence.prefix or ''):
        sequence.write({'prefix': sequence.prefix.replace('%(rom_month)s', '%(Rmonth)s')})
