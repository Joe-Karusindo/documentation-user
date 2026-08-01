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

    def _safe_get(self, record, field_name, default=False):
        return getattr(record, field_name) if field_name in record._fields else default

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
        purchase_orders = self._safe_get(ftm, 'purchase_order_ids') or self.env['purchase.order']
        pickings = self._safe_get(ftm, 'stock_picking_ids') or self.env['stock.picking']
        operation_commands = [(5, 0, 0)]
        ftm_lines = self._safe_get(ftm, 'custom_declaration_line_ids') or self.env['custom.declaration.import']
        for line in ftm_lines:
            operation_commands.append((0, 0, {
                'product_id': line.product_id.id if 'product_id' in line._fields and line.product_id else False,
                'qty': line.qty if 'qty' in line._fields else 0.0,
                'product_uom_id': line.product_uom.id if 'product_uom' in line._fields and line.product_uom else False,
                'currency_id': line.currency_id.id if 'currency_id' in line._fields and line.currency_id else False,
                'total_cost_currency': line.total_cost_currency if 'total_cost_currency' in line._fields else 0.0,
                'extra_expense_currency': line.extra_expense_currency if 'extra_expense_currency' in line._fields else 0.0,
                'purchase_order_id': line.purchase_order_id.id if 'purchase_order_id' in line._fields and line.purchase_order_id else False,
            }))

        return {
            'purchase_order_ids': [(6, 0, purchase_orders.ids)],
            'container_vendor_id': (self._safe_get(ftm, 'vendor_id').id
                                    if self._safe_get(ftm, 'vendor_id') else False),
            'picking_ids': [(6, 0, pickings.ids)],
            'form_no': self._safe_get(ftm, 'form_no') or False,
            'custom_doc_number': self._safe_get(ftm, 'number') or False,
            'no_awb': self._safe_get(ftm, 'no_awb') or False,
            'clearance_date': self._safe_get(ftm, 'clearance_date') or False,
            'currency_rate': self._safe_get(ftm, 'currency_rate') or 0.0,
            'total_taxable_currency': self._safe_get(ftm, 'total_cost_currency') or 0.0,
            'total_taxable_value': self._safe_get(ftm, 'total_cost') or 0.0,
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
                state_label = dict(rec._fields['state'].selection).get(rec.state, rec.state)
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

            for move in moves:
                if move.payment_state in ('paid', 'in_payment', 'partial'):
                    raise UserError(_(
                        'Cannot cancel or set to draft because related accounting '
                        'document %(move)s is already paid/partially paid.'
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
            rec.deposit_line_ids.filtered('vendor_bill_id').write({'vendor_bill_id': False})
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

    def action_set_to_draft(self):
        self._check_state_permission(_('set to draft'))
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_('Cancelled documents cannot be set to draft.'))
            rec._cancel_related_accounting_documents()
            rec.write({'state': 'draft'})

    def action_mark_deposit_paid(self):
        self._check_group(self.GROUP_FINANCE, _('mark deposit paid'))
        for rec in self:
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
            rec.write({'state': 'waiting_settlement'})

    def action_settlement_received(self):
        self._check_group(self.GROUP_FINANCE, _('mark settlement received'))
        for rec in self:
            if not rec.settlement_line_ids:
                raise UserError(_('Please input settlement lines first.'))
            if any(l.refund_amount < 0 or l.charge_amount < 0 for l in rec.settlement_line_ids):
                raise UserError(_('Refund amount and charge amount cannot be negative.'))
            rec.write({'state': 'settlement_received'})

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
        """Return the document to Draft so it can be edited again.

        After the form has been saved (or progressed in the workflow), clicking
        Cancel resets status to Draft. Related accounting documents that can
        safely be reversed are cancelled first (same safeguards as Set to Draft).
        """
        self._check_state_permission(_('cancel'))
        for rec in self:
            if rec.state == 'cancel':
                # Re-open a previously cancelled document for editing.
                rec.write({'state': 'draft'})
                continue
            if rec.state != 'draft':
                rec._cancel_related_accounting_documents()
            rec.write({'state': 'draft'})

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
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice_type')
        if len(moves) == 1:
            action.update({'name': title, 'view_mode': 'form', 'res_id': moves.id, 'views': [(self.env.ref('account.view_move_form').id, 'form')]})
        else:
            action.update({'name': title, 'domain': [('id', 'in', moves.ids)], 'view_mode': 'tree,form'})
        return action

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
            ),
            'account_names': (
                'uang muka jaminan sewa container',
            ),
        },
        {
            'codes': ('1720002',),
            'product_tokens': (
                'uang muka jaminan container',
            ),
            'account_names': (
                'uang muka jaminan container',
            ),
        },
    )
    APPROVED_DEPOSIT_PRODUCT_NAMES = (
        'Uang Muka Jaminan Container',
        'Uang Muka Jaminan Sewa Container',
    )
    APPROVED_DEPOSIT_ACCOUNT_CODES = ('1720002', '1720003')

    @api.model
    def _is_approved_deposit_product(self, product):
        """Exact approved product name match (ORM-safe with translated names)."""
        if not product:
            return False
        return (product.name or '').strip() in self.APPROVED_DEPOSIT_PRODUCT_NAMES

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
        product_name = (product.name or '').strip()
        if product_name == 'Uang Muka Jaminan Sewa Container':
            return ('1720003',), ('uang muka jaminan sewa container',)
        if product_name == 'Uang Muka Jaminan Container':
            return ('1720002',), ('uang muka jaminan container',)

        # Legacy fallback for minor spelling variants in imported master data.
        product_name_cf = product_name.casefold()
        default_code = (getattr(product, 'default_code', False) or '').strip().casefold()
        combined = f'{default_code} {product_name_cf}'
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
                    'or "Uang Muka Jaminan Sewa Container".'
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


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _container_deposit_from_lines(self):
        """Return the single container-deposit document behind the wizard."""
        deposits = self.line_ids.mapped('move_id.container_deposit_id')
        return deposits if len(deposits) == 1 else self.env['import.container.deposit']

    def _create_payment_vals_from_wizard(self, batch_result):
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


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    container_deposit_id = fields.Many2one('import.container.deposit', string='Container Deposit Reference', readonly=True, copy=False)
