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


def _restore_vendor_bills_window_action(env):
    """Undo permanent writes to Accounting > Vendors > Bills / Refunds.

    Older CDM builds called ``ir.actions.act_window.update(...)`` on shared
    window actions, which stored a CDM-only domain / tree view on the menu.
    """
    repairs = (
        (
            'account.action_move_in_invoice_type',
            'account.view_in_invoice_bill_tree',
            'Bills',
            "[('move_type', '=', 'in_invoice')]",
            'tree,kanban,form',
        ),
        (
            'account.action_move_in_refund_type',
            'account.view_in_invoice_refund_tree',
            'Refunds',
            "[('move_type', '=', 'in_refund')]",
            'tree,kanban,form',
        ),
    )
    for action_xmlid, tree_xmlid, name, domain, view_mode in repairs:
        action = env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            continue
        cdm_tree = env.ref(
            'container_deposit_management.view_cdm_deposit_bill_tree',
            raise_if_not_found=False,
        )
        current_domain = action.domain or ''
        corrupted = (
            "('id', 'in'" in current_domain
            or '("id", "in"' in current_domain
            or "('id', '='" in current_domain
            or '("id", "="' in current_domain
            or (cdm_tree and action.view_id.id == cdm_tree.id)
            or bool(action.res_id)
        )
        if not corrupted:
            continue
        tree = env.ref(tree_xmlid, raise_if_not_found=False)
        action.sudo().write({
            'name': name,
            'domain': domain,
            'view_mode': view_mode,
            'view_id': tree.id if tree else False,
            'res_id': False,
        })


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    _reactivate_mapped_deposit_accounts(env)
    _restore_vendor_bills_window_action(env)


def uninstall_hook(cr, registry):
    # Intentionally no-op: do not re-deprecate accounting accounts on uninstall.
    return
