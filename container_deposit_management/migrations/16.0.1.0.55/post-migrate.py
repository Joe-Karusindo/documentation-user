import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)



def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info(f"Running migration script for sequence from version {version}")
    cdm_seq = env.ref('container_deposit_management.seq_import_container_deposit')
    if cdm_seq:
        cdm_seq.prefix = 'CD/%(year)s/%(rom_month)s/'
