# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CryptoPriceHistory(models.Model):
    _name = 'crypto.price.history'
    _description = 'Crypto Price History'
    _order = 'date desc, id desc'

    asset_id = fields.Many2one(
        'crypto.asset',
        string='Crypto',
        required=True,
        index=True,
        ondelete='cascade',
    )
    symbol = fields.Char(related='asset_id.symbol', store=True)
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    price = fields.Float(required=True, digits=(16, 8))
    currency_id = fields.Many2one(related='asset_id.currency_id', store=True)
    source = fields.Selection(
        [
            ('manual', 'Manual'),
            ('transaction', 'Transaction'),
            ('api', 'API'),
            ('import', 'Import'),
        ],
        default='manual',
        required=True,
    )
    transaction_id = fields.Many2one('crypto.transaction', ondelete='set null')
    company_id = fields.Many2one(related='asset_id.company_id', store=True)
    notes = fields.Char()

    _sql_constraints = [
        ('asset_date_source_uniq', 'unique(asset_id, date, source, transaction_id)',
         'A price history entry already exists for this asset/date/source.'),
    ]

    def name_get(self):
        return [
            (r.id, '%s — %s: %s' % (r.symbol, r.date, r.price))
            for r in self
        ]

    @api.model
    def action_record_all_current_prices(self):
        """Cron/manual helper: snapshot current prices for all assets."""
        assets = self.env['crypto.asset'].search([('active', '=', True), ('current_price', '>', 0)])
        today = fields.Date.context_today(self)
        for asset in assets:
            existing = self.search([
                ('asset_id', '=', asset.id),
                ('date', '=', today),
                ('source', '=', 'manual'),
            ], limit=1)
            if existing:
                existing.price = asset.current_price
            else:
                self.create({
                    'asset_id': asset.id,
                    'date': today,
                    'price': asset.current_price,
                    'source': 'manual',
                })
            asset.last_price_update = fields.Datetime.now()
        return True
