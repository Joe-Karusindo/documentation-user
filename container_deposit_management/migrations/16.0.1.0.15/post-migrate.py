# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Reactivate mapped deposit accounts during module upgrade."""
    cr.execute("""
        UPDATE account_account
           SET deprecated = FALSE
         WHERE regexp_replace(COALESCE(code, ''), '[^0-9]', '', 'g') IN ('1720002', '1720003')
           AND COALESCE(deprecated, FALSE) = TRUE
    """)
