from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ImportVendorBillWizard(models.TransientModel):
    _name = 'import.vendor.bill.wizard'
    _description = 'Wizard to Select Line for Bill'

    import_id = fields.Many2one('custom.import', string='Import Ref')
    # Relasi ke baris-baris yang bisa dipilih (Transient)
    line_ids = fields.One2many('import.vendor.bill.wizard.line', 'wizard_id', string='Lines to Bill')

    def action_create_bill(self):
        selected_lines = self.line_ids.filtered(lambda l: l.selected)
        if not selected_lines:
            raise UserError(_("Pilih minimal satu baris untuk dibuatkan Vendor Bill!"))

        vendors = selected_lines.mapped('vendor_id')
        last_move_id = False
        
        for vendor in vendors:
            lines_for_this_vendor = selected_lines.filtered(lambda l: l.vendor_id == vendor)
            line_vals = []
            
            for line in lines_for_this_vendor:
                is_landed = line.product_id.landed_cost_ok
                line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'quantity': 1.0,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                    'is_landed_costs_line': is_landed,
                }))

            # CREATE BILL (Tanpa otomatis create LC di sini biar cepet)
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': vendor.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': line_vals,
                'ref': self.import_id.name,
                # Link ke Custom Import biar gampang dicari
                'custom_import_id': self.import_id.id, 
                'form_no': self.import_id.form_no,
            })

            # Update link ke original line
            for l in lines_for_this_vendor:
                l.original_line_id.write({'vendor_bill_ids': [(4, move.id)]})
            
            last_move_id = move.id

        return {
            'name': _('Vendor Bill Created'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': last_move_id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
    
class ImportVendorBillWizardLine(models.TransientModel):
    _name = 'import.vendor.bill.wizard.line'
    _description = 'Wizard Line'

    wizard_id = fields.Many2one('import.vendor.bill.wizard')
    # Link ke record asli supaya bisa update related bill nantinya
    original_line_id = fields.Many2one('custom.import.line')
    
    # Checkbox buat milih
    selected = fields.Boolean(string='Select', default=False)
    
    # Field dummy buat nampilin data doang
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    price_unit = fields.Float(string='Price', readonly=True)
    discount = fields.Float(string='Disc (%)', readonly=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', readonly=True)
    subtotal = fields.Float(string='Sub Total', readonly=True)

    from odoo import models, fields, api

class ImportConfirmWizard(models.TransientModel):
    _name = 'import.confirm.wizard'
    _description = 'Wizard Konfirmasi Import'

    import_id = fields.Many2one('custom.import', string='Import Ref')
    
    # Data Kasbon
    kasbon_import = fields.Char(string='Pencarian Kasbon Import')
    pajak_pib_jasindo = fields.Float(string='PT Karunia Jasindo')
    pajak_pib_bu_fanny = fields.Float(string='Bu Fanny')
    
    # DIUBAH: Sekarang jadi field biasa (bukan compute) agar bisa diinput manual
    total_kasbon = fields.Float(string='Kasbon') 

    # Perincian Pengeluaran
    biaya_pajak = fields.Float(string='1. Biaya Pajak')
    
    # Summary Fields (Tetap compute untuk live preview di pojok kanan bawah)
    total_pengeluaran = fields.Float(string='Total Pengeluaran', compute='_compute_summary')
    total_kekurangan = fields.Float(string='Kekurangan', compute='_compute_summary')

    @api.onchange('pajak_pib_jasindo', 'pajak_pib_bu_fanny')
    def _onchange_kasbon_pajak(self):
        """Otomatis ngisi total kasbon saat Jasindo/Bu Fanny diisi, 
        tapi user tetep bisa edit manual field total_kasbon-nya."""
        self.total_kasbon = self.pajak_pib_jasindo + self.pajak_pib_bu_fanny

    @api.depends('total_kasbon', 'biaya_pajak', 'import_id.import_line_ids.subtotal')
    def _compute_summary(self):
        for rec in self:
            total_lines = sum(rec.import_id.import_line_ids.mapped('subtotal'))
            rec.total_pengeluaran = rec.biaya_pajak + total_lines
            # Rumus sesuai permintaan: Pengeluaran - Kasbon (Manual) = Kekurangan
            rec.total_kekurangan = rec.total_pengeluaran - rec.total_kasbon

    def process_confirm(self):
        total_lines = sum(self.import_id.import_line_ids.mapped('subtotal'))
        total_keluar = self.biaya_pajak + total_lines
        
        self.import_id.write({
            'kasbon_import': self.kasbon_import,
            'pajak_pib_jasindo': self.pajak_pib_jasindo,
            'pajak_pib_bu_fanny': self.pajak_pib_bu_fanny,
            'total_kasbon': self.total_kasbon, # Nilai manual dari wizard masuk ke sini
            'biaya_pajak': self.biaya_pajak,
            'total_perincian_pengeluaran': total_lines,
            'total_pengeluaran': total_keluar,
            'total_kekurangan': total_keluar - self.total_kasbon,
            'state': 'confirm',
            'date_confirm': fields.Date.context_today(self),
        })
        return {'type': 'ir.actions.act_window_close'}