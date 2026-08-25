# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CryptoPnlWizard(models.TransientModel):
    _name = 'crypto.pnl.wizard'
    _description = 'Crypto Profit & Loss Report Wizard'

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today,
    )
    asset_ids = fields.Many2many(
        'crypto.asset',
        string='Cryptos',
        help='Leave empty to include all cryptos.',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    line_ids = fields.One2many('crypto.pnl.line', 'wizard_id', string='Lines')
    total_buy = fields.Monetary(currency_field='currency_id')
    total_sell = fields.Monetary(currency_field='currency_id')
    total_fees = fields.Monetary(currency_field='currency_id')
    total_realized_pnl = fields.Monetary(
        string='Total Realized P&L',
        currency_field='currency_id',
    )
    total_unrealized_pnl = fields.Monetary(
        string='Unrealized P&L (as of To Date)',
        currency_field='currency_id',
    )

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('date', '<=', fields.Datetime.to_datetime(self.date_to).replace(
                hour=23, minute=59, second=59
            )),
            ('transaction_type', 'in', ('buy', 'sell')),
        ]
        if self.asset_ids:
            domain.append(('asset_id', 'in', self.asset_ids.ids))

        txs = self.env['crypto.transaction'].search(domain, order='asset_id, date')
        by_asset = {}
        for tx in txs:
            bucket = by_asset.setdefault(tx.asset_id, {
                'buy_qty': 0.0,
                'buy_amount': 0.0,
                'sell_qty': 0.0,
                'sell_amount': 0.0,
                'fees': 0.0,
                'realized_pnl': 0.0,
            })
            if tx.transaction_type == 'buy':
                bucket['buy_qty'] += tx.quantity
                bucket['buy_amount'] += tx.total_amount
            else:
                bucket['sell_qty'] += tx.quantity
                bucket['sell_amount'] += tx.total_amount
                bucket['realized_pnl'] += tx.realized_pnl
            bucket['fees'] += tx.fee

        # Unrealized based on current holdings of selected assets
        assets = self.asset_ids or self.env['crypto.asset'].search([
            ('company_id', '=', self.company_id.id),
        ])
        lines = []
        total_buy = total_sell = total_fees = total_realized = total_unreal = 0.0
        for asset in assets:
            data = by_asset.get(asset, {
                'buy_qty': 0.0,
                'buy_amount': 0.0,
                'sell_qty': 0.0,
                'sell_amount': 0.0,
                'fees': 0.0,
                'realized_pnl': 0.0,
            })
            unreal = asset.unrealized_pnl
            if not any([
                data['buy_qty'], data['sell_qty'], data['realized_pnl'], unreal
            ]):
                continue
            lines.append((0, 0, {
                'asset_id': asset.id,
                'buy_qty': data['buy_qty'],
                'buy_amount': data['buy_amount'],
                'sell_qty': data['sell_qty'],
                'sell_amount': data['sell_amount'],
                'fees': data['fees'],
                'realized_pnl': data['realized_pnl'],
                'quantity_held': asset.quantity,
                'cost_basis': asset.cost_basis,
                'market_value': asset.market_value,
                'unrealized_pnl': unreal,
            }))
            total_buy += data['buy_amount']
            total_sell += data['sell_amount']
            total_fees += data['fees']
            total_realized += data['realized_pnl']
            total_unreal += unreal

        self.write({
            'line_ids': lines,
            'total_buy': total_buy,
            'total_sell': total_sell,
            'total_fees': total_fees,
            'total_realized_pnl': total_realized,
            'total_unrealized_pnl': total_unreal,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crypto.pnl.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_print_report(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_compute()
        return self.env.ref(
            'crypto_investment.action_report_crypto_pnl'
        ).report_action(self)


class CryptoPnlLine(models.TransientModel):
    _name = 'crypto.pnl.line'
    _description = 'Crypto P&L Report Line'
    _order = 'realized_pnl desc'

    wizard_id = fields.Many2one('crypto.pnl.wizard', required=True, ondelete='cascade')
    asset_id = fields.Many2one('crypto.asset', string='Crypto', required=True)
    symbol = fields.Char(related='asset_id.symbol')
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    buy_qty = fields.Float(digits=(16, 8))
    buy_amount = fields.Monetary(currency_field='currency_id')
    sell_qty = fields.Float(digits=(16, 8))
    sell_amount = fields.Monetary(currency_field='currency_id')
    fees = fields.Monetary(currency_field='currency_id')
    realized_pnl = fields.Monetary(string='Realized P&L', currency_field='currency_id')
    quantity_held = fields.Float(digits=(16, 8))
    cost_basis = fields.Monetary(currency_field='currency_id')
    market_value = fields.Monetary(currency_field='currency_id')
    unrealized_pnl = fields.Monetary(string='Unrealized P&L', currency_field='currency_id')
