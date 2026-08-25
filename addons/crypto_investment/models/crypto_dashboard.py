# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CryptoDashboard(models.TransientModel):
    _name = 'crypto.dashboard'
    _description = 'Crypto Portfolio Dashboard'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    total_market_value = fields.Monetary(currency_field='currency_id')
    total_cost_basis = fields.Monetary(currency_field='currency_id')
    total_unrealized_pnl = fields.Monetary(currency_field='currency_id')
    total_realized_pnl = fields.Monetary(currency_field='currency_id')
    total_pnl = fields.Monetary(string='Total P&L', currency_field='currency_id')
    asset_count = fields.Integer(string='Assets Held')
    buy_count = fields.Integer()
    sell_count = fields.Integer()
    last_projection_summary = fields.Text()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        assets = self.env['crypto.asset'].search([
            ('company_id', '=', company.id),
            ('quantity', '>', 0),
        ])
        all_assets = self.env['crypto.asset'].search([('company_id', '=', company.id)])
        txs = self.env['crypto.transaction'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'done'),
        ])
        market = sum(all_assets.mapped('market_value'))
        cost = sum(all_assets.mapped('cost_basis'))
        unreal = sum(all_assets.mapped('unrealized_pnl'))
        realized = sum(all_assets.mapped('realized_pnl'))
        res.update({
            'company_id': company.id,
            'total_market_value': market,
            'total_cost_basis': cost,
            'total_unrealized_pnl': unreal,
            'total_realized_pnl': realized,
            'total_pnl': unreal + realized,
            'asset_count': len(assets),
            'buy_count': len(txs.filtered(lambda t: t.transaction_type == 'buy')),
            'sell_count': len(txs.filtered(lambda t: t.transaction_type == 'sell')),
        })
        projection = self.env['crypto.price.projection'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'done'),
        ], order='date desc, id desc', limit=1)
        if projection:
            ups = projection.line_ids.filtered(lambda l: l.trend == 'up')
            downs = projection.line_ids.filtered(lambda l: l.trend == 'down')
            sides = projection.line_ids.filtered(lambda l: l.trend == 'sideways')
            res['last_projection_summary'] = _(
                'Proyeksi terakhir (%(name)s, %(date)s): '
                '%(up)s naik, %(down)s turun, %(side)s sideways.'
            ) % {
                'name': projection.name,
                'date': projection.date,
                'up': len(ups),
                'down': len(downs),
                'side': len(sides),
            }
        else:
            res['last_projection_summary'] = _(
                'Belum ada proyeksi. Buat analisa proyeksi 14 hari dari menu Analisa.'
            )
        return res

    def action_refresh(self):
        self.ensure_one()
        vals = self.default_get(list(self._fields))
        self.write(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crypto.dashboard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_open_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Crypto Assets'),
            'res_model': 'crypto.asset',
            'view_mode': 'tree,kanban,form,graph,pivot',
            'domain': [('company_id', '=', self.company_id.id)],
        }

    def action_open_transactions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transactions'),
            'res_model': 'crypto.transaction',
            'view_mode': 'tree,form,graph,pivot',
            'domain': [('company_id', '=', self.company_id.id), ('state', '=', 'done')],
        }

    def action_open_pnl(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Profit & Loss Report'),
            'res_model': 'crypto.pnl.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_projection(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Price Projection'),
            'res_model': 'crypto.price.projection',
            'view_mode': 'tree,form',
        }

    @api.model
    def action_open_dashboard(self):
        dash = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Crypto Dashboard'),
            'res_model': 'crypto.dashboard',
            'view_mode': 'form',
            'res_id': dash.id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'readonly'},
        }
