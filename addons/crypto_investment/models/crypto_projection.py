# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CryptoPriceProjection(models.Model):
    _name = 'crypto.price.projection'
    _description = 'Crypto Price Projection (14 days)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    date = fields.Date(
        string='Projection Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    horizon_days = fields.Integer(
        string='Horizon (days)',
        default=14,
        required=True,
        help='Number of days to project forward (default 14 = 2 weeks).',
    )
    lookback_days = fields.Integer(
        string='Lookback (days)',
        default=30,
        required=True,
        help='Historical window used for linear regression.',
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    asset_ids = fields.Many2many(
        'crypto.asset',
        string='Assets to Project',
        help='Leave empty to project all active crypto assets.',
    )
    line_ids = fields.One2many(
        'crypto.price.projection.line',
        'projection_id',
        string='Projection Lines',
        copy=False,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Computed'),
        ],
        default='draft',
        tracking=True,
        copy=False,
    )
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'crypto.price.projection'
                ) or _('New')
        return super().create(vals_list)

    def action_compute(self):
        for rec in self:
            if rec.horizon_days <= 0:
                raise UserError(_('Horizon days must be positive.'))
            if rec.lookback_days < 2:
                raise UserError(_('Lookback days must be at least 2.'))
            rec.line_ids.unlink()
            assets = rec.asset_ids or self.env['crypto.asset'].search([
                ('active', '=', True),
                ('company_id', '=', rec.company_id.id),
            ])
            lines = []
            for asset in assets:
                result = rec._project_asset(asset)
                if result:
                    lines.append((0, 0, result))
            rec.write({'line_ids': lines, 'state': 'done'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def _project_asset(self, asset):
        """Linear regression on historical prices → 14-day forecast."""
        self.ensure_one()
        History = self.env['crypto.price.history']
        start = self.date - timedelta(days=self.lookback_days)
        histories = History.search([
            ('asset_id', '=', asset.id),
            ('date', '>=', start),
            ('date', '<=', self.date),
        ], order='date asc')

        points = []
        for h in histories:
            x = (h.date - start).days
            points.append((float(x), float(h.price)))

        # Fallback: use current price as flat series if insufficient history
        if len(points) < 2:
            price = asset.current_price or asset.average_cost or 0.0
            if not price:
                return False
            return {
                'asset_id': asset.id,
                'current_price': price,
                'projected_price': price,
                'change_amount': 0.0,
                'change_percent': 0.0,
                'trend': 'sideways',
                'slope': 0.0,
                'confidence': 'low',
                'method': 'insufficient_history',
                'sample_count': len(points),
            }

        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xx = sum(p[0] * p[0] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        denom = (n * sum_xx - sum_x * sum_x) or 1.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        current_x = (self.date - start).days
        current_price = asset.current_price or points[-1][1]
        future_x = current_x + self.horizon_days
        projected = intercept + slope * future_x
        if projected < 0:
            projected = 0.0

        change_amount = projected - current_price
        change_percent = (change_amount / current_price * 100.0) if current_price else 0.0

        # Trend thresholds: >1% up, <-1% down, else sideways
        if change_percent > 1.0:
            trend = 'up'
        elif change_percent < -1.0:
            trend = 'down'
        else:
            trend = 'sideways'

        # Simple R² for confidence
        y_mean = sum_y / n
        ss_tot = sum((p[1] - y_mean) ** 2 for p in points) or 1.0
        ss_res = sum((p[1] - (intercept + slope * p[0])) ** 2 for p in points)
        r2 = max(0.0, 1.0 - (ss_res / ss_tot))
        if r2 >= 0.7 and n >= 10:
            confidence = 'high'
        elif r2 >= 0.4 and n >= 5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'asset_id': asset.id,
            'current_price': current_price,
            'projected_price': projected,
            'change_amount': change_amount,
            'change_percent': change_percent,
            'trend': trend,
            'slope': slope,
            'confidence': confidence,
            'method': 'linear_regression',
            'sample_count': n,
            'r_squared': r2,
        }


class CryptoPriceProjectionLine(models.Model):
    _name = 'crypto.price.projection.line'
    _description = 'Crypto Price Projection Line'
    _order = 'change_percent desc'

    projection_id = fields.Many2one(
        'crypto.price.projection',
        required=True,
        ondelete='cascade',
    )
    asset_id = fields.Many2one('crypto.asset', string='Crypto', required=True)
    symbol = fields.Char(related='asset_id.symbol', store=True)
    currency_id = fields.Many2one(related='projection_id.currency_id')
    current_price = fields.Float(digits=(16, 8))
    projected_price = fields.Float(
        string='Projected Price (14d)',
        digits=(16, 8),
    )
    change_amount = fields.Float(string='Δ Amount', digits=(16, 8))
    change_percent = fields.Float(string='Δ %', digits=(16, 2))
    trend = fields.Selection(
        [
            ('up', 'Naik'),
            ('down', 'Turun'),
            ('sideways', 'Sideways'),
        ],
        string='Trend',
    )
    slope = fields.Float(digits=(16, 10), help='Daily slope from linear regression.')
    confidence = fields.Selection(
        [
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
    )
    method = fields.Char()
    sample_count = fields.Integer(string='Samples')
    r_squared = fields.Float(string='R²', digits=(16, 4))
    analysis = fields.Text(compute='_compute_analysis')

    @api.depends('trend', 'change_percent', 'projected_price', 'current_price', 'confidence', 'symbol')
    def _compute_analysis(self):
        for line in self:
            trend_label = {
                'up': _('naik'),
                'down': _('turun'),
                'sideways': _('sideways / stabil'),
            }.get(line.trend, '')
            line.analysis = _(
                '%(symbol)s diproyeksikan %(trend)s sebesar %(pct).2f%% '
                'dalam 2 minggu (dari %(cur).8f → %(proj).8f). '
                'Kepercayaan model: %(conf)s (n=%(n)s, R²=%(r2).2f).'
            ) % {
                'symbol': line.symbol or '',
                'trend': trend_label,
                'pct': line.change_percent or 0.0,
                'cur': line.current_price or 0.0,
                'proj': line.projected_price or 0.0,
                'conf': line.confidence or '-',
                'n': line.sample_count or 0,
                'r2': line.r_squared or 0.0,
            }
