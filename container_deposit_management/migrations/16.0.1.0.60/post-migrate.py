# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Repair Accounting > Vendors > Bills / Refunds after CDM corrupted actions.

    Older CDM versions called ``recordset.update()`` on shared window actions,
    permanently storing a CDM-only domain / tree view. Restore standard actions.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
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
    cdm_tree = env.ref(
        'container_deposit_management.view_cdm_deposit_bill_tree',
        raise_if_not_found=False,
    )
    for action_xmlid, tree_xmlid, name, domain, view_mode in repairs:
        action = env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            continue
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
