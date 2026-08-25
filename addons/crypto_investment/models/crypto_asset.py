# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CryptoAsset(models.Model):
    _name = 'crypto.asset'
    _description = 'Crypto Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'symbol'
    _rec_name = 'display_name'

    name = fields.Char(required=True, tracking=True)
    symbol = fields.Char(required=True, tracking=True, index=True)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Valuation Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    current_price = fields.Float(
        string='Current Market Price',
        digits=(16, 8),
        tracking=True,
        help='Latest market price per unit in valuation currency.',
    )
    last_price_update = fields.Datetime(string='Last Price Update', readonly=True)
    quantity = fields.Float(
        string='Quantity Held',
        digits=(16, 8),
        compute='_compute_holdings',
        store=True,
    )
    average_cost = fields.Float(
        string='Average Cost',
        digits=(16, 8),
        compute='_compute_holdings',
        store=True,
    )
    cost_basis = fields.Monetary(
        string='Cost Basis',
        compute='_compute_holdings',
        store=True,
        currency_field='currency_id',
    )
    market_value = fields.Monetary(
        string='Market Value',
        compute='_compute_holdings',
        store=True,
        currency_field='currency_id',
    )
    unrealized_pnl = fields.Monetary(
        string='Unrealized P&L',
        compute='_compute_holdings',
        store=True,
        currency_field='currency_id',
    )
    unrealized_pnl_percent = fields.Float(
        string='Unrealized P&L %',
        compute='_compute_holdings',
        store=True,
        digits=(16, 2),
    )
    realized_pnl = fields.Monetary(
        string='Realized P&L',
        compute='_compute_holdings',
        store=True,
        currency_field='currency_id',
    )
    transaction_ids = fields.One2many('crypto.transaction', 'asset_id', string='Transactions')
    transaction_count = fields.Integer(compute='_compute_transaction_count')
    price_history_ids = fields.One2many('crypto.price.history', 'asset_id', string='Price History')
    projection_line_ids = fields.One2many(
        'crypto.price.projection.line', 'asset_id', string='Projections'
    )
    account_asset_id = fields.Many2one(
        'account.account',
        string='Crypto Asset Account',
        domain="[('account_type', 'in', ('asset_current', 'asset_non_current', 'asset_cash'))]",
        company_dependent=True,
        help='Account used to book crypto asset value.',
    )
    notes = fields.Text()
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('symbol_company_uniq', 'unique(symbol, company_id)',
         'Crypto symbol must be unique per company.'),
    ]

    @api.depends('name', 'symbol')
    def _compute_display_name(self):
        for asset in self:
            if asset.symbol and asset.name:
                asset.display_name = '%s (%s)' % (asset.symbol, asset.name)
            else:
                asset.display_name = asset.name or asset.symbol or _('New')

    @api.depends(
        'transaction_ids.state',
        'transaction_ids.transaction_type',
        'transaction_ids.quantity',
        'transaction_ids.total_amount',
        'transaction_ids.realized_pnl',
        'transaction_ids.unit_cost',
        'current_price',
    )
    def _compute_holdings(self):
        for asset in self:
            done = asset.transaction_ids.filtered(lambda t: t.state == 'done')
            qty = 0.0
            cost = 0.0
            realized = 0.0
            for tx in done.sorted('date'):
                if tx.transaction_type in ('buy', 'beginning'):
                    qty += tx.quantity
                    cost += tx.total_amount if tx.transaction_type == 'buy' else (tx.quantity * tx.unit_cost)
                elif tx.transaction_type == 'sell':
                    avg = (cost / qty) if qty else 0.0
                    sold_cost = avg * tx.quantity
                    cost -= sold_cost
                    qty -= tx.quantity
                    realized += tx.realized_pnl
            asset.quantity = qty
            asset.cost_basis = cost
            asset.average_cost = (cost / qty) if qty else 0.0
            asset.market_value = qty * asset.current_price
            asset.unrealized_pnl = asset.market_value - cost
            asset.unrealized_pnl_percent = (
                (asset.unrealized_pnl / cost * 100.0) if cost else 0.0
            )
            asset.realized_pnl = realized

    def _compute_transaction_count(self):
        for asset in self:
            asset.transaction_count = len(asset.transaction_ids)

    @api.constrains('symbol')
    def _check_symbol(self):
        for asset in self:
            if asset.symbol and not asset.symbol.strip():
                raise ValidationError(_('Symbol cannot be empty.'))

    def action_view_transactions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transactions — %s') % self.symbol,
            'res_model': 'crypto.transaction',
            'view_mode': 'tree,form,graph,pivot',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'default_asset_id': self.id,
                'search_default_done': 1,
            },
        }

    def action_view_price_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Price History — %s') % self.symbol,
            'res_model': 'crypto.price.history',
            'view_mode': 'tree,form,graph',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_update_price(self):
        """Record current price into price history."""
        History = self.env['crypto.price.history']
        now = fields.Datetime.now()
        for asset in self:
            if not asset.current_price:
                continue
            History.create({
                'asset_id': asset.id,
                'date': fields.Date.context_today(asset),
                'price': asset.current_price,
                'source': 'manual',
            })
            asset.last_price_update = now
        return True

    def name_get(self):
        return [(a.id, a.display_name or a.name) for a in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = args
        if name:
            domain = ['|', ('symbol', operator, name), ('name', operator, name)] + args
        return self.search(domain, limit=limit).name_get()
