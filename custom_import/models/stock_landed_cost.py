from odoo import models, fields, api, _

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    # Tambahkan field relasi ke Custom Import
    custom_import_id = fields.Many2one('custom.import', string='Import Reference', readonly=True)
    