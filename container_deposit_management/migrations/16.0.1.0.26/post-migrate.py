# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Posted and Done are merged into one step: move existing Posted records to Done."""
    cr.execute("""
        UPDATE import_container_deposit
           SET state = 'done'
         WHERE state = 'posted'
    """)
