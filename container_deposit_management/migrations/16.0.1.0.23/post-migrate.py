# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Migrate users from legacy CDM groups to the revised permission groups."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Group = env['res.groups'].sudo()

    legacy_map = {
        'container_deposit_management.group_container_deposit_import': 'container_deposit_management.group_container_deposit_user',
    }
    for old_xmlid, new_xmlid in legacy_map.items():
        old_group = env.ref(old_xmlid, raise_if_not_found=False)
        new_group = env.ref(new_xmlid, raise_if_not_found=False)
        if not old_group or not new_group:
            continue
        users = old_group.users
        if users:
            new_group.write({'users': [(4, user.id) for user in users]})
