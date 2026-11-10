from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class CustomImport(models.Model):
    _name = 'custom.import'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Import Custom Clearance'

    name = fields.Char(string='Internal Reference', required=True, copy=False, readonly=True, default='New')
    
    # Field FTM sebagai Key Utama
    ftm_id = fields.Many2one('custom.declaration.import', string='FTM Reference', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approval', 'Approved'),
        ('validate', 'Validate'),
        ('landed_cost', 'Landed Cost'),
        ('post', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Group Kiri (Auto-fill dari FTM)
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Order')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    picking_ids = fields.Many2many('stock.picking', string='Transfer')
    form_no = fields.Char(string='Form No')
    
    # Group Kanan (Auto-fill dari FTM)
    custom_doc_number = fields.Char(string='Custom Doc Number')
    no_awb = fields.Char(string='No AWB')
    clearance_date = fields.Date(string='Clearance Date')
    date_confirm = fields.Date(string='Date Confirmed', readonly=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_tax_rate = fields.Float(string='Currency Tax Rate', digits=(12, 4))
    total_taxable_currency = fields.Float(string='Total Taxable Valuable Currency')
    total_taxable_value = fields.Float(string='Total Taxable Value')
    
    import_line_ids = fields.One2many('custom.import.line', 'import_id', string='Additional Cost')
    operation_line_ids = fields.One2many(
        'custom.import.operation', 
        'import_id', 
        string='Operations', 
        copy=True, # Agar saat duplikat data ikut terbawa
        readonly=True, 
    )

    amount_untaxed = fields.Float(string='Untaxed Amount', store=True, compute='_compute_amounts')
    amount_tax = fields.Float(string='Tax', store=True, compute='_compute_amounts')
    amount_total = fields.Float(string='Total', store=True, compute='_compute_amounts')

    vendor_bill_count = fields.Integer(string='Bill Count', compute='_compute_vendor_bill_count')
    landed_cost_count = fields.Integer(string='Landed Cost Count', compute='_compute_landed_cost_count')
    # --- Field untuk Tab Document Printout ---
    kasbon_import = fields.Char(string='Kasbon Import')
    pajak_pib_jasindo = fields.Float(string='PT Karunia Jasindo')
    pajak_pib_bu_fanny = fields.Float(string='Bu Fanny')
    total_kasbon = fields.Float(string='Total Kasbon')
    
    biaya_pajak = fields.Float(string='Biaya Pajak')
    # Detail pengeluaran tambahan (diambil dari import_line_ids nantinya)
    total_perincian_pengeluaran = fields.Float(string='Total Perincian Pengeluaran')
    total_pengeluaran = fields.Float(string='Total Pengeluaran')
    total_kekurangan = fields.Float(string='Kekurangan')

    has_landed_cost = fields.Boolean(
        string='Has Landed Cost', 
        compute='_compute_has_landed_cost',
        search='_search_has_landed_cost'
    )
    product_ids = fields.Many2many(
        'product.product', 
        string='Products', 
        compute='_compute_product_ids'
    )

    landed_cost_ids = fields.One2many(
        'stock.landed.cost', 
        'custom_import_id', # pastikan field inverse ini sesuai di model stock.landed.cost
        string='Landed Costs'
    )
    
    @api.depends('import_line_ids.product_id')
    def _compute_product_ids(self):
        for rec in self:
            # Mengambil semua product_id unik dari detail baris tambahan biaya
            products = rec.import_line_ids.mapped('product_id')
            rec.product_ids = [(6, 0, products.ids)]

    def _compute_has_landed_cost(self):
        for rec in self:
            # Cari apakah ada dokumen landed cost yang mengarah ke CPR ini
            # Catatan: Sesuaikan nama field 'cpr_id' atau 'custom_import_id' di model stock.landed.cost Anda
            lc_count = self.env['stock.landed.cost'].search_count([('custom_import_id', '=', rec.id)])
            rec.has_landed_cost = lc_count > 0

    def _search_has_landed_cost(self, operator, value):
        # Mengambil semua ID custom.import yang sudah masuk ke dokumen stock.landed.cost
        landed_costs = self.env['stock.landed.cost'].search([('custom_import_id', '!=', False)])
        cpr_ids = landed_costs.mapped('custom_import_id').ids
        
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('id', 'in', cpr_ids)]
        else:
            return [('id', 'not in', cpr_ids)]
        

    def _get_all_related_lc_ids(self):
        self.ensure_one()
        # Menggunakan .sudo() agar user Finance/Sales bisa menghitung jumlahnya tanpa error akses
        # 1. Cari Landed Cost dari Picking
        lc_from_picking = self.env['stock.landed.cost'].sudo().search([
            ('picking_ids', 'in', self.picking_ids.ids)
        ]).ids
        
        # 2. Cari Landed Cost dari Vendor Bill yang terhubung di Additional Cost (Mulai dari state Draft)
        related_bills = self.import_line_ids.mapped('vendor_bill_ids').ids
        lc_from_bills = self.env['stock.landed.cost'].sudo().search([
            '|',
            ('vendor_bill_id', 'in', related_bills),
            ('vendor_bill_ids', 'in', related_bills) # Mengantisipasi relasi many2many / many2one Odoo
        ]).ids
        
        return list(set(lc_from_picking + lc_from_bills))

    def _compute_landed_cost_count(self):
        for rec in self:
            # Tetap hitung menggunakan sudo di dalam method pencarian
            rec.landed_cost_count = len(rec._get_all_related_lc_ids())

    def action_view_landed_costs(self):
        self.ensure_one()
        lc_ids = self._get_all_related_lc_ids()
        
        # Ambil tindakan dasar Odoo untuk Landed Cost
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        action['domain'] = [('id', 'in', lc_ids)]
        
        # FIX: Supaya selalu memunculkan Tree/List View terlebih dahulu, 
        # Hapus kondisi "if len(lc_ids) == 1:" yang langsung mengarah ke Form View.
        action['views'] = [
            (self.env.ref('stock_landed_costs.view_stock_landed_cost_tree').id, 'tree'),
            (self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form')
        ]
        action['view_mode'] = 'tree,form'
        
        return action

    @api.depends('import_line_ids.vendor_bill_ids')
    def _compute_vendor_bill_count(self):
        for rec in self:
            # Kita ambil semua ID bill dari tiap baris, lalu di-set() supaya unik (nggak dobel hitung)
            all_bills = rec.import_line_ids.mapped('vendor_bill_ids')
            rec.vendor_bill_count = len(all_bills)

    def action_view_vendor_bills(self):
        # Ambil semua ID bill yang terelasi di tree line
        bill_ids = self.import_line_ids.mapped('vendor_bill_ids').ids
        
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        
        # Masukkan domain agar hanya memfilter bill terkait
        action['domain'] = [('id', 'in', bill_ids)]
        
        # PAKSA: Selalu tampilkan Tree View di urutan pertama
        action['views'] = [
            (self.env.ref('account.view_in_invoice_bill_tree').id, 'tree'),
            (self.env.ref('account.view_move_form').id, 'form')
        ]
        
        # Hapus res_id agar Odoo tidak otomatis masuk ke form view jika data cuma 1
        action['res_id'] = False
        
        return action
    
    _LOCKED_AFTER_APPROVE_STATES = ('approval', 'validate', 'landed_cost', 'post', 'cancel')

    def _get_state_label(self):
        self.ensure_one()
        return dict(self._fields['state'].selection).get(self.state, self.state)

    def _check_not_locked_after_approve(self, action_label):
        """Blokir aksi pada CPR yang sudah Approved (dan status berikutnya)."""
        locked = self.filtered(lambda r: r.state in self._LOCKED_AFTER_APPROVE_STATES)
        if locked:
            details = '\n'.join(
                "- %s (%s)" % (rec.name, rec._get_state_label()) for rec in locked
            )
            raise UserError(_(
                "Tidak dapat %s Cost Payment Request yang sudah di-Approve "
                "(atau status setelahnya).\n"
                "Gunakan Cancel jika dokumen perlu dibatalkan.\n\n"
                "Dokumen terkunci:\n%s"
            ) % (action_label, details))

    def action_revisi(self):
        """Revisi hanya diizinkan sebelum Approved.

        Setelah dokumen Confirmed lalu di-Approve (dan status berikutnya),
        dokumen tidak boleh dikembalikan ke Draft; gunakan Cancel.
        """
        self._check_not_locked_after_approve(_('merevisi'))
        for rec in self:
            rec.write({'state': 'draft'})

    def action_cancel(self):
        """Cancel tetap diizinkan termasuk setelah Approved."""
        for rec in self:
            if rec.state == 'cancel':
                continue
            rec.write({'state': 'cancel'})

    def unlink(self):
        """Blokir Delete (termasuk Action > Delete di treeview) setelah Approved."""
        self._check_not_locked_after_approve(_('menghapus'))
        return super(CustomImport, self).unlink()

    # Create Method untuk Sequence Otomatis
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            now = datetime.now()
            year = now.strftime('%Y')
            month = now.month
            roman_months = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII', 9:'IX', 10:'X', 11:'XI', 12:'XII'}
            month_rom = roman_months[month]
            
            # LOGIC BARU: Cari record terakhir di bulan/tahun yang sama biar gak duplikat
            prefix = f"CPR/{year}/{month_rom}/"
            last_record = self.search([('name', 'like', prefix + '%')], order='name desc', limit=1)
            
            if last_record:
                # Ambil 5 digit terakhir, tambah 1
                last_no = int(last_record.name.split('/')[-1])
                new_no = str(last_no + 1).zfill(5)
            else:
                new_no = '00001'
                
            vals['name'] = prefix + new_no
        return super(CustomImport, self).create(vals)

    # Onchange FTM
    @api.onchange('ftm_id')
    def _onchange_ftm_id(self):
        if self.ftm_id:
            ftm = self.ftm_id
            self.purchase_order_ids = ftm.purchase_order_ids
            self.vendor_id = ftm.vendor_id
            self.picking_ids = ftm.stock_picking_ids
            self.form_no = ftm.form_no
            
            self.custom_doc_number = ftm.number
            self.no_awb = ftm.no_awb
            self.clearance_date = ftm.clearance_date
            self.currency_id = ftm.currency_id
            self.currency_tax_rate = ftm.currency_rate
            self.total_taxable_currency = ftm.total_cost_currency
            self.total_taxable_value = ftm.total_cost
            # LOGIC BARU: Isi tab Operations dari Line FTM
            op_lines = []
            for line in ftm.custom_declaration_line_ids:
                op_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                    'product_uom': line.product_uom.id,
                    'currency_id': line.currency_id.id,
                    'total_cost_currency': line.total_cost_currency,
                    'extra_expense_currency': line.extra_expense_currency,
                    'purchase_order_id': line.purchase_order_id.id,
                }))
            
            # PENTING: Gunakan perintah (5,0,0) untuk hapus yang lama dulu
            # Lalu masukkan yang baru
            self.operation_line_ids = [(5, 0, 0)] + op_lines

    def action_confirm(self):
        if self.state != 'draft':
            return
        # SIMPAN agar data dari onchange (Operations)
        self._onchange_ftm_id()
        # Siapkan data default untuk wizard
        return {
            'name': _('Perincian Kasbon & Pengeluaran'),
            'type': 'ir.actions.act_window',
            'res_model': 'import.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_import_id': self.id,
                'default_kasbon_import': self.custom_doc_number,
                'default_biaya_pajak': 0.0, # Bisa diisi default jika ada
            }
        }
    
    def action_approve(self): self.write({'state': 'approval'})
    def action_validate(self): self.write({'state': 'validate'})
    def action_post(self):
        for rec in self:
            # Opsional: Tambahkan validasi di sini jika diperlukan sebelum posting
            rec.write({'state': 'post'})

    def action_create_vendor_bill(self):
        if not self.import_line_ids:
            raise UserError(_("Tidak ada baris data di Operations!"))

        # Siapkan data untuk wizard
        wizard_lines = []
        for line in self.import_line_ids:
            wizard_lines.append((0, 0, {
                'original_line_id': line.id,
                'product_id': line.product_id.id,
                'vendor_id': line.vendor_id.id,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'taxes_id': [(6, 0, line.taxes_id.ids)],
                'subtotal': line.subtotal,
            }))

        # Buat record wizard-nya dulu
        wizard = self.env['import.vendor.bill.wizard'].create({
            'import_id': self.id,
            'line_ids': wizard_lines,
        })

        return {
            'name': _('Select Lines to Create Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'import.vendor.bill.wizard',
            'view_mode': 'form',
            'res_id': wizard.id, # Buka record yang barusan dibuat
            'target': 'new',
        }
# Tambahkan field totalan di model utama buat visual kanan bawah
    
    @api.depends('import_line_ids.price_unit', 'import_line_ids.discount', 'import_line_ids.taxes_id')
    def _compute_amounts(self):
        for rec in self:
            untaxed = 0.0
            tax = 0.0
            for line in rec.import_line_ids:
                # Hitung dasar
                price_disc = line.price_unit * (1 - (line.discount / 100.0))
                taxes = line.taxes_id.compute_all(price_disc, quantity=1.0, product=line.product_id)
                untaxed += taxes['total_excluded']
                tax += sum(t['amount'] for t in taxes['taxes'])
            
            rec.amount_untaxed = untaxed
            rec.amount_tax = tax
            rec.amount_total = untaxed + tax

class CustomImportLine(models.Model):
    _name = 'custom.import.line'
    _description = 'Import Line'

    import_id = fields.Many2one('custom.import', string='Import Reference', ondelete='cascade')
    
    # PAKAI SEQUENCE BIAR STABLE
    line_no = fields.Integer(string='No', compute='_compute_line_no')
    
    parent_state = fields.Selection(related='import_id.state', string='Parent State', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    price_unit = fields.Float(string='Price')
    discount = fields.Float(string='Disc (%)')
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'purchase')])
    
    subtotal = fields.Float(string='Sub Total', compute='_compute_subtotal', store=True)
    vendor_bill_ids = fields.Many2many('account.move', string='Related Vendor Bills', readonly=True)

    @api.depends('import_id.import_line_ids')
    def _compute_line_no(self):
        for rec in self.mapped('import_id'):
            number = 1
            for line in rec.import_line_ids:
                line.line_no = number
                number += 1

    @api.depends('price_unit', 'discount', 'taxes_id')
    def _compute_subtotal(self):
        for line in self:
            price_after_disc = line.price_unit * (1 - (line.discount / 100.0))
            taxes = line.taxes_id.compute_all(price_after_disc, quantity=1.0, product=line.product_id)
            line.subtotal = taxes['total_included']

# Model Baru buat nampung data dari FTM Line Operations
class CustomImportOperation(models.Model):
    _name = 'custom.import.operation'
    _description = 'Import Operation Lines'

    import_id = fields.Many2one('custom.import', ondelete='cascade')
    line_no = fields.Integer(string='No', compute='_compute_line_no')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='UOM')
    currency_id = fields.Many2one('res.currency', string='Currency On Order')
    total_cost_currency = fields.Float(string='Currency Taxable Value')
    extra_expense_currency = fields.Float(string='Expense Taxable Value')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.depends('import_id.operation_line_ids')
    def _compute_line_no(self):
        for rec in self.mapped('import_id'):
            number = 1
            for line in rec.operation_line_ids:
                line.line_no = number
                number += 1