# -*- coding: utf-8 -*-
"""Install/upgrade hooks for container deposit account readiness."""


def _reactivate_mapped_deposit_accounts(env):
    """Ensure mapped deposit accounts 1720002 / 1720003 are not deprecated.

    A deprecated mapped account would make the Deposit Account column stay
    blank on auto-fill and block posting, so reactivate them on
    install/upgrade.
    """
    env.cr.execute("""
        UPDATE account_account
           SET deprecated = FALSE
         WHERE regexp_replace(COALESCE(code, ''), '[^0-9]', '', 'g') IN ('1720002', '1720003')
           AND COALESCE(deprecated, FALSE) = TRUE
    """)


def _ensure_container_deposit_sequence(env):
    """Ensure CD sequence uses roman month and monthly date ranges."""
    sequence = env['ir.sequence'].search([('code', '=', 'import.container.deposit')], limit=1)
    if not sequence:
        return
    vals = {
        'prefix': 'CD/%(year)s/%(Rmonth)s/',
        'padding': 5,
        'use_date_range': True,
    }
    if 'range_reset' in sequence._fields:
        vals['range_reset'] = 'monthly'
    sequence.write(vals)


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    _reactivate_mapped_deposit_accounts(env)
    _ensure_container_deposit_sequence(env)


def uninstall_hook(cr, registry):
    # Intentionally no-op: do not re-deprecate accounting accounts on uninstall.
    return
