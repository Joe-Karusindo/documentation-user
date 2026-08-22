def migrate(cr, version):
    """Lock settlement lines of documents that already passed the settlement
    input stage, so the new settlement_locked flag matches their state."""
    cr.execute(
        """
        UPDATE import_container_deposit
           SET settlement_locked = TRUE
         WHERE state IN ('settlement_received', 'waiting_approval',
                         'approved', 'done')
        """
    )
