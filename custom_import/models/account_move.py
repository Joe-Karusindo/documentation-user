from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'


    custom_import_id = fields.Many2one('custom.import', string='Import Reference', readonly=True)