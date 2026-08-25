# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CryptoBeginningBalance(models.Model):
    _name = 'crypto.beginning.balance'
    _description = 'Crypto Beginning Balance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )
    cash_balance = fields.Monetary(
        string='Cash Beginning Balance',
        currency_field='currency_id',
        tracking=True,
        help='Opening cash/bank balance available for crypto trading.',
    )
    line_ids = fields.One2many(
        'crypto.beginning.balance.line',
        'balance_id',
        string='Crypto Holdings',
        copy=True,
    )
    total_crypto_value = fields.Monetary(
        string='Total Crypto Value',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    total_portfolio = fields.Monetary(
        string='Total Portfolio',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        copy=False,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', 'in', ('general', 'bank', 'cash')), ('company_id', '=', company_id)]",
        check_company=True,
    )
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    notes = fields.Text()

    @api.depends('cash_balance', 'line_ids.total_value')
    def _compute_totals(self):
        for rec in self:
            crypto_val = sum(rec.line_ids.mapped('total_value'))
            rec.total_crypto_value = crypto_val
            rec.total_portfolio = crypto_val + rec.cash_balance

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'crypto.beginning.balance'
                ) or _('New')
        return super().create(vals_list)

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft beginning balances can be posted.'))
            if not rec.line_ids and not rec.cash_balance:
                raise UserError(_('Add cash balance and/or crypto holdings before posting.'))
            rec._create_opening_transactions()
            rec._create_accounting_entry()
            rec.state = 'posted'
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state != 'posted':
                raise UserError(_('Only posted beginning balances can be cancelled.'))
            txs = self.env['crypto.transaction'].search([
                ('beginning_balance_id', '=', rec.id),
                ('state', '=', 'done'),
            ])
            txs.action_cancel()
            if rec.move_id and rec.move_id.state == 'posted':
                rec.move_id.button_draft()
                rec.move_id.button_cancel()
            rec.state = 'cancelled'
        return True

    def action_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_('Only cancelled records can be reset to draft.'))
            rec.state = 'draft'
        return True

    def _create_opening_transactions(self):
        self.ensure_one()
        Transaction = self.env['crypto.transaction']
        for line in self.line_ids:
            Transaction.create({
                'date': self.date,
                'asset_id': line.asset_id.id,
                'transaction_type': 'beginning',
                'quantity': line.quantity,
                'unit_price': line.unit_cost,
                'unit_cost': line.unit_cost,
                'fee': 0.0,
                'company_id': self.company_id.id,
                'beginning_balance_id': self.id,
                'state': 'done',
                'notes': _('Opening balance from %s') % self.name,
            })
            if line.unit_cost and not line.asset_id.current_price:
                line.asset_id.current_price = line.unit_cost

    def _create_accounting_entry(self):
        self.ensure_one()
        if not self.journal_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not journal:
                return
            self.journal_id = journal

        company = self.company_id
        equity_account = company.crypto_opening_equity_account_id
        cash_account = company.crypto_cash_account_id
        if not equity_account:
            return

        line_cmds = []
        if self.cash_balance and cash_account:
            line_cmds.append((0, 0, {
                'name': _('Crypto cash opening — %s') % self.name,
                'account_id': cash_account.id,
                'debit': self.cash_balance,
                'credit': 0.0,
            }))
            line_cmds.append((0, 0, {
                'name': _('Crypto cash opening equity — %s') % self.name,
                'account_id': equity_account.id,
                'debit': 0.0,
                'credit': self.cash_balance,
            }))

        for line in self.line_ids:
            asset_account = line.asset_id.account_asset_id or company.crypto_asset_account_id
            if not asset_account or not line.total_value:
                continue
            line_cmds.append((0, 0, {
                'name': _('Opening %s — %s') % (line.asset_id.symbol, self.name),
                'account_id': asset_account.id,
                'debit': line.total_value,
                'credit': 0.0,
            }))
            line_cmds.append((0, 0, {
                'name': _('Opening equity %s — %s') % (line.asset_id.symbol, self.name),
                'account_id': equity_account.id,
                'debit': 0.0,
                'credit': line.total_value,
            }))

        if not line_cmds:
            return

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'company_id': company.id,
            'line_ids': line_cmds,
        })
        move.action_post()
        self.move_id = move


class CryptoBeginningBalanceLine(models.Model):
    _name = 'crypto.beginning.balance.line'
    _description = 'Crypto Beginning Balance Line'

    balance_id = fields.Many2one(
        'crypto.beginning.balance',
        required=True,
        ondelete='cascade',
    )
    asset_id = fields.Many2one('crypto.asset', string='Crypto', required=True)
    quantity = fields.Float(required=True, digits=(16, 8))
    unit_cost = fields.Float(
        string='Unit Cost',
        required=True,
        digits=(16, 8),
        help='Historical cost per unit at opening.',
    )
    currency_id = fields.Many2one(related='balance_id.currency_id')
    total_value = fields.Monetary(
        compute='_compute_total_value',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('quantity', 'unit_cost')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.quantity * line.unit_cost

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id and self.asset_id.current_price:
            self.unit_cost = self.asset_id.current_price
