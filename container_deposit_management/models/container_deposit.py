# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ImportContainerDeposit(models.Model):
    _name = 'import.container.deposit'
    _description = 'Container Deposit Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    GROUP_USER = 'container_deposit_management.group_container_deposit_user'
    GROUP_MANAGEMENT = 'container_deposit_management.group_container_deposit_management'
    GROUP_FINANCE = 'container_deposit_management.group_container_deposit_finance'
    GROUP_ACCOUNTING = 'container_deposit_management.group_container_deposit_accounting'
    GROUP_ADMIN = 'container_deposit_management.group_container_deposit_administrator'

    # Workflow owner per status (Cancel / Set to Draft permission).
    STATE_PERMISSION_GROUPS = {
        'draft': GROUP_USER,
        'waiting_confirm': GROUP_USER,
        'confirmed': GROUP_MANAGEMENT,
        'deposit_paid': GROUP_FINANCE,
        'waiting_settlement': GROUP_FINANCE,
        'settlement_received': GROUP_FINANCE,
        'waiting_approval': GROUP_FINANCE,
        'approved': GROUP_MANAGEMENT,
        'done': GROUP_ACCOUNTING,
        # Cancelled is final: Set to Draft is not available (button hidden).
        'cancel': GROUP_USER,
    }

    name = fields.Char(string='Internal Reference', required=True, copy=False, readonly=True, default='New')
    ftm_id = fields.Many2one('custom.declaration.import', string='FTM Reference', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_confirm', 'Waiting Confirmation'),
        ('confirmed', 'Confirmed'),
        ('deposit_paid', 'Deposit Paid'),
        ('waiting_settlement', 'Waiting Settlement'),
        ('settlement_received', 'Settlement Received'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    # Transaction currency for container deposit amounts. It intentionally
    # defaults to company currency and is no longer overwritten by the FTM currency.
    # Existing records are not migrated, preserving historical data.
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    container_vendor_id = fields.Many2one(
        'res.partner', string='Container Vendor', tracking=True,
        domain="[('is_vendor', '=', True), ('active', '=', True)]",
        help='Only partners with Vendor status (Is Vendor) can be selected.'
    )
    # Kept for historical records only; removed from the form in 16.0.1.0.17.
    # Deposit accounts are now selected per deposit line (1720002 / 1720003).
    deposit_account_id = fields.Many2one('account.account', string='Container Deposit Asset Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    landed_cost_journal_id = fields.Many2one('account.journal', string='Landed Cost Journal', domain="[('type', '=', 'general')]")

    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders', copy=False)
    picking_ids = fields.Many2many('stock.picking', string='Transfers / Receipts', copy=False)
    form_no = fields.Char(string='Form No', copy=False)
    custom_doc_number = fields.Char(string='Custom Doc Number', copy=False)
    no_awb = fields.Char(string='AWB / BL Number', copy=False)
    clearance_date = fields.Date(string='Clearance Date', copy=False)
    tax_rate_datetime = fields.Char(string='Tax Rate Date/Time', copy=False)
    currency_rate = fields.Float(string='FTM Currency Rate', digits=(12, 6), copy=False)
    total_taxable_currency = fields.Monetary(string='FTM Taxable Value Currency', currency_field='currency_id', copy=False)
    total_taxable_value = fields.Monetary(string='FTM Taxable Value Company Currency', currency_field='company_currency_id', copy=False)
    company_currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)

    deposit_line_ids = fields.One2many('import.container.deposit.line', 'deposit_id', string='Deposit / Initial Charge Lines', copy=True)
    settlement_line_ids = fields.One2many('import.container.deposit.settlement.line', 'deposit_id', string='Settlement Lines', copy=True)
    operation_line_ids = fields.One2many('import.container.deposit.operation', 'deposit_id', string='FTM Operation Lines', copy=False, readonly=True)

    deposit_amount = fields.Monetary(string='Deposit Amount', compute='_compute_amounts', store=True, currency_field='currency_id')
    initial_charge_amount = fields.Monetary(string='Initial Charge Amount', compute='_compute_amounts', store=True, currency_field='currency_id')
    refund_amount = fields.Monetary(string='Refund Amount', compute='_compute_amounts', store=True, currency_field='currency_id')
    deducted_charge_amount = fields.Monetary(string='Final Deducted / Container Charge', compute='_compute_amounts', store=True, currency_field='currency_id')
    settlement_balance = fields.Monetary(string='Settlement Balance', compute='_compute_amounts', store=True, currency_field='currency_id',
        help='Deposit amount - refund amount - final deducted charge. Should be zero before posting.')

    vendor_bill_count = fields.Integer(compute='_compute_counts')
    refund_bill_count = fields.Integer(compute='_compute_counts')
    landed_cost_count = fields.Integer(compute='_compute_counts')
    journal_entry_count = fields.Integer(compute='_compute_counts')

    all_lines_billed = fields.Boolean(
        compute='_compute_billing_status',
        help='True when every deposit line already has a Vendor Bill.')
    deposit_bills_paid = fields.Boolean(
        compute='_compute_billing_status',
        help='True when all deposit Vendor Bills are posted and paid/in payment.')
    deposit_bills_reversed = fields.Boolean(
        compute='_compute_billing_status',
        help='True when all deposit Vendor Bills are posted and fully reversed '
             '(reverse + refund paid). Hides Settlement and Set to Draft; '
             'Cancel remains available to close the document.')
    deposit_reopen_blocked = fields.Boolean(
        compute='_compute_billing_status',
        help='True when any deposit Vendor Bill is still paid/in payment/'
             'partial. Blocks Set to Draft (full reopen) and Cancel until '
             'those bills are reversed and the refund is paid '
             '(payment_state becomes reversed) or the payment is undone.')
    settlement_locked = fields.Boolean(
        readonly=True, copy=False,
        help='Set when the Settlement button is clicked again to save the '
             'entered amounts: the settlement lines become read-only until '
             'Set to Draft is used.')
    refund_bills_paid = fields.Boolean(
        compute='_compute_refund_status',
        help='True when all refund Vendor Credit Notes are posted and '
             'paid/in payment.')

    note = fields.Text(string='Internal Notes')

    @api.depends('deposit_line_ids.vendor_bill_id',
                 'deposit_line_ids.vendor_bill_id.state',
                 'deposit_line_ids.vendor_bill_id.payment_state')
    def _compute_billing_status(self):
        for rec in self:
            lines = rec.deposit_line_ids
            rec.all_lines_billed = bool(lines) and all(l.vendor_bill_id for l in lines)
            bills = lines.mapped('vendor_bill_id').filtered(lambda m: m.state != 'cancel')
            rec.deposit_bills_paid = bool(bills) and all(
                m.state == 'posted' and m.payment_state in ('paid', 'in_payment')
                for m in bills
            )
            # Reverse + refund paid → Odoo marks the bill payment_state 'reversed'.
            rec.deposit_bills_reversed = bool(bills) and all(
                m.state == 'posted' and m.payment_state == 'reversed'
                for m in bills
            )
            # Outstanding paid deposit money blocks full reopen / cancel.
            # Lifted when every bill is unpaid, cancelled, or fully reversed
            # (reverse + refund settled → payment_state 'reversed').
            rec.deposit_reopen_blocked = any(
                m.payment_state in ('paid', 'in_payment', 'partial')
                for m in bills
            )

    @api.depends('settlement_line_ids.refund_bill_id',
                 'settlement_line_ids.refund_bill_id.state',
                 'settlement_line_ids.refund_bill_id.payment_state')
    def _compute_refund_status(self):
        for rec in self:
            bills = rec.settlement_line_ids.mapped('refund_bill_id').filtered(
                lambda m: m.state != 'cancel')
            rec.refund_bills_paid = bool(bills) and all(
                m.state == 'posted' and m.payment_state in ('paid', 'in_payment', 'reversed')
                for m in bills
            )

    def _get_default_landed_cost_journal(self, company=None):
        """Return the configured Landed Cost Journal for the company."""
        company = company or self.env.company
        return self.env['account.journal'].search([
            ('name', '=', 'Landed Cost Journal'),
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
        ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        # Do not rely only on @api.onchange for FTM information. Readonly values
        # populated by onchange can be omitted by the web client when saving.
        # Populate them again server-side so they are always persisted.
        prepared_vals_list = []
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('import.container.deposit') or 'New'
            if vals.get('ftm_id'):
                ftm = self.env['custom.declaration.import'].browse(vals['ftm_id']).exists()
                if ftm:
                    vals.update(self._prepare_ftm_sync_vals(ftm))
                    company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
                    default_journal = self._get_default_landed_cost_journal(company)
                    if default_journal:
                        vals['landed_cost_journal_id'] = default_journal.id
            prepared_vals_list.append(vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        # Re-synchronise only when the selected FTM is changed. This keeps the
        # FTM snapshot persistent without overwriting later manual adjustments
        # on every normal save.
        if 'ftm_id' in vals:
            vals = dict(vals)
            if vals.get('ftm_id'):
                ftm = self.env['custom.declaration.import'].browse(vals['ftm_id']).exists()
                if ftm:
                    vals.update(self._prepare_ftm_sync_vals(ftm))
                    company = self.company_id if len(self) == 1 and self.company_id else self.env.company
                    default_journal = self._get_default_landed_cost_journal(company)
                    if default_journal:
                        vals['landed_cost_journal_id'] = default_journal.id
            else:
                vals.update(self._empty_ftm_sync_vals())
        return super().write(vals)


    def _empty_ftm_sync_vals(self):
        return {
            'purchase_order_ids': [(5, 0, 0)],
            'picking_ids': [(5, 0, 0)],
            'form_no': False,
            'custom_doc_number': False,
            'no_awb': False,
            'clearance_date': False,
            'tax_rate_datetime': False,
            'currency_rate': 0.0,
            'total_taxable_currency': 0.0,
            'total_taxable_value': 0.0,
            'operation_line_ids': [(5, 0, 0)],
        }

    def _prepare_ftm_sync_vals(self, ftm):
        ftm = ftm or self.env['custom.declaration.import']
        purchase_orders = ftm.purchase_order_ids or self.env['purchase.order']
        pickings = ftm.stock_picking_ids or self.env['stock.picking']
        operation_commands:list[tuple[int, int, dict|int]] = [fields.Command.clear()]
        ftm_lines = ftm.custom_declaration_line_ids or self.env['custom.declaration.line']
        for line in ftm_lines:
            operation_vals = {
                'product_id': line.product_id.id if 'product_id' in line._fields and line.product_id else False,
                'qty': line.qty if 'qty' in line._fields else 0.0,
                'product_uom_id': line.product_uom.id if 'product_uom' in line._fields and line.product_uom else False,
                'currency_id': line.currency_id.id if 'currency_id' in line._fields and line.currency_id else False,
                'total_cost_currency': line.total_cost_currency if 'total_cost_currency' in line._fields else 0.0,
                'extra_expense_currency': line.extra_expense_currency if 'extra_expense_currency' in line._fields else 0.0,
                'purchase_order_id': line.purchase_order_id.id if 'purchase_order_id' in line._fields and line.purchase_order_id else False,
            }
            operation_commands.append(fields.Command.create(operation_vals))

        return {
            'purchase_order_ids': [(6, 0, purchase_orders.ids)],
            'container_vendor_id': ftm.vendor_id.id,
            'picking_ids': [(6, 0, pickings.ids)],
            'form_no': ftm.form_no or False,
            'custom_doc_number': ftm.number or False,
            'no_awb': ftm.no_awb or False,
            'clearance_date': ftm.clearance_date or False,
            'currency_rate': ftm.currency_rate or 0.0,
            'total_taxable_currency': ftm.total_cost_currency or 0.0,
            'total_taxable_value': ftm.total_cost or 0.0,
            'operation_line_ids': operation_commands,
        }

    @api.depends('deposit_line_ids.amount', 'deposit_line_ids.line_type',
                 'settlement_line_ids.refund_amount', 'settlement_line_ids.charge_amount')
    def _compute_amounts(self):
        for rec in self:
            # Line Type column was removed from the UI; all deposit lines are
            # treated as refundable deposit amounts.
            deposit_lines = rec.deposit_line_ids.filtered(lambda l: l.line_type != 'initial_charge')
            rec.deposit_amount = sum(deposit_lines.mapped('amount'))
            rec.initial_charge_amount = sum(rec.deposit_line_ids.filtered(lambda l: l.line_type == 'initial_charge').mapped('amount'))
            rec.refund_amount = sum(rec.settlement_line_ids.mapped('refund_amount'))
            rec.deducted_charge_amount = sum(rec.settlement_line_ids.mapped('charge_amount'))
            rec.settlement_balance = rec.deposit_amount - rec.refund_amount - rec.deducted_charge_amount

    def _compute_counts(self):
        for rec in self:
            bills = rec.deposit_line_ids.mapped('vendor_bill_id')
            refunds = rec.settlement_line_ids.mapped('refund_bill_id')
            costs = rec.settlement_line_ids.mapped('landed_cost_id')
            entries = rec.settlement_line_ids.mapped('journal_entry_id')
            rec.vendor_bill_count = len(bills)
            rec.refund_bill_count = len(refunds)
            rec.landed_cost_count = len(costs)
            rec.journal_entry_count = len(entries)

    @api.onchange('ftm_id')
    def _onchange_ftm_id(self):
        for rec in self:
            if not rec.ftm_id:
                rec.update(rec._empty_ftm_sync_vals())
                continue
            rec.update(rec._prepare_ftm_sync_vals(rec.ftm_id))
            default_journal = rec._get_default_landed_cost_journal(rec.company_id or rec.env.company)
            rec.landed_cost_journal_id = default_journal

    def _is_administrator(self):
        return (
            self.env.su
            or self.env.user.has_group(self.GROUP_ADMIN)
            or self.env.user.has_group('base.group_system')
        )

    def _check_group(self, xmlid, action_label):
        if self._is_administrator():
            return
        if not self.env.user.has_group(xmlid):
            raise UserError(_('You are not allowed to %(action)s this Container Deposit document.') % {
                'action': action_label,
            })

    def _check_state_permission(self, action_label):
        """Enforce workflow permission per current status (see permission matrix)."""
        if self._is_administrator():
            return
        for rec in self:
            required_group = rec.STATE_PERMISSION_GROUPS.get(rec.state)
            if required_group and not self.env.user.has_group(required_group):
                state_label = dict(rec._fields['state'].selection).get(rec.state, rec.state) #type: ignore
                raise UserError(_(
                    'You are not allowed to %(action)s this document while it is in '
                    'status "%(state)s".'
                ) % {'action': action_label, 'state': state_label})

    def action_submit(self):
        self._check_group(self.GROUP_USER, _('submit'))
        for rec in self:
            if not rec.deposit_line_ids:
                raise UserError(_('Please input at least one deposit/initial charge line.'))
            rec.write({'state': 'waiting_confirm'})

    def action_confirm(self):
        self._check_group(self.GROUP_MANAGEMENT, _('confirm'))
        for rec in self:
            vals = {'state': 'confirmed'}
            if rec.ftm_id:
                vals.update(rec._prepare_ftm_sync_vals(rec.ftm_id))
            rec.write(vals)

    def action_print_container_deposit(self):
        self.ensure_one()
        return self.env.ref('container_deposit_management.action_report_container_deposit').report_action(self)

    def _has_inventory_affecting_documents(self):
        """True when a validated landed cost already changed product valuation."""
        self.ensure_one()
        return bool(self.settlement_line_ids.mapped('landed_cost_id').filtered(lambda lc: lc.state == 'done'))

    def _get_deposit_vendor_bills(self):
        """Active (non-cancelled) vendor bills linked to deposit lines."""
        self.ensure_one()
        return self.deposit_line_ids.mapped('vendor_bill_id').filtered(
            lambda m: m.exists() and m.state != 'cancel')

    def _check_deposit_reopen_allowed(self, action_label):
        """Block full reopen/cancel while deposit bills are still paid.

        Allowed again after each deposit vendor bill is reversed and the
        refund is paid (payment_state 'reversed'), or the payment is undone
        so the bill is no longer paid/in_payment/partial.
        """
        for rec in self:
            bills = rec._get_deposit_vendor_bills()
            blocking = bills.filtered(
                lambda m: m.payment_state in ('paid', 'in_payment', 'partial'))
            if not blocking:
                continue
            raise UserError(_(
                'Cannot %(action)s %(name)s because the following deposit '
                'Vendor Bill(s) are still Paid (or partially paid):\n%(bills)s\n\n'
                'Reverse the deposit vendor bill(s) and complete the refund '
                'payment first (bill payment status must become Reversed). '
                'The block is then lifted for Set to Draft / Cancel.'
            ) % {
                'action': action_label,
                'name': rec.display_name,
                'bills': '\n'.join(
                    '- %s (%s)' % (
                        m.name if m.name and m.name != '/' else m.display_name,
                        m.payment_state,
                    )
                    for m in blocking
                ),
            })

    def _is_settlement_unlock_set_to_draft(self):
        """True when Set to Draft only unlocks settlement (deposit stays paid)."""
        self.ensure_one()
        return self.deposit_bills_paid and self.state in self.SETTLEMENT_RESET_STATES

    def _cancel_related_accounting_documents(self):
        """Cancel draft/posted related docs that do not change inventory valuation.

        Updates Action Toolbar (smart buttons) by unlinking cancelled documents
        from deposit/settlement lines after a successful cancel.
        """
        AccountMove = self.env['account.move']
        for rec in self:
            if rec._has_inventory_affecting_documents():
                raise UserError(_(
                    'Cannot cancel or set to draft %(name)s because a validated '
                    'FTM Landed Cost already changed inventory/product valuation.\n'
                    'Reverse the landed cost first if this document must be reopened.'
                ) % {'name': rec.display_name})

            vendor_bills = rec.deposit_line_ids.mapped('vendor_bill_id').exists()
            refund_bills = rec.settlement_line_ids.mapped('refund_bill_id').exists()
            journal_entries = rec.settlement_line_ids.mapped('journal_entry_id').exists()
            moves = (vendor_bills | refund_bills | journal_entries).filtered(lambda m: m.state != 'cancel')

            # Paid deposit bills: kept as-is during settlement unlock (Set to
            # Draft from waiting settlement onward). Full reopen / Cancel is
            # blocked earlier by _check_deposit_reopen_allowed while they remain
            # paid.
            paid_deposit_bills = vendor_bills.filtered(
                lambda m: m.state != 'cancel'
                and m.payment_state in ('paid', 'in_payment', 'partial'))
            # Fully reversed deposit bills (reverse + refund paid): do not call
            # button_draft/cancel on them; just unlink so the CDM can be reopened.
            reversed_deposit_bills = vendor_bills.filtered(
                lambda m: m.state != 'cancel' and m.payment_state == 'reversed')

            for move in moves - paid_deposit_bills - reversed_deposit_bills:
                if move.payment_state in ('paid', 'in_payment', 'partial'):
                    raise UserError(_(
                        'Cannot cancel or set to draft because settlement '
                        'document %(move)s is already paid/partially paid.\n'
                        'Cancel its payment first.'
                    ) % {'move': move.display_name})
                if move.state == 'posted':
                    move.button_draft()
                if move.state == 'draft':
                    move.button_cancel()

            landed_costs = rec.settlement_line_ids.mapped('landed_cost_id').exists()
            for cost in landed_costs:
                if cost.state == 'done':
                    raise UserError(_(
                        'Cannot cancel or set to draft because landed cost %(cost)s '
                        'is already validated and affects inventory valuation.'
                    ) % {'cost': cost.display_name})
                if cost.state == 'draft' and hasattr(cost, 'button_cancel'):
                    cost.button_cancel()
                elif cost.state != 'cancel':
                    cost.write({'state': 'cancel'})

            # Clear links so Action Toolbar counts refresh immediately.
            # Paid deposit bills stay linked during settlement unlock.
            # Reversed deposit bills are unlinked so Create Deposit Bill can
            # run again after a full reopen.
            rec.deposit_line_ids.filtered(
                lambda l: l.vendor_bill_id and l.vendor_bill_id not in paid_deposit_bills
            ).write({'vendor_bill_id': False})
            rec.settlement_line_ids.write({
                'refund_bill_id': False,
                'landed_cost_id': False,
                'journal_entry_id': False,
            })

            # Drop leftover cancelled moves that were created only for this CDM.
            orphan_moves = AccountMove.search([
                ('container_deposit_id', '=', rec.id),
                ('state', '=', 'cancel'),
            ])
            if orphan_moves:
                orphan_moves.write({'container_deposit_id': False})

    # Once the deposit bills are paid, "Set to Draft" from these stages returns
    # to Waiting Settlement (not Draft): the deposit itself can no longer be
    # changed, only the settlement needs to be corrected/redone.
    SETTLEMENT_RESET_STATES = (
        'waiting_settlement', 'settlement_received', 'waiting_approval',
        'approved', 'done',
    )

    def action_set_to_draft(self):
        self._check_state_permission(_('set to draft'))
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_(
                    'Cancelled documents cannot be set to draft. '
                    'Create a new Container Deposit if needed.'
                ))
            if rec.deposit_bills_reversed:
                raise UserError(_(
                    'Cannot set to draft %(name)s because the deposit Vendor '
                    'Bill(s) are already Reversed and the refund is paid.\n'
                    'Settlement and Set to Draft are not available. Use Cancel '
                    'to close this document, or create a new Container Deposit.'
                ) % {'name': rec.display_name})
            # Settlement unlock (paid deposit, waiting settlement+) stays allowed.
            # Full reopen to Draft is blocked while deposit bills are Paid.
            if not rec._is_settlement_unlock_set_to_draft():
                rec._check_deposit_reopen_allowed(_('set to draft'))
            rec._cancel_related_accounting_documents()
            if rec.deposit_bills_paid and rec.state in self.SETTLEMENT_RESET_STATES:
                rec.write({'state': 'waiting_settlement', 'settlement_locked': False})
            else:
                rec.write({'state': 'draft', 'settlement_locked': False})

    def action_mark_deposit_paid(self):
        self._check_group(self.GROUP_FINANCE, _('mark deposit paid'))
        for rec in self:
            all_payment_state_is_paid = all(state == 'paid' for state in rec.deposit_line_ids.mapped('vendor_bill_id.payment_state'))
            if not all_payment_state_is_paid:
                raise UserError("You need to ensure all bills are paid!")
            if rec.deposit_amount <= 0:
                raise UserError(_('Deposit amount must be greater than zero.'))
            bills = rec.deposit_line_ids.mapped('vendor_bill_id').filtered(lambda m: m.state != 'cancel')
            if not bills:
                raise UserError(_(
                    'Please create the Deposit Bill and register its payment '
                    'before marking the deposit as paid.'))
            unpaid = bills.filtered(
                lambda m: m.state != 'posted' or m.payment_state not in ('paid', 'in_payment'))
            if unpaid:
                raise UserError(_(
                    'The following Vendor Bills are not fully paid yet:\n%s\n\n'
                    'Post and register payment for all deposit bills before '
                    'marking the deposit as paid.'
                ) % '\n'.join('- %s' % (m.name if m.name and m.name != '/' else m.display_name) for m in unpaid))
            rec.write({'state': 'deposit_paid'})

    def action_start_settlement(self):
        """Settlement button: generate settlement lines (readonly source columns).

        Landed Cost Product / Charge and Charge Account are auto-filled from the
        corresponding data table:
        * Uang Muka Jaminan Sewa Container -> Biaya Sewa Container (Demurrage) -> 6130006
        * Uang Muka Jaminan Container -> Biaya Perbaikan dan Kebersihan Container -> 6130016
        """
        self._check_group(self.GROUP_FINANCE, _('start settlement'))
        SettlementLine = self.env['import.container.deposit.settlement.line']
        for rec in self:
            if rec.deposit_bills_reversed:
                raise UserError(_(
                    'Cannot start settlement on %(name)s because the deposit '
                    'Vendor Bill(s) are Reversed and the refund is paid.\n'
                    'Settlement is only available while deposit bills remain Paid.'
                ) % {'name': rec.display_name})
            if not rec.deposit_bills_paid:
                raise UserError(_(
                    'Cannot start settlement on %(name)s because the deposit '
                    'Vendor Bill(s) are not fully paid.\n'
                    'Post and register payment for all deposit bills first.'
                ) % {'name': rec.display_name})
            if not rec.settlement_line_ids:
                vals = []
                for line in rec.deposit_line_ids.filtered(lambda l: l.line_type == 'deposit'):
                    # Resolve the corresponding landed-cost charge product for
                    # the deposit product (Uang Muka Jaminan...) via the mapping
                    # table. Deposit products themselves are asset products, not
                    # landed-cost products.
                    mapping = SettlementLine._get_charge_mapping_for_deposit_product(line.product_id)
                    charge_product = (
                        SettlementLine._find_landed_cost_product(mapping['charge_tokens'])
                        if mapping else self.env['product.product']
                    )
                    if not charge_product and line.product_id.landed_cost_ok:
                        charge_product = line.product_id
                    charge_account = (
                        SettlementLine._get_charge_account_for_product(charge_product, rec.company_id)
                        if charge_product else self.env['account.account']
                    )
                    vals.append((0, 0, {
                        'source_deposit_line_id': line.id,
                        'product_id': charge_product.id if charge_product else False,
                        'name': (charge_product.display_name if charge_product
                                 else (line.product_id.display_name if line.product_id else False)),
                        'container_vendor_id': line.vendor_id.id,
                        'original_deposit_amount': line.amount,
                        'refund_amount': 0.0,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'charge_amount': line.amount,
                        'split_method': 'by_current_cost_price',
                        'charge_account_id': charge_account.id if charge_account else False,
                    }))
                rec.write({'settlement_line_ids': vals})
                # First click: open the settlement for input.
                rec.write({'state': 'waiting_settlement', 'settlement_locked': False})
            else:
                # Second click acts as Save: lock the entered amounts.
                # Only Set to Draft unlocks them again.
                rec.write({'state': 'waiting_settlement', 'settlement_locked': True})

    def action_settlement_received(self):
        self._check_group(self.GROUP_FINANCE, _('mark settlement received'))
        for rec in self:
            if not rec.settlement_line_ids:
                raise UserError(_('Please input settlement lines first.'))
            if any(l.refund_amount < 0 or l.charge_amount < 0 for l in rec.settlement_line_ids):
                raise UserError(_('Refund amount and charge amount cannot be negative.'))
            rec.write({'state': 'settlement_received', 'settlement_locked': True})

    def action_request_approval(self):
        self._check_group(self.GROUP_FINANCE, _('request approval'))
        for rec in self:
            if round(rec.settlement_balance, 2) != 0.0:
                raise UserError(_('Settlement balance must be zero before approval. Current balance: %s') % rec.settlement_balance)
            rec.write({'state': 'waiting_approval'})

    def action_approve(self):
        self._check_group(self.GROUP_MANAGEMENT, _('approve'))
        self.write({'state': 'approved'})

    def action_posted(self):
        """Posted and Done are one step: posting finishes the process."""
        self._check_group(self.GROUP_ACCOUNTING, _('mark posted'))
        for rec in self:
            if rec.deducted_charge_amount and not rec.landed_cost_count:
                raise UserError(_('Please create FTM landed cost before marking as Posted.'))
            rec.write({'state': 'done'})

    def action_cancel(self):
        self._check_state_permission(_('cancel'))
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_('This document is already cancelled.'))
            # Paid deposit bills block Cancel until reversed + refund paid.
            rec._check_deposit_reopen_allowed(_('cancel'))
            rec._cancel_related_accounting_documents()
            rec.write({'state': 'cancel'})

    def action_create_deposit_bill(self):
        self.ensure_one()
        self._check_group(self.GROUP_FINANCE, _('create deposit bill'))
        lines = self.deposit_line_ids.filtered(lambda l: not l.vendor_bill_id)
        if not lines:
            raise UserError(_('No unbilled deposit/initial charge line.'))
        vendors = lines.mapped('vendor_id')
        created = self.env['account.move']
        for vendor in vendors:
            vlines = lines.filtered(lambda l: l.vendor_id == vendor)
            invoice_lines = []
            for line in vlines:
                account = line.account_id or line.product_id.property_account_expense_id or line.product_id.categ_id.property_account_expense_categ_id
                if not account:
                    raise UserError(_('Please set Deposit Account for line/product %s.') % line.display_name)
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name or line.product_id.display_name,
                    'quantity': 1.0,
                    'price_unit': line.amount,
                    'account_id': account.id,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'is_landed_costs_line': False,
                }))
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                # Always keep the accounting entry name unassigned while draft.
                # Some custom account.move defaults may otherwise copy a source
                # reference into name and collide with an existing journal entry.
                'name': '/',
                'partner_id': vendor.id,
                'currency_id': self.company_currency_id.id,
                'invoice_date': fields.Date.context_today(self),
                'ref': self.name,
                'invoice_line_ids': invoice_lines,
                'container_deposit_id': self.id,
            })
            created |= move
            for line in vlines:
                line.vendor_bill_id = move.id
        return self._open_moves(created, _('Vendor Bill Created'))

    def action_create_refund_credit_note(self):
        self.ensure_one()
        self._check_group(self.GROUP_ACCOUNTING, _('create refund credit note'))
        lines = self.settlement_line_ids.filtered(lambda l: l.refund_amount > 0 and not l.refund_bill_id)
        if not lines:
            raise UserError(_('No settlement refund line to create vendor credit note.'))
        vendors = lines.mapped('container_vendor_id')
        created = self.env['account.move']
        for vendor in vendors:
            vlines = lines.filtered(lambda l: l.container_vendor_id == vendor)
            invoice_lines = []
            for line in vlines:
                account = line.source_deposit_line_id.account_id
                if not account:
                    raise UserError(_(
                        'Please set Deposit Account on the source deposit line before creating the refund credit note.'
                    ))
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': _('Refund container deposit - %s') % (line.product_id.display_name or ''),
                    'quantity': 1.0,
                    'price_unit': line.refund_amount,
                    'account_id': account.id,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                }))
            move = self.env['account.move'].create({
                'move_type': 'in_refund',
                'name': '/',
                'partner_id': vendor.id,
                'currency_id': self.company_currency_id.id,
                'invoice_date': fields.Date.context_today(self),
                'ref': self.name,
                'invoice_line_ids': invoice_lines,
                'container_deposit_id': self.id,
            })
            created |= move
            for line in vlines:
                line.refund_bill_id = move.id
        return self._open_moves(created, _('Vendor Credit Note Created'))

    def action_create_ftm_landed_cost(self):
        self.ensure_one()
        self._check_group(self.GROUP_ACCOUNTING, _('create FTM landed cost'))
        if not self.picking_ids:
            raise UserError(_('No receipt/transfer linked from FTM. Cannot create landed cost.'))
        lines = self.settlement_line_ids.filtered(lambda l: l.charge_amount > 0 and not l.landed_cost_id)
        if not lines:
            raise UserError(_('No final container charge line to create landed cost.'))
        cost_lines = []
        for line in lines:
            product = line.product_id
            if not product:
                raise UserError(_(
                    'Settlement line "%s" has a Final Deduction but no Landed Cost Product. '
                    'Select a charge product with Landed Cost enabled '
                    '(for example Biaya Sewa Container / Detention / Demurrage), '
                    'not the Uang Muka Jaminan deposit product.'
                ) % (line.name or line.source_deposit_line_id.display_name or line.id))
            if not product.landed_cost_ok:
                raise UserError(_(
                    'Product %s must have Landed Cost enabled.\n\n'
                    'Do not enable Landed Cost on Uang Muka Jaminan products. '
                    'On the settlement line, change Landed Cost Product / Charge to a '
                    'real container-charge product (Is a Landed Cost = True), '
                    'for example "Biaya Sewa Container (THC)" or create a new '
                    'service product with Purchase + Landed Cost enabled.'
                ) % product.display_name)
            account = line.charge_account_id or product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
            cost_lines.append((0, 0, {
                'name': line.name or product.display_name,
                'product_id': product.id,
                'price_unit': line.charge_amount,
                'split_method': line.split_method,
                'account_id': account.id if account else False,
            }))
        LandedCost = self.env['stock.landed.cost']
        vendor_bills = lines.mapped('source_deposit_line_id.vendor_bill_id')
        landed_cost_vals = {
            'date': fields.Date.context_today(self),
            'account_journal_id': self.landed_cost_journal_id.id if self.landed_cost_journal_id else False,
            'picking_ids': [(6, 0, self.picking_ids.ids)],
            'cost_lines': cost_lines,
            'container_deposit_id': self.id,
        }
        # Link the landed cost back to the FTM. The existing custom-report
        # fields then derive Purchase Orders, Vendor and Custom Doc. Number
        # from this declaration.
        if 'custom_declaration_import_id' in LandedCost._fields:
            landed_cost_vals['custom_declaration_import_id'] = self.ftm_id.id
        # Standard Odoo supports one primary Vendor Bill. Keep the first bill
        # as the primary reference and, when the database customisation is
        # available, retain every related deposit bill in Bill Cost.
        if vendor_bills and 'vendor_bill_id' in LandedCost._fields:
            landed_cost_vals['vendor_bill_id'] = vendor_bills[0].id
        if vendor_bills and 'vendor_bill_ids' in LandedCost._fields:
            landed_cost_vals['vendor_bill_ids'] = [(6, 0, vendor_bills.ids)]
        landed_cost = LandedCost.create(landed_cost_vals)
        for line in lines:
            line.landed_cost_id = landed_cost.id
        return {
            'name': _('FTM Landed Cost'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.landed.cost',
            'view_mode': 'form',
            'res_id': landed_cost.id,
            'target': 'current',
        }

    def _open_moves(self, moves, title):
        action = self.env.ref('account.action_move_in_invoice_type')
        # CDM variant of the invoice form: no STTF buttons, single Reset to Draft.
        if len(moves) == 1:
            action.update({'name': title, 'view_mode': 'form', 'res_id': moves.id})
        else:
            # Restricted list: no New/Upload/Create Landed Costs, Register
            # Payment highlighted. Bills must be created from the CDM document.
            tree = self.env.ref('container_deposit_management.view_cdm_deposit_bill_tree')
            action.update({
                'name': title,
                'domain': f"[('id', 'in', {moves.ids})]",
                'view_mode': 'tree,form',
                'view_id': tree.id
            })
        return action.read()[0]

    def action_view_vendor_bills(self):
        self.ensure_one()
        return self._open_moves(self.deposit_line_ids.mapped('vendor_bill_id'), _('Vendor Bills'))

    def action_view_refund_bills(self):
        self.ensure_one()
        return self._open_moves(self.settlement_line_ids.mapped('refund_bill_id'), _('Vendor Credit Notes'))

    def action_view_landed_costs(self):
        self.ensure_one()
        costs = self.settlement_line_ids.mapped('landed_cost_id')
        action = self.env['ir.actions.actions']._for_xml_id('stock_landed_costs.action_stock_landed_cost')
        action['domain'] = [('id', 'in', costs.ids)]
        return action

    def action_view_journal_entries(self):
        self.ensure_one()
        entries = self.settlement_line_ids.mapped('journal_entry_id')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [('id', 'in', entries.ids)]
        return action


class ImportContainerDepositLine(models.Model):
    _name = 'import.container.deposit.line'
    _description = 'Import Container Deposit Initial Line'
    _order = 'sequence, id'

    deposit_id = fields.Many2one('import.container.deposit', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    parent_state = fields.Selection(related='deposit_id.state', store=True)
    currency_id = fields.Many2one(related='deposit_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one(related='deposit_id.company_id', store=True, readonly=True)
    line_type = fields.Selection([
        ('deposit', 'Refundable Container Deposit'),
        ('initial_charge', 'Initial Non-refundable Container Charge'),
    ], default='deposit', required=True)
    # Approved deposit products and their account codes
    # (1720002 / 1720003 under 1720 Uang Muka Pembelian).
    DEPOSIT_PRODUCT_ACCOUNT_MAP = (
        {
            'codes': ('1720003',),
            'product_tokens': (
                'uang muka jaminan sewa container',
                'uang muka jaminan sewa kontainer',
            ),
            'account_names': (
                'uang muka jaminan sewa container',
                'uang muka jaminan sewa kontainer',
            ),
        },
        {
            'codes': ('1720002',),
            'product_tokens': (
                'uang muka jaminan container',
                'uang muka jaminan kontainer',
            ),
            'account_names': (
                'uang muka jaminan container',
                'uang muka jaminan kontainer',
            ),
        },
    )
    APPROVED_DEPOSIT_PRODUCT_NAMES = (
        'Uang Muka Jaminan Container',
        'Uang Muka Jaminan Sewa Container',
        'Uang Muka Jaminan Kontainer',
        'Uang Muka Jaminan Sewa Kontainer',
    )
    APPROVED_DEPOSIT_ACCOUNT_CODES = ('1720002', '1720003')

    @api.model
    def _deposit_product_match_text(self, product):
        """Build a casefold search string from product name(s) and default code."""
        product = product or self.env['product.product']
        if not product:
            return ''
        parts = []
        for lang in (self.env.context.get('lang'), 'en_US', 'id_ID'):
            if not lang:
                continue
            name = product.with_context(lang=lang).name
            if name:
                parts.append(name.strip().casefold())
        if product.name:
            parts.append((product.name or '').strip().casefold())
        default_code = (product.default_code or '').strip().casefold()
        return f'{default_code} {" ".join(dict.fromkeys(parts))}'

    @api.model
    def _is_approved_deposit_product(self, product):
        """Approved deposit product (Container/Kontainer spelling, any locale)."""
        if not product:
            return False
        if (product.name or '').strip() in self.APPROVED_DEPOSIT_PRODUCT_NAMES:
            return True
        combined = self._deposit_product_match_text(product)
        return any(
            any(token in combined for token in mapping['product_tokens'])
            for mapping in self.DEPOSIT_PRODUCT_ACCOUNT_MAP
        )

    @api.model
    def _get_approved_deposit_product_ids(self):
        """Return IDs for the two approved deposit products.

        Do not rely on [('name', 'in', ...)] in domains: on this database
        product names are stored as translated JSONB and the SQL domain can
        return only one of the two approved products in the dropdown.
        """
        Product = self.env['product.product'].sudo()
        candidates = Product.search([
            ('purchase_ok', '=', True),
            ('active', '=', True),
        ])
        approved = candidates.filtered(lambda p: self._is_approved_deposit_product(p))
        if len(approved) >= len(self.APPROVED_DEPOSIT_PRODUCT_NAMES):
            return approved.ids

        # JSONB fallback when ORM name reads differ from stored translation.
        names = list(self.APPROVED_DEPOSIT_PRODUCT_NAMES)
        self.env.cr.execute("""
            SELECT pp.id
              FROM product_product pp
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE pt.active = TRUE
               AND pt.purchase_ok = TRUE
               AND (
                    pt.name->>'en_US' = ANY(%s)
                 OR btrim(pt.name::text, '"') = ANY(%s)
               )
             ORDER BY pp.id
        """, (names, names))
        return [row[0] for row in self.env.cr.fetchall()]

    @api.model
    def _approved_deposit_product_domain(self):
        return [('id', 'in', self._get_approved_deposit_product_ids())]

    @api.model
    def _get_approved_deposit_account_ids(self, company=None):
        """Return account.account IDs for 1720002 and 1720003."""
        company = company or self.env.company
        company_id = company.id
        Account = self.env['account.account'].sudo()
        account_ids = []
        for code in self.APPROVED_DEPOSIT_ACCOUNT_CODES:
            self.env.cr.execute("""
                SELECT id
                  FROM account_account
                 WHERE regexp_replace(COALESCE(code, ''), '[^0-9]', '', 'g') = %s
                 ORDER BY CASE WHEN COALESCE(deprecated, FALSE) THEN 1 ELSE 0 END,
                          CASE WHEN company_id = %s THEN 0 ELSE 1 END,
                          company_id NULLS LAST,
                          id
                 LIMIT 1
            """, (code, company_id))
            row = self.env.cr.fetchone()
            if row:
                account_ids.append(row[0])
        return account_ids

    def _approved_deposit_account_domain(self):
        company = self.company_id or self.env.company
        return [('id', 'in', self._get_approved_deposit_account_ids(company))]

    product_id = fields.Many2one(
        'product.product', string='Product / Charge', required=True,
        domain=lambda self: self._approved_deposit_product_domain(),
        help='Limited to Uang Muka Jaminan Container and Uang Muka Jaminan Sewa Container.'
    )
    name = fields.Char(string='Description')
    vendor_id = fields.Many2one(
        'res.partner', string='Vendor', required=True,
        domain="[('is_vendor', '=', True), ('active', '=', True)]",
        help='Only partners with Vendor status (Is Vendor) can be selected.'
    )
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'purchase')])
    account_id = fields.Many2one(
        'account.account', string='Deposit Account', store=True, required=True,
        domain=lambda self: self._approved_deposit_account_domain(),
        help='Deposit account selection limited to: '
             '1720002 Uang Muka Jaminan Container and '
             '1720003 Uang Muka Jaminan Sewa Container. '
             'Auto-filled from Product / Charge.'
    )
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True, copy=False)
    note = fields.Char(string='Note')

    @api.model
    def _normalise_account_code(self, value):
        return ''.join(ch for ch in (value or '') if ch.isdigit())

    @api.model
    def _resolve_deposit_product_mapping(self, product):
        """Return (account_codes, expected_account_names) for a deposit product."""
        product = product or self.env['product.product']
        product_name = (product.name or '').strip()
        if product_name == 'Uang Muka Jaminan Sewa Container':
            return ('1720003',), ('uang muka jaminan sewa container', 'uang muka jaminan sewa kontainer')
        if product_name == 'Uang Muka Jaminan Sewa Kontainer':
            return ('1720003',), ('uang muka jaminan sewa kontainer', 'uang muka jaminan sewa container')
        if product_name == 'Uang Muka Jaminan Container':
            return ('1720002',), ('uang muka jaminan container', 'uang muka jaminan kontainer')
        if product_name == 'Uang Muka Jaminan Kontainer':
            return ('1720002',), ('uang muka jaminan kontainer', 'uang muka jaminan container')

        combined = self._deposit_product_match_text(product)
        for mapping in self.DEPOSIT_PRODUCT_ACCOUNT_MAP:
            if any(token in combined for token in mapping['product_tokens']):
                return mapping['codes'], mapping['account_names']
        return (), ()

    def _get_product_deposit_account(self, product=None, company=None):
        """Return the configured deposit account for a deposit product.

        Mapping:
        * Uang Muka Jaminan Container -> 1720002
        * Uang Muka Jaminan Sewa Container -> 1720003
        """
        product = product or self.product_id
        company = company or self.deposit_id.company_id or self.company_id or self.env.company
        Account = self.env['account.account']
        if not product:
            return Account

        account_codes, expected_names = self._resolve_deposit_product_mapping(product)
        if not account_codes:
            return Account

        company_id = company.id or self.env.company.id

        # 1. Prefer an explicitly configured product/category expense account
        # when it is the required mapped account (company-aware).
        property_candidates = (
            product.with_company(company).property_account_expense_id,
            product.categ_id.with_company(company).property_account_expense_categ_id,
        )
        for candidate in property_candidates:
            if candidate and self._normalise_account_code(candidate.code) in account_codes:
                return candidate

        # 2. Deterministic code-only lookup among the two approved deposit accounts.
        self.env.cr.execute("""
            SELECT id
              FROM account_account
             WHERE regexp_replace(COALESCE(code, ''), '[^0-9]', '', 'g') = ANY(%s)
             ORDER BY CASE WHEN COALESCE(deprecated, FALSE) THEN 1 ELSE 0 END,
                      CASE WHEN company_id = %s THEN 0 ELSE 1 END,
                      company_id NULLS LAST,
                      id
             LIMIT 1
        """, (list(account_codes), company_id))
        row = self.env.cr.fetchone()
        if row:
            account = Account.sudo().browse(row[0]).exists()
            if account:
                return account

        # 3. ORM fallback by translated name.
        GlobalAccount = Account.sudo().with_context(active_test=False)
        for expected_name in expected_names:
            named = GlobalAccount.search([
                ('name', '=ilike', expected_name),
            ], order='id')
            if not named:
                continue
            preferred = named.filtered(lambda rec: not rec.deprecated)
            pool = preferred or named
            account = (
                pool.filtered(lambda rec: rec.company_id.id == company_id)[:1]
                or pool[:1]
            )
            if account:
                return account

        return Account

    def _required_account_code_for_product(self, product):
        codes, _names = self._resolve_deposit_product_mapping(product)
        return ' / '.join(codes) if codes else '1720002'

    @api.onchange('product_id', 'deposit_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                company = (line.deposit_id.company_id or line.company_id or line.env.company)
                line.account_id = line._get_product_deposit_account(
                    product=line.product_id, company=company
                )
            else:
                line.account_id = False

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        Product = self.env['product.product']
        Deposit = self.env['import.container.deposit']
        for incoming in vals_list:
            vals = dict(incoming)
            product = Product.browse(vals.get('product_id')).exists() if vals.get('product_id') else Product
            deposit = Deposit.browse(vals.get('deposit_id')).exists() if vals.get('deposit_id') else Deposit
            company = deposit.company_id if deposit else self.env.company
            if product:
                account = self._get_product_deposit_account(product=product, company=company)
                if not account:
                    raise ValidationError(_(
                        'Account %(code)s required for product %(product)s was not found '
                        'in company %(company)s. Please create/activate that account first.'
                    ) % {
                        'code': self._required_account_code_for_product(product),
                        'product': product.display_name,
                        'company': company.display_name,
                    })
                vals['account_id'] = account.id
                vals.setdefault('name', product.display_name)
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        vals = dict(vals)
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals.get('product_id')).exists()
            if product:
                # Records in one write may theoretically belong to different
                # companies, so update each line with its own company mapping.
                for line in self:
                    account = line._get_product_deposit_account(product=product)
                    if not account:
                        raise ValidationError(_(
                            'Account %(code)s required for product %(product)s was not found '
                            'in company %(company)s.'
                        ) % {
                            'code': line._required_account_code_for_product(product),
                            'product': product.display_name,
                            'company': (line.company_id or self.env.company).display_name,
                        })
                    line_vals = dict(vals, account_id=account.id)
                    line_vals.setdefault('name', product.display_name)
                    super(ImportContainerDepositLine, line).write(line_vals)
                return True
            vals['account_id'] = False
        return super().write(vals)

    @api.onchange('deposit_id')
    def _onchange_deposit_id(self):
        for line in self:
            if line.deposit_id and not line.vendor_id:
                line.vendor_id = line.deposit_id.container_vendor_id

    @api.constrains('product_id')
    def _check_approved_deposit_product(self):
        for line in self:
            if line.product_id and not self._is_approved_deposit_product(line.product_id):
                raise ValidationError(_(
                    'Product / Charge must be either "Uang Muka Jaminan Container" '
                    'or "Uang Muka Jaminan Sewa Container" '
                    '(Container/Kontainer spelling accepted).'
                ))

    @api.constrains('account_id')
    def _check_approved_deposit_account(self):
        approved_codes = set(self.APPROVED_DEPOSIT_ACCOUNT_CODES)
        for line in self:
            if not line.account_id:
                continue
            code = self._normalise_account_code(line.account_id.code)
            if code not in approved_codes:
                raise ValidationError(_(
                    'Deposit Account must be either 1720002 Uang Muka Jaminan Container '
                    'or 1720003 Uang Muka Jaminan Sewa Container.'
                ))

    @api.constrains('vendor_id')
    def _check_vendor_status(self):
        for line in self:
            partner = line.vendor_id
            if not partner:
                continue
            is_vendor = partner.is_vendor if 'is_vendor' in partner._fields else partner.supplier_rank > 0
            if not is_vendor:
                raise ValidationError(_('The selected partner must have Vendor status (Is Vendor).'))


class ImportContainerDepositSettlementLine(models.Model):
    _name = 'import.container.deposit.settlement.line'
    _description = 'Import Container Deposit Settlement Line'
    _order = 'sequence, id'

    deposit_id = fields.Many2one('import.container.deposit', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    currency_id = fields.Many2one(related='deposit_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one(related='deposit_id.company_id', store=True, readonly=True)
    source_deposit_line_id = fields.Many2one('import.container.deposit.line', string='Source Deposit Line')
    product_id = fields.Many2one(
        'product.product', string='Landed Cost Product / Charge',
        domain="[('landed_cost_ok', '=', True)]",
        help='Must be a product with Landed Cost enabled. Do not use Uang Muka Jaminan deposit products here.',
    )
    name = fields.Char(string='Description')
    container_vendor_id = fields.Many2one('res.partner', string='Container Vendor', required=True)
    original_deposit_amount = fields.Monetary(string='Original Deposit Amount', currency_field='currency_id')
    refund_amount = fields.Monetary(string='Refund Amount', currency_field='currency_id', default=0.0)
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[('type_tax_use', '=', 'purchase')],
        help='Purchase taxes applied to the Refund Amount when the Vendor Credit Note is created.',
    )
    charge_amount = fields.Monetary(
        string='Final Deducted Charge', currency_field='currency_id', default=0.0,
        help='Auto-calculated as Original Deposit Amount - Refund Amount when Refund Amount changes.',
    )
    charge_type = fields.Selection([
        ('detention', 'Detention'),
        ('demurrage', 'Demurrage'),
        ('rental', 'Container Rental'),
        ('cleaning', 'Cleaning'),
        ('repair', 'Repair'),
        ('admin', 'Admin'),
        ('other', 'Other'),
    ], string='Charge Type', default='detention')
    split_method = fields.Selection([
        ('equal', 'Equal'),
        ('by_quantity', 'By Quantity'),
        ('by_current_cost_price', 'By Current Cost'),
        ('by_weight', 'By Weight'),
        ('by_volume', 'By Volume'),
    ], string='Landed Cost Split Method', default='by_current_cost_price', required=True)
    charge_account_id = fields.Many2one('account.account', string='Charge Account', domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    refund_bill_id = fields.Many2one('account.move', string='Refund Credit Note', readonly=True, copy=False)
    landed_cost_id = fields.Many2one('stock.landed.cost', string='FTM Landed Cost', readonly=True, copy=False)
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    note = fields.Char(string='Note')

    # PTKJ corresponding data table:
    # Deposit product -> settlement Landed Cost product -> Charge Account.
    # * Uang Muka Jaminan Sewa Container -> Biaya Sewa Container (Demurrage) -> 6130006
    # * Uang Muka Jaminan Container -> Biaya Perbaikan dan Kebersihan Container -> 6130016
    # Tokens are casefolded substrings; Kontainer spelling kept for legacy master data.
    DEPOSIT_TO_CHARGE_MAP = (
        {
            'deposit_tokens': ('uang muka jaminan sewa container', 'uang muka jaminan sewa kontainer'),
            'charge_tokens': ('biaya sewa container', 'biaya sewa kontainer', 'sewa container'),
            'account_code': '6130006',
        },
        {
            'deposit_tokens': ('uang muka jaminan container', 'uang muka jaminan kontainer'),
            'charge_tokens': ('biaya perbaikan dan kebersihan container', 'biaya perbaikan dan kebersihan kontainer', 'perbaikan dan kebersihan'),
            'account_code': '6130016',
        },
    )

    @api.model
    def _get_charge_mapping_for_deposit_product(self, deposit_product):
        """Return the mapping row for a deposit (Uang Muka Jaminan) product."""
        if not deposit_product:
            return None
        name = (deposit_product.name or '').strip().casefold()
        for mapping in self.DEPOSIT_TO_CHARGE_MAP:
            if any(token in name for token in mapping['deposit_tokens']):
                return mapping
        return None

    @api.model
    def _find_landed_cost_product(self, tokens):
        """Find the corresponding landed-cost charge product by name tokens.

        Uses ORM reads (not SQL name domains) because product names are stored
        as translated JSONB on this database.
        """
        Product = self.env['product.product'].sudo()
        candidates = Product.search([
            ('landed_cost_ok', '=', True),
            ('active', '=', True),
        ])
        for token in tokens:
            matches = candidates.filtered(lambda p: token in (p.name or '').casefold())
            if matches:
                return matches.sorted('id')[0]
        return Product

    @api.model
    def _find_account_by_code(self, code, company=None):
        """Deterministic account lookup by digits-normalised code (e.g. 6130006)."""
        Account = self.env['account.account']
        if not code:
            return Account
        company = company or self.env.company
        self.env.cr.execute("""
            SELECT id
              FROM account_account
             WHERE regexp_replace(COALESCE(code, ''), '[^0-9]', '', 'g') = %s
             ORDER BY CASE WHEN COALESCE(deprecated, FALSE) THEN 1 ELSE 0 END,
                      CASE WHEN company_id = %s THEN 0 ELSE 1 END,
                      company_id NULLS LAST,
                      id
             LIMIT 1
        """, (code, company.id))
        row = self.env.cr.fetchone()
        return Account.sudo().browse(row[0]) if row else Account

    def _get_charge_account_for_product(self, product, company=None):
        """Return the mapped Charge Account for a landed-cost charge product.

        Preference order:
        1. Corresponding data table by product name (6130006 / 6130016).
        2. Product / category expense account.
        """
        Account = self.env['account.account']
        if not product:
            return Account
        company = company or self.company_id or self.env.company
        product_name = (product.name or '').strip().casefold()
        for mapping in self.DEPOSIT_TO_CHARGE_MAP:
            if any(token in product_name for token in mapping['charge_tokens']):
                account = self._find_account_by_code(mapping['account_code'], company)
                if account:
                    return account
        return (product.with_company(company).property_account_expense_id
                or product.categ_id.with_company(company).property_account_expense_categ_id
                or Account)

    @api.model
    def _compute_charge_from_refund(self, original_amount, refund_amount):
        original = original_amount or 0.0
        refund = refund_amount or 0.0
        return max(original - refund, 0.0)

    @api.onchange('refund_amount', 'original_deposit_amount')
    def _onchange_refund_amount(self):
        """Final Deduction = Original Deposit Amount - Refund Amount."""
        for line in self:
            line.charge_amount = line._compute_charge_from_refund(
                line.original_deposit_amount, line.refund_amount
            )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if 'charge_amount' not in vals:
                vals['charge_amount'] = self._compute_charge_from_refund(
                    vals.get('original_deposit_amount'), vals.get('refund_amount')
                )
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        vals = dict(vals)
        if 'refund_amount' in vals or 'original_deposit_amount' in vals:
            # Recalculate Final Deduction whenever refund/original changes,
            # unless the caller explicitly sets charge_amount in the same write.
            if 'charge_amount' not in vals:
                for line in self:
                    original = vals.get('original_deposit_amount', line.original_deposit_amount)
                    refund = vals.get('refund_amount', line.refund_amount)
                    line_vals = dict(vals, charge_amount=self._compute_charge_from_refund(original, refund))
                    super(ImportContainerDepositSettlementLine, line).write(line_vals)
                return True
        return super().write(vals)

    @api.constrains('refund_amount', 'charge_amount', 'original_deposit_amount')
    def _check_amounts(self):
        for line in self:
            if line.refund_amount < 0 or line.charge_amount < 0:
                raise ValidationError(_('Refund and charge amount cannot be negative.'))
            if line.original_deposit_amount and (line.refund_amount + line.charge_amount) > line.original_deposit_amount + 0.01:
                raise ValidationError(_('Refund + final charge cannot exceed original deposit amount.'))

    @api.constrains('product_id', 'charge_amount')
    def _check_landed_cost_product(self):
        for line in self:
            if line.product_id and line.charge_amount and not line.product_id.landed_cost_ok:
                raise ValidationError(_(
                    'Product %s must have Landed Cost enabled before it can be used '
                    'as Final Deduction / FTM Landed Cost product.'
                ) % line.product_id.display_name)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                if not line.name:
                    line.name = line.product_id.display_name
                account = line._get_charge_account_for_product(line.product_id, line.company_id)
                if account:
                    line.charge_account_id = account


class ImportContainerDepositOperation(models.Model):
    _name = 'import.container.deposit.operation'
    _description = 'Import Container Deposit FTM Operation Line'
    _order = 'id'

    deposit_id = fields.Many2one('import.container.deposit', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    qty = fields.Float(string='Quantity')
    product_uom_id = fields.Many2one('uom.uom', string='UOM')
    currency_id = fields.Many2one('res.currency', string='Currency')
    total_cost_currency = fields.Float(string='Currency Taxable Value')
    extra_expense_currency = fields.Float(string='Expense Taxable Value')


class AccountMove(models.Model):
    _inherit = 'account.move'

    container_deposit_id = fields.Many2one(
        'import.container.deposit',
        string='Container Deposit Reference',
        readonly=True,
        copy=False,
        index=True,
    )

    def action_cdm_register_payment(self):
        """Register Payment from the CDM bills list.

        The restricted CDM list has no separate Post action, so draft bills
        are posted automatically before opening the standard payment wizard
        (which only accepts posted entries).
        """
        moves = self.filtered(lambda m: m.state != 'cancel')
        if not moves:
            raise UserError(_('All selected bills are cancelled; there is nothing to pay.'))
        vendors = moves.mapped('partner_id.commercial_partner_id')
        if len(vendors) > 1:
            raise UserError(_(
                'The selected bills belong to different vendors:\n%s\n\n'
                'Payment must be registered per vendor. Please select only '
                'bills of the same vendor, then click Register Payment.'
            ) % '\n'.join('- %s' % v.display_name for v in vendors.sorted('display_name')))
        draft_moves = moves.filtered(lambda m: m.state == 'draft')
        if draft_moves:
            draft_moves.action_post()
        return moves.action_register_payment()

    def action_cdm_cancel_deposit_bill(self):
        """Cancel selected CDM bills/credit notes and restore the CDM document
        to the point before Create Deposit Bill / Create Refund Credit Note:
        the moves are cancelled and unlinked from the deposit/settlement lines,
        so the create buttons become available again."""
        Deposit = self.env['import.container.deposit']
        user = self.env.user
        allowed = (
            self.env.su
            or user.has_group(Deposit.GROUP_FINANCE)
            or user.has_group(Deposit.GROUP_ACCOUNTING)
            or user.has_group(Deposit.GROUP_ADMIN)
            or user.has_group('base.group_system')
        )
        if not allowed:
            raise UserError(_(
                'Only Container Deposit Finance, Accounting or Administrator '
                'users can cancel deposit bills.'))
        paid = self.filtered(lambda m: m.payment_state in ('paid', 'in_payment', 'partial'))
        if paid:
            raise UserError(_(
                'The following bills already have payments and cannot be cancelled:\n%s\n\n'
                'Cancel their payments first.'
            ) % '\n'.join('- %s' % (m.name if m.name and m.name != '/' else m.display_name) for m in paid))
        for move in self:
            if move.state == 'posted':
                move.button_draft()
            if move.state != 'cancel':
                move.button_cancel()
        deposit_lines = self.env['import.container.deposit.line'].sudo().search([
            ('vendor_bill_id', 'in', self.ids)])
        deposit_lines.write({'vendor_bill_id': False})
        settlement_lines = self.env['import.container.deposit.settlement.line'].sudo().search([
            ('refund_bill_id', 'in', self.ids)])
        settlement_lines.write({'refund_bill_id': False})


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _container_deposit_from_lines(self):
        """Return the single container-deposit document behind the wizard."""
        deposits = self.line_ids.mapped('move_id.container_deposit_id')
        return deposits if len(deposits) == 1 else self.env['import.container.deposit']

    def _create_payment_vals_from_wizard(self, batch_result=None):
        # Some other modules override/call this method without passing
        # batch_result (e.g. their edit-mode path).
        if batch_result is None:
            vals = super()._create_payment_vals_from_wizard()
        else:
            vals = super()._create_payment_vals_from_wizard(batch_result)
        deposit = self._container_deposit_from_lines()
        if deposit:
            vals['container_deposit_id'] = deposit.id
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        lines = batch_result.get('lines') if isinstance(batch_result, dict) else False
        deposits = lines.mapped('move_id.container_deposit_id') if lines else self.env['import.container.deposit']
        if len(deposits) == 1:
            vals['container_deposit_id'] = deposits.id
        return vals


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    container_deposit_id = fields.Many2one(
        'import.container.deposit',
        string='Container Deposit Reference',
        readonly=True,
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        for payment, vals in zip(payments, vals_list):
            deposit_id = vals.get('container_deposit_id')
            if deposit_id and payment.move_id:
                payment.move_id.container_deposit_id = deposit_id
        return payments

    def _cdm_unique_payment_move_name(self):
        """Compute the journal-entry name for a CDM payment from the journal's
        own entry sequence — the same convention as Vendor Bills
        (BILL/YYYY/Roman/####): PREFIX/YYYY/Roman/#### continuing the
        journal's last number, with a uniqueness guard."""
        self.ensure_one()
        move = self.move_id
        journal = move.journal_id
        sequence = journal.sequence_id
        if not sequence:
            return False
        
        Move = self.env['account.move'].sudo().with_context(active_test=False)
        sequence_ctx = sequence.sudo().with_context(ir_sequence_date=move.date)
        name = sequence_ctx.next_by_id()
        # Skip numbers already used in this journal (stale sequence counter),
        # so numbering reconnects with the journal's real last number.
        while name and Move.search_count([('journal_id', '=', journal.id), ('name', '=', name)]):
            name = sequence_ctx.next_by_id()
        return name

    def action_post(self):
        # Journal-entry numbering for payments is fragile on this database
        # (od_journal_sequence vs the standard sequence mixin) and raised
        # "Another entry with the same name already exists". For payments
        # coming from Container Deposit Management, pre-assign a verified
        # unique entry name drawn from the journal's own sequence, exactly
        # like Vendor Bills.
        for payment in self:
            move = payment.move_id
            if payment.container_deposit_id and move and (not move.name or move.name == '/'):
                name = payment._cdm_unique_payment_move_name()
                if name:
                    move.name = name
        return super().action_post()


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    container_deposit_id = fields.Many2one('import.container.deposit', string='Container Deposit Reference', readonly=True, copy=False)
    account_move_line_ids = fields.One2many(
        related='account_move_id.line_ids',
        string='Journal Items',
        readonly=True,
    )
    cdm_deposit_clearing_needed = fields.Boolean(
        compute='_compute_cdm_deposit_clearing_needed',
        help='True when this CDM landed cost is validated but Final Deduction '
             'has not yet cleared the deposit asset account.',
    )

    @api.depends(
        'container_deposit_id',
        'state',
        'container_deposit_id.settlement_line_ids.landed_cost_id',
        'container_deposit_id.settlement_line_ids.charge_amount',
        'container_deposit_id.settlement_line_ids.journal_entry_id',
    )
    def _compute_cdm_deposit_clearing_needed(self):
        for cost in self:
            if cost.state != 'done' or not cost.container_deposit_id:
                cost.cdm_deposit_clearing_needed = False
            else:
                cost.cdm_deposit_clearing_needed = bool(cost._cdm_settlement_lines_for_clearing())

    def action_cdm_post_deposit_clearing(self):
        """Manual action for already-validated CDM LCs missing the clearing JE."""
        for cost in self:
            if not cost.container_deposit_id:
                raise UserError(_('This Landed Cost is not linked to a Container Deposit.'))
            if cost.state != 'done':
                raise UserError(_(
                    'Validate the FTM Landed Cost first. Deposit clearing is posted '
                    'automatically on Validate, or use this action afterwards.'
                ))
        self._cdm_post_deposit_clearing_entries()
        return True

    def compute_landed_cost(self):
        """Allow Compute on CDM-generated landed costs.

        CDM sets ``custom_declaration_import_id`` so FTM display fields
        (PO, Vendor, Custom Doc. Number, …) stay linked. ``viin_foreign_trade``
        then blocks Compute for any LC that has that FTM link, because
        FTM-generated LCs already carry valuation lines.

        CDM LCs still need Compute to allocate the final deducted charges
        onto the transfers. Temporarily clear the FTM flags for CDM records
        only, run the normal Compute chain, then restore the link.
        """
        cdm = self.filtered('container_deposit_id')
        others = self - cdm
        res = True
        if others:
            res = super(StockLandedCost, others).compute_landed_cost()
        if not cdm:
            return res

        has_imp = 'custom_declaration_import_id' in cdm._fields
        has_exp = 'custom_declaration_export_id' in cdm._fields
        saved_imp = {
            c.id: c.custom_declaration_import_id.id
            for c in cdm
        } if has_imp else {}
        saved_exp = {
            c.id: c.custom_declaration_export_id.id
            for c in cdm
        } if has_exp else {}

        clear_vals = {}
        if has_imp:
            clear_vals['custom_declaration_import_id'] = False
        if has_exp:
            clear_vals['custom_declaration_export_id'] = False
        if clear_vals:
            cdm.with_context(tracking_disable=True).write(clear_vals)
        try:
            res = super(StockLandedCost, cdm).compute_landed_cost()
        finally:
            for c in cdm:
                restore = {}
                if saved_imp.get(c.id):
                    restore['custom_declaration_import_id'] = saved_imp[c.id]
                if saved_exp.get(c.id):
                    restore['custom_declaration_export_id'] = saved_exp[c.id]
                if restore:
                    c.with_context(tracking_disable=True).write(restore)
        return res

    def button_validate(self):
        """After LC validate, clear the deposit asset for Final Deduction.

        Standard landed-cost validation moves cost into stock and credits the
        Charge Account (e.g. 6130006). CDM still holds that amount on the
        deposit asset (1720002 / 1720003) until a companion clearing entry is
        posted:

            Dr Charge Account (6130006)
            Cr Deposit Account (1720003)

        so the deposit account closes after Refund CN + Final Deduction.
        """
        res = super().button_validate()
        self.filtered('container_deposit_id')._cdm_post_deposit_clearing_entries()
        return res

    def _cdm_settlement_lines_for_clearing(self):
        """Settlement lines of this LC that still need a deposit clearing JE."""
        self.ensure_one()
        deposit = self.container_deposit_id
        if not deposit:
            return self.env['import.container.deposit.settlement.line']
        return deposit.settlement_line_ids.filtered(
            lambda l: l.landed_cost_id == self
            and l.charge_amount > 0
            and not l.journal_entry_id
        )

    def _cdm_post_deposit_clearing_entries(self):
        """Post Dr Charge Account / Cr Deposit Account for Final Deduction."""
        AccountMove = self.env['account.move']
        for cost in self:
            if cost.state != 'done' or not cost.container_deposit_id:
                continue
            lines = cost._cdm_settlement_lines_for_clearing()
            if not lines:
                continue

            deposit = cost.container_deposit_id
            journal = deposit.landed_cost_journal_id or cost.account_journal_id
            if not journal:
                raise UserError(_(
                    'Please set Landed Cost Journal on %(name)s before validating '
                    'the FTM Landed Cost (needed to clear the deposit account).'
                ) % {'name': deposit.display_name})

            move_lines = []
            for line in lines:
                amount = line.charge_amount
                if not amount:
                    continue
                charge_account = line.charge_account_id
                if not charge_account:
                    raise UserError(_(
                        'Settlement line "%(line)s" has Final Deduction %(amount)s '
                        'but no Charge Account. Set Charge Account (e.g. 6130006) '
                        'before validating the FTM Landed Cost.'
                    ) % {
                        'line': line.name or line.display_name,
                        'amount': amount,
                    })
                deposit_account = line.source_deposit_line_id.account_id
                if not deposit_account:
                    raise UserError(_(
                        'Settlement line "%(line)s" has no Deposit Account on the '
                        'source deposit line. Set account 1720002/1720003 before '
                        'validating the FTM Landed Cost.'
                    ) % {'line': line.name or line.display_name})
                label = _('CDM deposit clearing - %(deposit)s - %(line)s') % {
                    'deposit': deposit.name,
                    'line': line.name or line.product_id.display_name or line.id,
                }
                partner = line.container_vendor_id
                move_lines.extend([
                    (0, 0, {
                        'name': label,
                        'account_id': charge_account.id,
                        'partner_id': partner.id if partner else False,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': label,
                        'account_id': deposit_account.id,
                        'partner_id': partner.id if partner else False,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ])

            if not move_lines:
                continue

            move = AccountMove.create({
                'move_type': 'entry',
                'name': '/',
                'date': cost.date or fields.Date.context_today(cost),
                'ref': _('CDM deposit clearing - %s') % deposit.name,
                'journal_id': journal.id,
                'container_deposit_id': deposit.id,
                'line_ids': move_lines,
            })
            move.action_post()
            lines.write({'journal_entry_id': move.id})
