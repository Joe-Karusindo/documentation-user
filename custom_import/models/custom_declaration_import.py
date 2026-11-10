from odoo import models, fields, api

class CustomDeclarationImport(models.Model):
    _inherit = 'custom.declaration.import'

    cpr_id = fields.Many2one(
        'custom.import', 
        string='Cost Payment Request', 
        compute='_compute_cpr_id', 
    )

    @api.depends('stock_picking_ids') # Atur ulang sesuai kebutuhan trigger recompute-nya
    def _compute_cpr_id(self):
        for rec in self:
            cpr = self.env['custom.import'].search([('ftm_id', '=', rec.id)], limit=1)
            rec.cpr_id = cpr.id if cpr else False