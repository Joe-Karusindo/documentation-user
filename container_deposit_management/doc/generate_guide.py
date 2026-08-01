# -*- coding: utf-8 -*-
"""Generate Panduan Penggunaan Container Deposit Management v16.0.1.0.26 (.docx)."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC_PATH = '/Users/joe/odoo16/odoo/JASINDO/container_deposit_management/doc/Panduan_Penggunaan_Container_Deposit_Management_v16_1_0_26.docx'

doc = Document()

style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)


def title(text, size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = doc.add_paragraph()
    p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    return p


def h1(text):
    doc.add_heading(text, level=1)


def h2(text):
    doc.add_heading(text, level=2)


def para(text, bold=False, italic=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    return p


def bullet(text):
    doc.add_paragraph(text, style='List Bullet')


def number(text):
    doc.add_paragraph(text, style='List Number')


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Light Grid Accent 1'
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ''
        run = hdr[i].paragraphs[0].add_run(h)
        run.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.add_paragraph()
    return t


# ============ COVER ============
title('PANDUAN PENGGUNAAN', 20)
title('CUSTOM MODULE ODOO 16', 16)
title('Import Container Deposit Management', 24)
title('Versi Modul: 16.0.1.0.26', 13, bold=False)
doc.add_paragraph()
title('Technical Name: container_deposit_management', 12, bold=False)
title('Kategori: Inventory / Inventory', 12, bold=False)
doc.add_paragraph()
title('Dokumen Functional Guide — Step-by-Step per Stage', 12, bold=False)
title('Tanggal: 31 July 2026', 12, bold=False)
p = title('Audience: User Operasional Import, Management, Finance, Accounting, Administrator', 11, bold=False)
p.runs[0].italic = True
doc.add_page_break()

# ============ DAFTAR ISI ============
h1('Daftar Isi')
for item in [
    '1. Ringkasan Modul & Konsep Bisnis',
    '2. Perubahan Penting Versi 16.0.1.0.26',
    '3. Prasyarat Instalasi & Master Data',
    '4. Hak Akses (User Permission)',
    '5. Akses Menu & Penomoran Dokumen',
    '6. Alur Status (Workflow Stages)',
    '7. Penjelasan Field pada Form',
    '8. Panduan Step-by-Step per Stage',
    '9. Fungsi Setiap Tombol (Header & Smart Buttons)',
    '10. Cancel & Set to Draft',
    '11. Jurnal Accounting per Langkah',
    '12. Aturan Settlement Balance & Validasi',
    '13. Contoh Kasus End-to-End',
    '14. Opsi Show/Hide Kolom (Tree View)',
    '15. Troubleshooting Umum',
    '16. Checklist UAT',
    'Lampiran A — Matriks Hak Akses Model',
    'Lampiran B — Versi Dokumen',
]:
    para(item)
doc.add_page_break()

# ============ 1 ============
h1('1. Ringkasan Modul & Konsep Bisnis')
para('Modul Import Container Deposit Management digunakan untuk mengelola uang jaminan (deposit) '
     'container impor secara terpisah dari biaya impor (landed cost). Modul ini merupakan '
     'pengganti/refactor dari custom_safety_deposit.')

h2('1.1 Prinsip Utama')
bullet('Deposit container diperlakukan sebagai aset/piutang sementara (temporary receivable/asset), BUKAN biaya impor.')
bullet('Hanya nilai potongan/biaya final (Final Deducted Charge) setelah container dikembalikan yang di-posting ke FTM Landed Cost.')
bullet('Pembayaran deposit awal dipisahkan dari settlement refund dan deduction.')
bullet('Mata uang transaksi selalu menggunakan currency company (mis. IDR), tidak diganti oleh currency FTM.')

h2('1.2 Model Data')
table(['Model', 'Kegunaan'], [
    ['import.container.deposit', 'Dokumen utama Container Deposit Management'],
    ['import.container.deposit.line', 'Baris Deposit / Initial Charges (uang muka jaminan)'],
    ['import.container.deposit.settlement.line', 'Baris Settlement: Refund, Deduction, Charge'],
    ['import.container.deposit.operation', 'Snapshot baris operasi FTM (read-only)'],
])

h2('1.3 Dependensi Modul')
bullet('base, mail, account, purchase, stock, stock_account, stock_landed_costs')
bullet('custom_import (stack FTM / custom.declaration.import), ab_foreign_trade, custom_reports, ab_accounting')
bullet('sequence_reset_period, od_journal_sequence (penomoran journal & bulan Romawi)')

# ============ 2 ============
h1('2. Perubahan Penting Versi 16.0.1.0.26')
table(['No', 'Perubahan', 'Keterangan'], [
    ['1', 'Sequence dokumen bulan Romawi',
     'Nomor dokumen: CD/YYYY/RomawiBulan/##### (contoh CD/2026/VII/00001), reset bulanan.'],
    ['2', 'Hak akses berjenjang',
     'Lima group baru: User, Management, Finance, Accounting, Administrator. '
     'Tombol workflow tampil & dicek per group.'],
    ['3', 'Status Posted & Done digabung',
     'Tombol Mark Posted langsung menyelesaikan dokumen ke status Done. '
     'Status Posted dihapus dari workflow; record lama berstatus Posted otomatis menjadi Done.'],
    ['4', 'Cancel & Set to Draft',
     'Tersedia di semua status aktif dengan pembatasan per group; otomatis membatalkan '
     'dokumen accounting terkait yang aman dibatalkan.'],
    ['5', 'Penomoran Vendor Bill / Credit Note standar',
     'Bill memakai sequence journal BILL/YYYY/Romawi/####; Credit Note memakai RBILL/YYYY/Romawi/####. '
     'Fallback CD-BILL-*/CD-CN-* dihapus (dokumen lama tidak berubah).'],
    ['6', 'Print Container Deposit',
     'Report PDF untuk pengajuan dari Impor ke Management (status Draft s.d. Confirmed).'],
    ['7', 'Kolom editable dibatasi',
     'Tab Deposit: hanya Product, Vendor, Amount, Taxes yang dapat diedit. '
     'Tab Settlement: hanya Landed Cost Product, Refund Amount, Taxes, Charge Type.'],
    ['8', 'Opsi show/hide kolom',
     'Semua tree view (list utama, Deposit, Settlement, FTM Operations) mendukung '
     'show/hide kolom melalui ikon pengaturan kolom.'],
])

# ============ 3 ============
h1('3. Prasyarat Instalasi & Master Data')
h2('3.1 Sebelum Install / Upgrade')
number('Pastikan modul custom_import, stock_landed_costs, sequence_reset_period, dan od_journal_sequence sudah terpasang.')
number('Install/upgrade terlebih dahulu di database testing/UAT — jangan langsung production.')
number('Pastikan Chart of Accounts memiliki akun aktif berikut:')
table(['Kode Akun', 'Nama / Fungsi', 'Pemakaian'], [
    ['1700002', 'Uang Muka Jaminan Container', 'Deposit Account untuk produk jaminan container'],
    ['1700003', 'Uang Muka Jaminan Sewa Container', 'Deposit Account untuk produk jaminan sewa'],
])
para('Catatan: Saat install/upgrade, modul akan mereaktivasi akun 1700002 dan 1700003 jika sempat '
     'di-deprecate, serta menyesuaikan prefix sequence dokumen secara otomatis.', italic=True)

h2('3.2 Product Master yang Diizinkan (Deposit Lines)')
para('Pada tab Deposit / Initial Charges, Product / Charge hanya boleh:')
table(['Product', 'Deposit Account Auto'], [
    ['Uang Muka Jaminan Container', '1700002'],
    ['Uang Muka Jaminan Sewa Container', '1700003'],
])

h2('3.3 Product untuk Settlement (Landed Cost)')
para('Pada tab Settlement, field Landed Cost Product / Charge HARUS produk dengan Is a Landed Cost = True '
     '(contoh: Biaya Sewa Container / Detention / Demurrage / THC). JANGAN gunakan produk Uang Muka Jaminan.')

h2('3.4 Journal')
bullet('Landed Cost Journal (type: General) — otomatis terisi saat FTM Reference dipilih.')
bullet('Purchase Journal — untuk Vendor Bill deposit & Vendor Credit Note refund. '
       'Pastikan sequence journal: BILL/%(range_year)s/%(rom_month)s/ dan refund RBILL/%(range_year)s/%(rom_month)s/.')
bullet('Bank/Cash Journal — untuk Register Payment.')

h2('3.5 Vendor')
para('Partner yang dipilih harus berstatus Vendor (Is Vendor = True).')

# ============ 4 ============
h1('4. Hak Akses (User Permission)')
para('Assign group melalui Settings → Users → tab Access Rights → bagian CONTAINER DEPOSIT MANAGEMENT. '
     'Pengecekan dilakukan di dua lapis: visibilitas tombol pada form (XML groups) dan validasi server '
     '(Python) sehingga tidak dapat dilewati.')

h2('4.1 Daftar Group')
table(['Group', 'Peran', 'Status yang Dikelola'], [
    ['User', 'Staff operasional impor', 'Draft, Waiting Confirmation (Submit, Print)'],
    ['Management', 'Atasan/checker & approver', 'Confirmed (tombol Confirm), Approved (tombol Approve)'],
    ['Finance', 'Tim finance', 'Deposit Paid s.d. Waiting Approval (Create Deposit Bill, Mark Deposit Paid, '
     'Settlement, Settlement Received, Request Approval)'],
    ['Accounting', 'Tim accounting', 'Refund CN, FTM Landed Cost, Mark Posted (→ Done)'],
    ['Administrator', 'Full permission', 'Semua status dan semua tombol; bypass semua pengecekan group'],
])

h2('4.2 Matriks Permission per Status (termasuk hak Cancel / Set to Draft)')
table(['No', 'Status', 'Kode Teknis', 'Arti Bisnis', 'User Permission'], [
    ['1', 'Draft', 'draft', 'Dokumen baru; input FTM & baris deposit', 'User (can Cancel)'],
    ['2', 'Waiting Confirmation', 'waiting_confirm', 'Menunggu konfirmasi atasan/checker', 'User (can Cancel)'],
    ['3', 'Confirmed', 'confirmed', 'Sudah dikonfirmasi; siap buat Vendor Bill', 'Management (can Cancel)'],
    ['4', 'Deposit Paid', 'deposit_paid', 'Deposit sudah dibayar ke vendor', 'Finance (can Cancel)'],
    ['5', 'Waiting Settlement', 'waiting_settlement', 'Menunggu input refund & potongan', 'Finance (can Cancel)'],
    ['6', 'Settlement Received', 'settlement_received', 'Nilai settlement sudah diisi', 'Finance (can Cancel)'],
    ['7', 'Waiting Approval', 'waiting_approval', 'Menunggu approval (balance harus 0)', 'Finance (can Cancel)'],
    ['8', 'Approved', 'approved', 'Disetujui; buat Refund CN & FTM Landed Cost', 'Management (can Cancel)'],
    ['9', 'Done', 'done', 'Mark Posted diklik; dokumen accounting terposting; proses selesai', 'Accounting (can Cancel)'],
])
para('Administrator memiliki full permission pada seluruh status di atas.', italic=True)

# ============ 5 ============
h1('5. Akses Menu & Penomoran Dokumen')
para('Path menu (setelah modul terpasang):')
para('Import → Container Deposit Management', bold=True)
para('Menu hanya tampil untuk user yang memiliki salah satu group Container Deposit Management.')
para('Nomor dokumen otomatis: CD/YYYY/RomawiBulan/##### (contoh: CD/2026/VII/00001). '
     'Sequence menggunakan date range dengan reset bulanan, sehingga nomor urut kembali ke 00001 setiap awal bulan.')

# ============ 6 ============
h1('6. Alur Status (Workflow Stages)')
para('Dokumen berjalan melalui status berikut (statusbar):')
para('Draft → Waiting Confirmation → Confirmed → Deposit Paid → Waiting Settlement → '
     'Settlement Received → Waiting Approval → Approved → Done', bold=True)
para('Diagram alur singkat:')
para('Draft → Submit → Waiting Confirmation → Confirm → Confirmed → Create Deposit Bill + Register Payment '
     '→ Mark Deposit Paid → Settlement → Waiting Settlement → isi Refund/Deduction → Settlement Received '
     '→ Request Approval → Waiting Approval → Approve → Approved → Create Refund Credit Note + '
     'Create FTM Landed Cost → Mark Posted → Done (selesai)')
para('Catatan: Sejak versi 16.0.1.0.26 status Posted dan Done digabung. Saat tombol Mark Posted diklik, '
     'status langsung menjadi Done dan proses selesai.', italic=True)

# ============ 7 ============
h1('7. Penjelasan Field pada Form')
h2('7.1 Header — FTM & Vendor')
table(['Field', 'Keterangan', 'Editable'], [
    ['Internal Reference (name)', 'Nomor otomatis CD/YYYY/Romawi/#####', 'Tidak'],
    ['FTM Reference', 'Wajib. Link ke custom.declaration.import; mengisi PO, picking, vendor, dsb.', 'Hanya Draft'],
    ['Container Vendor', 'Vendor container; domain Is Vendor', 'Draft & Waiting Confirmation'],
    ['Landed Cost Journal', 'Default: journal bernama "Landed Cost Journal"', 'Hingga Confirmed/Approved'],
    ['Company / Currency', 'Perusahaan & currency dokumen (hidden)', 'Internal'],
])

h2('7.2 Header — FTM Information (Read-only / Auto)')
table(['Field', 'Sumber'], [
    ['Purchase Orders', 'Dari FTM'],
    ['Transfers / Receipts', 'Dari FTM (wajib ada untuk Create FTM Landed Cost)'],
    ['Form No', 'Dari FTM'],
    ['Custom Doc Number', 'Dari FTM'],
    ['AWB / BL Number', 'Dari FTM'],
    ['Clearance Date', 'Dari FTM'],
])

h2('7.3 Tab Deposit / Initial Charges')
table(['Kolom', 'Fungsi', 'Editable', 'Show/Hide'], [
    ['Product / Charge', 'Hanya 2 produk Uang Muka Jaminan', 'Ya', 'Selalu tampil'],
    ['Description', 'Auto dari product', 'Tidak (read-only)', 'Hide (default)'],
    ['Vendor', 'Vendor per baris; wajib Is Vendor', 'Ya', 'Show (default)'],
    ['Amount', 'Nilai deposit', 'Ya', 'Selalu tampil'],
    ['Taxes', 'Pajak purchase (opsional)', 'Ya', 'Show (default)'],
    ['Deposit Account', '1700002/1700003 auto dari product', 'Tidak (read-only)', 'Hide (default)'],
    ['Vendor Bill', 'Link bill yang dibuat', 'Tidak (read-only)', 'Hide (default)'],
    ['Note', 'Catatan baris', 'Tidak (read-only)', 'Hide (default)'],
])
para('Baris dapat diedit saat state: Draft, Waiting Confirmation.', italic=True)

h2('7.4 Tab Settlement: Refund / Deduction / Charges')
table(['Kolom', 'Fungsi', 'Editable', 'Show/Hide'], [
    ['Source Deposit Line', 'Baris deposit asal (auto saat Settlement)', 'Tidak', 'Hide (default)'],
    ['Landed Cost Product / Charge', 'Produk landed cost (wajib)', 'Ya', 'Selalu tampil'],
    ['Description', 'Deskripsi charge', 'Tidak', 'Hide (default)'],
    ['Container Vendor', 'Vendor settlement', 'Tidak', 'Show (default)'],
    ['Original Deposit Amount', 'Nilai deposit asal', 'Tidak', 'Show (default)'],
    ['Refund Amount', 'Jumlah yang dikembalikan vendor', 'Ya', 'Selalu tampil'],
    ['Taxes', 'Pajak untuk Refund Credit Note', 'Ya', 'Show (default)'],
    ['Final Deducted Charge', 'Auto = Original − Refund', 'Tidak (auto)', 'Show (default)'],
    ['Charge Type', 'detention/demurrage/rental/cleaning/repair/admin/other', 'Ya', 'Selalu tampil'],
    ['Landed Cost Split Method', 'Metode split landed cost', 'Tidak', 'Hide (default)'],
    ['Charge Account', 'Akun biaya charge', 'Tidak', 'Hide (default)'],
    ['Refund Credit Note', 'Link CN refund', 'Tidak', 'Hide (default)'],
    ['FTM Landed Cost', 'Link stock.landed.cost', 'Tidak', 'Hide (default)'],
    ['Note', 'Catatan', 'Tidak', 'Hide (default)'],
])
para('Baris dapat diedit saat state: Waiting Settlement, Settlement Received, Waiting Approval, Approved. '
     'Baris settlement digenerate otomatis (read-only source) saat tombol Settlement diklik.', italic=True)

h2('7.5 Tab FTM Operations')
para('Snapshot baris operasi FTM (product, PO, qty, UOM, currency, taxable values). Seluruhnya read-only, '
     'dengan opsi show/hide untuk kolom UOM, Currency, dan Taxable Value.')

h2('7.6 Ringkasan Amount (Footer)')
table(['Field', 'Rumus / Arti'], [
    ['Deposit Amount', 'Σ amount baris deposit'],
    ['Initial Charge Amount', 'Σ amount baris tipe initial_charge (legacy)'],
    ['Refund Amount', 'Σ refund_amount settlement'],
    ['Final Deducted / Container Charge', 'Σ charge_amount settlement'],
    ['Settlement Balance', 'Deposit − Refund − Final Deduction → harus 0 sebelum Request Approval'],
])

# ============ 8 ============
h1('8. Panduan Step-by-Step per Stage')

h2('Stage 1 — Draft: Buat Dokumen Baru (Group: User)')
para('Tujuan: Membuat dokumen deposit dan mengaitkannya ke FTM.')
number('Buka menu Import → Container Deposit Management → New.')
number('Pilih FTM Reference. Sistem otomatis mengisi PO, Transfers/Receipts, Form No, Custom Doc Number, '
       'AWB/BL, Clearance Date, Container Vendor, Landed Cost Journal, dan tab FTM Operations.')
number('Pada tab Deposit / Initial Charges, tambah baris: pilih Product (Uang Muka Jaminan Container atau '
       'Sewa Container), isi Vendor dan Amount. Deposit Account terisi otomatis.')
number('Klik Print Container Deposit untuk mencetak dokumen pengajuan ke Management (opsional).')
number('Save.')
para('Tombol aktif: Submit | Print Container Deposit | Cancel', bold=True)
para('Jurnal Accounting: Belum ada.')

h2('Stage 2 — Submit → Waiting Confirmation (Group: User)')
number('Klik tombol Submit.')
number('Validasi: minimal 1 baris deposit harus ada.')
number('Status berubah menjadi Waiting Confirmation.')
para('Tombol aktif: Confirm (Management) | Print Container Deposit | Set to Draft | Cancel', bold=True)

h2('Stage 3 — Confirm → Confirmed (Group: Management)')
para('Tujuan: Konfirmasi pengajuan dari user impor. Hanya group Management (atau Administrator) '
     'yang dapat melihat dan mengeksekusi tombol Confirm.')
number('Management memeriksa dokumen (bisa dari print out Container Deposit).')
number('Klik Confirm. Sistem re-sync data FTM (PO, picking, operasi).')
number('Status → Confirmed.')
para('Tombol aktif: Create Deposit Bill (Finance) | Mark Deposit Paid (Finance) | Set to Draft | Cancel', bold=True)

h2('Stage 4a — Create Deposit Bill (Group: Finance)')
para('Tujuan: Membuat Vendor Bill untuk pencatatan uang muka jaminan.')
number('Klik Create Deposit Bill.')
number('Sistem membuat 1 Vendor Bill per Vendor (group by vendor).')
number('Buka bill → Review → Confirm (Post) → Register Payment.')
para('Penomoran: bill memakai sequence journal Vendor Bill standar — BILL/YYYY/Romawi/#### '
     '(contoh BILL/2026/VII/0097), menyambung nomor terakhir journal.', italic=True)
para('Jurnal saat Post Bill: Dr Uang Muka 1700002/1700003 | Cr Utang Usaha.')
para('Jurnal saat Register Payment: Dr Utang Usaha | Cr Bank/Kas.')

h2('Stage 4b — Mark Deposit Paid → Deposit Paid (Group: Finance)')
number('Setelah pembayaran dilakukan, klik Mark Deposit Paid.')
number('Validasi: Deposit Amount > 0.')
number('Status → Deposit Paid.')

h2('Stage 5 — Settlement → Waiting Settlement (Group: Finance)')
para('Tujuan: Memulai proses settlement setelah container dikembalikan vendor.')
number('Klik Settlement.')
number('Sistem generate baris settlement dari baris deposit (Source Deposit Line, Original Amount, dsb. read-only).')
number('Status → Waiting Settlement.')
number('Isi Refund Amount per baris; Final Deducted Charge otomatis = Original − Refund.')
number('Pilih Landed Cost Product / Charge (produk dengan Is a Landed Cost = True) dan Charge Type.')

h2('Stage 6 — Settlement Received (Group: Finance)')
number('Klik Settlement Received setelah nilai settlement final dari vendor diterima.')
number('Validasi: settlement lines ada; refund/charge tidak negatif.')
number('Status → Settlement Received.')

h2('Stage 7 — Request Approval → Waiting Approval (Group: Finance)')
number('Klik Request Approval.')
number('Validasi: Settlement Balance harus = 0.')
number('Status → Waiting Approval.')

h2('Stage 8 — Approve → Approved (Group: Management)')
number('Management memeriksa dan klik Approve.')
number('Status → Approved.')
para('Tombol aktif: Create Refund Credit Note (Accounting) | Create FTM Landed Cost (Accounting) | '
     'Mark Posted (Accounting) | Set to Draft | Cancel', bold=True)

h2('Stage 9a — Create Refund Credit Note (Group: Accounting)')
para('Tujuan: Membuat Vendor Credit Note untuk nilai refund dari vendor.')
number('Klik Create Refund Credit Note.')
number('Sistem membuat CN per vendor untuk baris refund > 0 yang belum ber-CN.')
number('Buka CN → Post → proses penerimaan/rekonsiliasi refund.')
para('Penomoran: Credit Note memakai sequence refund journal — RBILL/YYYY/Romawi/#### '
     '(contoh RBILL/2026/VII/0005), menyambung nomor terakhir. Nomor tidak lagi tampil "/" setelah Post.', italic=True)
para('Jurnal saat Post CN: Dr Utang Usaha | Cr Uang Muka 1700002/1700003.')

h2('Stage 9b — Create FTM Landed Cost (Group: Accounting)')
para('Tujuan: Membebankan HANYA Final Deducted Charge ke biaya barang impor.')
number('Pastikan Transfers/Receipts dari FTM ada dan setiap baris charge > 0 memiliki Landed Cost Product.')
number('Klik Create FTM Landed Cost → sistem membuat draft stock.landed.cost.')
number('Buka Landed Cost → Compute → Validate.')
para('Jurnal saat Validate: Dr Stock Valuation/Expense | Cr Interim/Contra (hanya sebesar Final Deduction).')

h2('Stage 10 — Mark Posted → Done (Group: Accounting)')
para('Tujuan: Menyelesaikan proses. Posted dan Done adalah satu langkah.')
number('Klik Mark Posted.')
number('Validasi: jika ada Final Deducted Charge > 0, FTM Landed Cost harus sudah dibuat.')
number('Status langsung → Done. Proses Container Deposit Management selesai.')
para('Catatan: Mark Posted tidak membuat journal baru; journal sudah tercipta saat Post Bill/CN/Payment '
     'dan Validate Landed Cost.', italic=True)

# ============ 9 ============
h1('9. Fungsi Setiap Tombol')
h2('9.1 Tombol Header (Action Buttons)')
table(['Tombol', 'Terlihat di Status', 'Group', 'Fungsi / Validasi Utama'], [
    ['Submit', 'Draft', 'User', 'Kirim ke Waiting Confirmation; minimal 1 deposit line'],
    ['Print Container Deposit', 'Draft, Waiting Confirmation, Confirmed', 'User', 'Cetak PDF pengajuan ke Management'],
    ['Confirm', 'Waiting Confirmation', 'Management', 'Konfirmasi + sync FTM'],
    ['Set to Draft', 'Semua kecuali Draft & Cancelled', 'Sesuai owner status', 'Kembalikan ke Draft + batalkan dokumen terkait'],
    ['Create Deposit Bill', 'Confirmed, Deposit Paid', 'Finance', 'Buat Vendor Bill per vendor (BILL/…)'],
    ['Mark Deposit Paid', 'Confirmed', 'Finance', 'Tandai deposit dibayar; Deposit Amount > 0'],
    ['Settlement', 'Deposit Paid, Waiting Settlement', 'Finance', 'Mulai settlement; generate lines'],
    ['Settlement Received', 'Waiting Settlement', 'Finance', 'Settlement diterima; amount ≥ 0'],
    ['Request Approval', 'Settlement Received', 'Finance', 'Ajukan approval; Settlement Balance = 0'],
    ['Approve', 'Waiting Approval', 'Management', 'Setujui settlement'],
    ['Create Refund Credit Note', 'Approved', 'Accounting', 'Buat Vendor Credit Note refund (RBILL/…)'],
    ['Create FTM Landed Cost', 'Approved', 'Accounting', 'Buat draft Landed Cost FTM'],
    ['Mark Posted', 'Approved', 'Accounting', 'Selesaikan dokumen → Done; landed cost wajib jika ada deduction'],
    ['Cancel', 'Semua kecuali Cancelled', 'Sesuai owner status', 'Batalkan dokumen + dokumen accounting terkait'],
])
para('Administrator dapat melihat dan mengeksekusi seluruh tombol pada semua status.', italic=True)

h2('9.2 Smart Buttons (Button Box)')
table(['Smart Button', 'Muncul Jika', 'Fungsi'], [
    ['Vendor Bills', 'vendor_bill_count > 0', 'Buka Vendor Bill terkait deposit'],
    ['Refunds', 'refund_bill_count > 0', 'Buka Vendor Credit Note refund'],
    ['Landed Costs', 'landed_cost_count > 0', 'Buka FTM Landed Cost'],
    ['Journal Entries', 'journal_entry_count > 0', 'Buka journal entry ter-link di settlement'],
])

# ============ 10 ============
h1('10. Cancel & Set to Draft')
para('Kedua tombol tersedia pada seluruh status aktif (Draft s.d. Done untuk Cancel; '
     'Waiting Confirmation s.d. Done untuk Set to Draft), dengan hak akses mengikuti owner status '
     '(lihat matriks bab 4.2).')

h2('10.1 Validasi Otomatis')
bullet('DIBLOKIR jika ada FTM Landed Cost yang sudah divalidasi (state Done) — karena sudah mengubah '
       'nilai persediaan/product. Reverse landed cost terlebih dahulu bila dokumen harus dibuka kembali.')
bullet('DIBLOKIR jika ada Vendor Bill / Credit Note yang sudah dibayar (paid/partial).')

h2('10.2 Yang Dilakukan Sistem Saat Cancel / Set to Draft')
number('Vendor Bill, Credit Note, dan Journal Entry terkait yang masih draft/posted (belum dibayar) '
       'di-set ke draft lalu dibatalkan.')
number('Landed Cost draft dibatalkan.')
number('Link dokumen pada baris deposit/settlement dibersihkan sehingga smart buttons '
       '(Action Toolbar) ter-update — tidak lagi menampilkan hitungan dokumen lama.')
number('Status dokumen menjadi Cancelled (Cancel) atau Draft (Set to Draft).')

# ============ 11 ============
h1('11. Ringkasan Jurnal Accounting per Langkah')
table(['Langkah', 'Membuat Journal?', 'Jenis Dokumen', 'Pola Jurnal (sederhana)'], [
    ['Submit / Confirm', 'Tidak', '—', '—'],
    ['Create Deposit Bill + Post Bill', 'Ya', 'Vendor Bill (BILL/YYYY/Romawi/####)', 'Dr Uang Muka 1700002/03 | Cr Utang Usaha'],
    ['Register Payment Bill', 'Ya', 'Payment', 'Dr Utang Usaha | Cr Bank'],
    ['Mark Deposit Paid', 'Tidak', 'Status saja', '—'],
    ['Settlement / Received / Request / Approve', 'Tidak', '—', '—'],
    ['Create Refund CN + Post CN', 'Ya', 'Vendor Credit Note (RBILL/YYYY/Romawi/####)', 'Dr Utang Usaha | Cr Uang Muka 1700002/03'],
    ['Payment / settle CN refund', 'Ya', 'Payment', 'Dr Bank | Cr Utang Usaha (kas masuk)'],
    ['Create + Validate FTM Landed Cost', 'Ya', 'stock.landed.cost via Landed Cost Journal', 'Dr Stock/Expense | Cr Interim/Contra (hanya Final Deduction)'],
    ['Mark Posted (→ Done) / Cancel', 'Tidak', 'Status saja', '—'],
])

h2('11.1 Penomoran Dokumen Accounting')
bullet('Draft bill/CN selalu bernomor "/" sampai di-Post.')
bullet('Saat Post: Vendor Bill mengikuti sequence journal BILL/YYYY/Romawi/#### dan Credit Note '
       'RBILL/YYYY/Romawi/####, menyambung nomor terakhir pada bulan berjalan.')
bullet('Dokumen lama berformat CD-BILL-*/CD-CN-* (versi sebelumnya) tidak diubah.')

h2('11.2 Apa yang TIDAK boleh masuk Landed Cost')
bullet('Nilai penuh deposit awal (uang muka jaminan) — tetap di aset 1700002/1700003 sampai '
       'di-clear oleh refund/deduction.')
bullet('Produk Uang Muka Jaminan Container/Sewa — jangan diaktifkan sebagai Landed Cost product.')

# ============ 12 ============
h1('12. Aturan Settlement Balance & Validasi')
para('Settlement Balance = Deposit Amount − Refund Amount − Final Deducted Charge', bold=True)
para('Harus = 0 sebelum Request Approval.')
para('Contoh valid:')
table(['Komponen', 'Nilai (IDR)'], [
    ['Deposit Amount', '10.000.000'],
    ['Refund Amount', '7.000.000'],
    ['Final Deducted Charge', '3.000.000'],
    ['Settlement Balance', '0  ✓'],
])
para('Contoh tidak valid (tidak bisa Request Approval):')
table(['Komponen', 'Nilai (IDR)'], [
    ['Deposit Amount', '10.000.000'],
    ['Refund Amount', '6.000.000'],
    ['Final Deducted Charge', '3.000.000'],
    ['Settlement Balance', '1.000.000  ✗'],
])
para('Validasi lain pada settlement line:')
bullet('Refund dan Charge tidak boleh negatif.')
bullet('Refund + Final Charge tidak boleh melebihi Original Deposit Amount.')
bullet('Jika Charge > 0, product wajib landed_cost_ok = True.')

# ============ 13 ============
h1('13. Contoh Kasus End-to-End')
para('Skenario: Import FTM-ABC; deposit container Rp 10.000.000; setelah return, vendor refund '
     'Rp 7.500.000 dan potong detention Rp 2.500.000.')
h2('13.1 Langkah Operasional')
number('[User] Buat dokumen CD → pilih FTM → isi baris Uang Muka Jaminan Container Rp 10.000.000 (akun 1700002) → Print Container Deposit → Submit.')
number('[Management] Confirm.')
number('[Finance] Create Deposit Bill → Post Bill (BILL/2026/VII/…) → Register Payment Rp 10.000.000 → Mark Deposit Paid.')
number('[Finance] Settlement → isi Refund 7.500.000 → Final Deduction auto 2.500.000 → pilih produk landed cost Detention → Settlement Received → Request Approval (balance 0).')
number('[Management] Approve.')
number('[Accounting] Create Refund Credit Note Rp 7.500.000 → Post (RBILL/2026/VII/…) → terima/rekonsiliasi refund.')
number('[Accounting] Create FTM Landed Cost Rp 2.500.000 → Compute → Validate.')
number('[Accounting] Mark Posted → status langsung Done. Selesai.')
h2('13.2 Ringkasan Dampak Accounting')
table(['Event', 'Dampak'], [
    ['Bayar deposit', 'Aset Uang Muka +10jt; Bank −10jt'],
    ['Refund CN + kas masuk', 'Aset Uang Muka −7,5jt; Bank +7,5jt'],
    ['Validate Landed Cost', 'Biaya/Stock +2,5jt (final deduction saja)'],
    ['Saldo akhir Uang Muka terkait transaksi', '0'],
])

# ============ 14 ============
h1('14. Opsi Show/Hide Kolom (Tree View)')
para('Semua tree view mendukung pengaturan kolom melalui ikon pengaturan (⚙ / slider) di pojok kanan '
     'header tabel. Preferensi kolom tersimpan per user.')
h2('14.1 List Utama Container Deposit Management')
table(['Kolom', 'Default'], [
    ['Internal Reference, Status', 'Selalu tampil'],
    ['FTM Reference, Container Vendor, Deposit Amount, Settlement Balance', 'Show'],
    ['Form No, Custom Doc Number, AWB/BL, Clearance Date', 'Hide'],
    ['Initial Charge, Refund Amount, Final Deducted Charge', 'Hide'],
    ['Vendor Bills / Refunds / Landed Costs (jumlah)', 'Hide'],
])
h2('14.2 Tab pada Form')
bullet('Deposit / Initial Charges: Description, Deposit Account, Vendor Bill, Note dapat di-show/hide (default hide).')
bullet('Settlement: Source Deposit Line, Description, Split Method, Charge Account, Refund Credit Note, FTM Landed Cost, Note dapat di-show/hide (default hide).')
bullet('FTM Operations: UOM, Currency, dan Taxable Value dapat di-show/hide (default hide).')

# ============ 15 ============
h1('15. Troubleshooting Umum')
table(['Gejala / Error', 'Penyebab Umum', 'Solusi'], [
    ['Please input at least one deposit line', 'Submit tanpa baris', 'Tambah baris deposit'],
    ['You are not allowed to … this Container Deposit document', 'User tidak punya group yang sesuai', 'Assign group yang benar di Settings → Users'],
    ['Deposit amount must be greater than zero', 'Mark Deposit Paid tanpa nilai', 'Isi amount > 0'],
    ['Settlement balance must be zero…', 'Refund + Deduction ≠ Deposit', 'Sesuaikan angka hingga balance 0'],
    ['No receipt/transfer linked from FTM', 'FTM tanpa picking', 'Pastikan FTM punya Transfers'],
    ['Product must have Landed Cost enabled', 'Salah pilih produk Uang Muka', 'Pilih produk charge landed_cost_ok'],
    ['Account 1700002/03 not found', 'Akun belum ada / deprecated', 'Buat/aktifkan akun; upgrade modul'],
    ['Cannot cancel … validated FTM Landed Cost', 'Landed cost sudah Validate', 'Reverse landed cost dahulu bila perlu dibuka'],
    ['Cannot cancel … already paid', 'Bill/CN sudah dibayar', 'Batalkan payment sesuai SOP dahulu'],
    ['Please create FTM landed cost before Posted', 'Ada deduction tapi belum LC', 'Create FTM Landed Cost dulu'],
    ['Nomor CN tampil "/"', 'CN masih draft (belum Post)', 'Post CN; nomor RBILL/… otomatis terisi'],
    ['KeyError rom_month saat save', 'Modul od_journal_sequence versi lama', 'Upgrade od_journal_sequence ≥ 14.0.4.0.1'],
    ['Partner must have Vendor status', 'Partner bukan vendor', 'Centang Is Vendor pada partner'],
])

# ============ 16 ============
h1('16. Checklist UAT')
for item in [
    'Upgrade modul ke 16.0.1.0.26 di DB test; akun 1700002 & 1700003 aktif.',
    'Nomor dokumen baru berformat CD/YYYY/Romawi/##### dan reset tiap bulan.',
    'Lima group (User, Management, Finance, Accounting, Administrator) muncul di Settings → Users.',
    'User tanpa group tidak melihat menu; setiap tombol hanya tampil untuk group-nya.',
    'Print Container Deposit menghasilkan PDF pengajuan.',
    'Confirm hanya bisa oleh Management; Approve hanya oleh Management.',
    'Create Deposit Bill → Post → nomor BILL/YYYY/Romawi/#### menyambung sequence journal.',
    'Create Refund CN → Post → nomor RBILL/YYYY/Romawi/#### (bukan "/").',
    'Settlement: Final Deduction auto saat isi Refund; Request Approval gagal jika balance ≠ 0.',
    'Create FTM Landed Cost hanya sebesar Final Deduction; Validate sukses ke picking FTM.',
    'Mark Posted langsung mengubah status ke Done (tidak ada status Posted terpisah).',
    'Record lama berstatus Posted otomatis menjadi Done setelah upgrade.',
    'Cancel/Set to Draft membatalkan dokumen terkait & mengosongkan smart buttons; diblokir jika LC sudah Validate atau bill sudah dibayar.',
    'Opsi show/hide kolom berfungsi di list utama dan tab Deposit/Settlement/FTM Operations.',
]:
    bullet('☐  ' + item)

# ============ LAMPIRAN A ============
h1('Lampiran A — Matriks Hak Akses Model (ir.model.access)')
table(['Group', 'Dokumen CD', 'Deposit Line', 'Settlement Line', 'FTM Operation'], [
    ['User', 'R/W/C', 'R/W/C', 'R', 'R'],
    ['Management', 'R/W/C', 'R/W/C', 'R', 'R'],
    ['Finance', 'R/W/C', 'R/W/C', 'R/W/C', 'R'],
    ['Accounting', 'R/W/C/U', 'R/W/C/U', 'R/W/C/U', 'R/W/C/U'],
    ['Administrator', 'R/W/C/U', 'R/W/C/U', 'R/W/C/U', 'R/W/C/U'],
])
para('R = Read, W = Write, C = Create, U = Unlink (delete).', italic=True)
para('Selain access rights model, setiap tombol workflow juga dicek di level server (Python) '
     'sehingga user tanpa group yang sesuai tidak dapat mengeksekusi aksi meskipun memanggil API langsung.')

# ============ LAMPIRAN B ============
h1('Lampiran B — Versi Dokumen')
table(['Item', 'Nilai'], [
    ['Nama Modul', 'Import Container Deposit Management'],
    ['Versi yang dianalisis', '16.0.1.0.26'],
    ['Perubahan utama sejak 16.0.1.0.21', 'Hak akses berjenjang 5 group; Posted+Done digabung; sequence Romawi; penomoran BILL/RBILL standar; Cancel/Set to Draft; Print Container Deposit; show/hide kolom'],
    ['Format panduan', 'Microsoft Word (.docx)'],
    ['Bahasa', 'Indonesia'],
    ['Tanggal', '31 July 2026'],
])
para('Dokumen ini disusun berdasarkan evaluasi source code modul (models, views, hooks, security, report, '
     'migrations). Detail akun Debit/Kredit Landed Cost final dapat berbeda antar database tergantung '
     'konfigurasi COA, product category, dan inventory valuation method.', italic=True)

doc.save(DOC_PATH)
print('Saved:', DOC_PATH)
