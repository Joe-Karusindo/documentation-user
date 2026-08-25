# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CryptoTransaction(models.Model):
    _name = 'crypto.transaction'
    _description = 'Crypto Buy/Sell Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    asset_id = fields.Many2one(
        'crypto.asset',
        string='Crypto',
        required=True,
        tracking=True,
        index=True,
    )
    symbol = fields.Char(related='asset_id.symbol', store=True)
    transaction_type = fields.Selection(
        [
            ('buy', 'Buy'),
            ('sell', 'Sell'),
            ('beginning', 'Beginning Balance'),
        ],
        required=True,
        tracking=True,
        default='buy',
    )
    quantity = fields.Float(required=True, digits=(16, 8), tracking=True)
    unit_price = fields.Float(
        string='Price / Unit',
        required=True,
        digits=(16, 8),
        tracking=True,
        help='Market price per unit at transaction time.',
    )
    unit_cost = fields.Float(
        string='Unit Cost (avg)',
        digits=(16, 8),
        readonly=True,
        help='Average cost used for sell COGS / beginning cost.',
        copy=False,
    )
    fee = fields.Monetary(
        string='Fee',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    subtotal = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help='Buy: price*qty + fee. Sell: price*qty - fee.',
    )
    cost_of_sold = fields.Monetary(
        string='Cost of Sold',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    realized_pnl = fields.Monetary(
        string='Realized P&L',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='asset_id.currency_id',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('type', 'in', ('general', 'bank', 'cash')), ('company_id', '=', company_id)]",
        check_company=True,
    )
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    beginning_balance_id = fields.Many2one(
        'crypto.beginning.balance',
        string='Beginning Balance',
        ondelete='cascade',
        copy=False,
    )
    partner_id = fields.Many2one('res.partner', string='Exchange / Counterparty')
    notes = fields.Text()
    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        digits=(16, 8),
    )

    @api.depends('quantity', 'unit_price', 'fee', 'transaction_type', 'unit_cost')
    def _compute_amounts(self):
        for tx in self:
            subtotal = tx.quantity * tx.unit_price
            tx.subtotal = subtotal
            if tx.transaction_type == 'buy':
                tx.total_amount = subtotal + tx.fee
                tx.cost_of_sold = 0.0
                tx.realized_pnl = 0.0
            elif tx.transaction_type == 'sell':
                tx.total_amount = subtotal - tx.fee
                cost = (tx.unit_cost or 0.0) * tx.quantity
                tx.cost_of_sold = cost
                tx.realized_pnl = tx.total_amount - cost
            else:  # beginning
                cost_price = tx.unit_cost or tx.unit_price
                tx.total_amount = tx.quantity * cost_price
                tx.cost_of_sold = 0.0
                tx.realized_pnl = 0.0

    def _compute_available_qty(self):
        for tx in self:
            tx.available_qty = tx.asset_id.quantity if tx.asset_id else 0.0

    @api.onchange('asset_id', 'transaction_type')
    def _onchange_asset_id(self):
        if self.asset_id and self.asset_id.current_price and not self.unit_price:
            self.unit_price = self.asset_id.current_price
        if self.transaction_type == 'sell' and self.asset_id:
            self.unit_cost = self.asset_id.average_cost

    @api.onchange('transaction_type')
    def _onchange_transaction_type(self):
        if self.transaction_type == 'beginning':
            self.fee = 0.0

    @api.constrains('quantity', 'unit_price')
    def _check_positive_values(self):
        for tx in self:
            if tx.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
            if tx.unit_price < 0:
                raise ValidationError(_('Unit price cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'crypto.transaction'
                ) or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for tx in self:
            if tx.state != 'draft':
                raise UserError(_('Only draft transactions can be confirmed.'))
            if tx.transaction_type == 'beginning' and not self.env.context.get('from_beginning'):
                # beginning txs are created already done by beginning balance
                pass
            if tx.transaction_type == 'sell':
                available = tx._get_available_quantity_before()
                if tx.quantity > available + 1e-12:
                    raise UserError(_(
                        'Insufficient %(symbol)s quantity. Available: %(avail).8f, '
                        'trying to sell: %(qty).8f'
                    ) % {
                        'symbol': tx.asset_id.symbol,
                        'avail': available,
                        'qty': tx.quantity,
                    })
                tx.unit_cost = tx._get_average_cost_before()
            elif tx.transaction_type == 'buy':
                tx.unit_cost = tx.unit_price
            elif tx.transaction_type == 'beginning':
                tx.unit_cost = tx.unit_cost or tx.unit_price

            tx._create_accounting_entry()
            tx.state = 'done'
            # refresh market price from trade if newer
            if tx.unit_price and tx.transaction_type in ('buy', 'sell'):
                tx.asset_id.write({
                    'current_price': tx.unit_price,
                    'last_price_update': fields.Datetime.now(),
                })
                self.env['crypto.price.history'].create({
                    'asset_id': tx.asset_id.id,
                    'date': fields.Date.to_date(tx.date) if tx.date else fields.Date.context_today(tx),
                    'price': tx.unit_price,
                    'source': 'transaction',
                    'transaction_id': tx.id,
                })
        return True

    def action_cancel(self):
        for tx in self:
            if tx.state == 'cancelled':
                continue
            if tx.move_id and tx.move_id.state == 'posted':
                tx.move_id.button_draft()
                tx.move_id.button_cancel()
            tx.state = 'cancelled'
        return True

    def action_draft(self):
        for tx in self:
            if tx.state != 'cancelled':
                raise UserError(_('Only cancelled transactions can be reset to draft.'))
            if tx.transaction_type == 'beginning':
                raise UserError(_('Beginning balance transactions cannot be reset manually.'))
            tx.state = 'draft'
        return True

    def _get_prior_done_transactions(self):
        self.ensure_one()
        domain = [
            ('asset_id', '=', self.asset_id.id),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
            '|',
            ('date', '<', self.date),
            '&', ('date', '=', self.date), ('id', '<', self.id or 0),
        ]
        return self.search(domain, order='date asc, id asc')

    def _get_available_quantity_before(self):
        self.ensure_one()
        qty = 0.0
        for prev in self._get_prior_done_transactions():
            if prev.transaction_type in ('buy', 'beginning'):
                qty += prev.quantity
            else:
                qty -= prev.quantity
        return qty

    def _get_average_cost_before(self):
        self.ensure_one()
        qty = 0.0
        cost = 0.0
        for prev in self._get_prior_done_transactions():
            if prev.transaction_type in ('buy', 'beginning'):
                add_cost = (
                    prev.total_amount if prev.transaction_type == 'buy'
                    else prev.quantity * (prev.unit_cost or prev.unit_price)
                )
                qty += prev.quantity
                cost += add_cost
            elif prev.transaction_type == 'sell' and qty:
                avg = cost / qty
                cost -= avg * prev.quantity
                qty -= prev.quantity
        return (cost / qty) if qty else 0.0

    def _create_accounting_entry(self):
        """Post journal entry for buy/sell. Skips if accounts are not configured."""
        self.ensure_one()
        if self.transaction_type == 'beginning':
            return

        company = self.company_id
        journal = self.journal_id
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', 'in', ('bank', 'cash', 'general')),
                ('company_id', '=', company.id),
            ], limit=1)
            if not journal:
                return
            self.journal_id = journal

        cash_account = company.crypto_cash_account_id
        asset_account = self.asset_id.account_asset_id or company.crypto_asset_account_id
        gain_account = company.crypto_gain_account_id
        loss_account = company.crypto_loss_account_id
        fee_account = company.crypto_fee_account_id

        if not cash_account or not asset_account:
            return

        label = '%s %s %s' % (self.transaction_type.upper(), self.quantity, self.asset_id.symbol)
        lines = []

        if self.transaction_type == 'buy':
            # Dr Crypto Asset (price*qty [+fee if no fee account])
            # Dr Fee expense (optional)
            # Cr Cash (price*qty + fee)
            asset_debit = self.total_amount if (self.fee and not fee_account) else self.subtotal
            lines.append((0, 0, {
                'name': label,
                'account_id': asset_account.id,
                'debit': asset_debit,
                'credit': 0.0,
            }))
            if self.fee and fee_account:
                lines.append((0, 0, {
                    'name': _('Fee — %s') % label,
                    'account_id': fee_account.id,
                    'debit': self.fee,
                    'credit': 0.0,
                }))
            lines.append((0, 0, {
                'name': label,
                'account_id': cash_account.id,
                'debit': 0.0,
                'credit': self.subtotal + (self.fee or 0.0),
            }))

        elif self.transaction_type == 'sell':
            # Dr Cash (price*qty - fee)
            # Dr Fee expense (optional; when set, cash is net and fee is separate)
            # Cr Crypto Asset (avg cost * qty)
            # Cr Gain / Dr Loss  (realized_pnl = total_amount - cost_of_sold)
            #
            # Balance check when fee_account set:
            #   debit  = (proceeds - fee) + fee = proceeds
            #   credit = cost + (proceeds - fee - cost) = proceeds - fee  → short by fee
            # So when fee is booked separately, P&L must use gross proceeds vs cost,
            # OR we debit cash for full proceeds. We choose: debit cash NET and
            # compute balancing P&L as (proceeds - cost), with fee as expense
            # reducing equity via P&L naturally — use gross PnL for JE:
            #   realized for books = proceeds - cost; fee stays expense.
            proceeds = self.subtotal
            cost = self.cost_of_sold
            gross_pnl = proceeds - cost

            if self.fee and fee_account:
                lines.append((0, 0, {
                    'name': label,
                    'account_id': cash_account.id,
                    'debit': self.total_amount,
                    'credit': 0.0,
                }))
                lines.append((0, 0, {
                    'name': _('Fee — %s') % label,
                    'account_id': fee_account.id,
                    'debit': self.fee,
                    'credit': 0.0,
                }))
                pnl_for_entry = gross_pnl
            else:
                lines.append((0, 0, {
                    'name': label,
                    'account_id': cash_account.id,
                    'debit': self.total_amount,
                    'credit': 0.0,
                }))
                pnl_for_entry = self.realized_pnl  # net of fee

            lines.append((0, 0, {
                'name': _('COGS — %s') % label,
                'account_id': asset_account.id,
                'debit': 0.0,
                'credit': cost,
            }))

            pnl_account = (gain_account if pnl_for_entry >= 0 else loss_account) or gain_account or loss_account
            if pnl_account and abs(pnl_for_entry) > 1e-9:
                if pnl_for_entry >= 0:
                    lines.append((0, 0, {
                        'name': _('Gain — %s') % label,
                        'account_id': pnl_account.id,
                        'debit': 0.0,
                        'credit': pnl_for_entry,
                    }))
                else:
                    lines.append((0, 0, {
                        'name': _('Loss — %s') % label,
                        'account_id': pnl_account.id,
                        'debit': abs(pnl_for_entry),
                        'credit': 0.0,
                    }))

        if not lines:
            return

        debit = sum(l[2]['debit'] for l in lines)
        credit = sum(l[2]['credit'] for l in lines)
        if abs(debit - credit) > 0.0001:
            diff = debit - credit
            lines.append((0, 0, {
                'name': _('Rounding — %s') % label,
                'account_id': cash_account.id,
                'debit': 0.0 if diff > 0 else abs(diff),
                'credit': diff if diff > 0 else 0.0,
            }))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.to_date(self.date) if self.date else fields.Date.context_today(self),
            'journal_id': journal.id,
            'ref': self.name,
            'company_id': company.id,
            'line_ids': lines,
        })
        move.action_post()
        self.move_id = move
