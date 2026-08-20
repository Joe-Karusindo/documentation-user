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




def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    _reactivate_mapped_deposit_accounts(env)


def uninstall_hook(cr, registry):
    # Intentionally no-op: do not re-deprecate accounting accounts on uninstall.
    return
