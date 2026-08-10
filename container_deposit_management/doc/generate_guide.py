# -*- coding: utf-8 -*-
"""Generate Panduan Penggunaan Container Deposit Management v16.0.1.0.49 (.docx)."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC_PATH = '/Users/joe/odoo16/odoo/JASINDO/container_deposit_management/doc/Panduan_Penggunaan_Container_Deposit_Management_v16_1_0_49.docx'

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
title('Versi Modul: 16.0.1.0.50 (panduan file v16_1_0_49)', 13, bold=False)
doc.add_paragraph()
title('Technical Name: container_deposit_management', 12, bold=False)
title('Kategori: Inventory / Inventory', 12, bold=False)
doc.add_paragraph()
title('Dokumen Functional Guide — Step-by-Step per Stage', 12, bold=False)
title('Tanggal: 5 August 2026', 12, bold=False)
p = title('Audience: User Operasional Import, Management, Finance, Accounting, Administrator', 11, bold=False)
p.runs[0].italic = True
doc.add_page_break()

# ============ DAFTAR ISI ============
h1('Daftar Isi')
for item in [
    '1. Ringkasan Modul & Konsep Bisnis',
    '2. Perubahan Penting Hingga Versi 16.0.1.0.50',
    '3. Prasyarat Instalasi & Master Data',
    '4. Hak Akses (User Permission)',
    '5. Akses Menu & Penomoran Dokumen',
    '6. Alur Status (Workflow Stages)',
    '7. Penjelasan Field pada Form',
    '8. Panduan Step-by-Step per Stage',
    '9. Fungsi Setiap Tombol (Header & Smart Buttons)',
    '10. Cancel & Set to Draft',
    '11. SOP Cancel pada Stage 4a, 9a, dan 9b (Journal & Audit)',
    '12. Ringkasan Jurnal Accounting per Langkah',
    '13. Aturan Settlement Balance & Validasi',
    '14. Contoh Kasus End-to-End',
    '15. Opsi Show/Hide Kolom (Tree View)',
    '16. Troubleshooting Umum',
    '17. Checklist UAT',
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
h1('2. Perubahan Penting Hingga Versi 16.0.1.0.50')
table(['No', 'Perubahan', 'Keterangan'], [
    ['1', 'Sequence dokumen bulan Romawi',
     'Nomor dokumen: CD/YYYY/RomawiBulan/##### (contoh CD/2026/VII/00001), reset bulanan.'],
    ['2', 'Hak akses berjenjang',
     'Lima group: User, Management, Finance, Accounting, Administrator. '
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
     'Tab Settlement: hanya Refund Amount, Taxes, Charge Type.'],
    ['8', 'Opsi show/hide kolom',
     'Semua tree view (list utama, Deposit, Settlement, FTM Operations) mendukung '
     'show/hide kolom melalui ikon pengaturan kolom.'],
    ['9', 'Tombol Create Deposit Bill / Mark Deposit Paid pintar',
     'Create Deposit Bill otomatis tersembunyi setelah semua baris deposit ter-bill. '
     'Mark Deposit Paid di-highlight setelah bill dibuat, dan divalidasi: semua bill harus '
     'sudah Posted dan Paid/In Payment sebelum status berubah ke Deposit Paid.'],
    ['10', 'Settlement auto-fill',
     'Saat tombol Settlement diklik, Landed Cost Product / Charge dan Charge Account '
     'otomatis terisi sesuai tabel mapping produk deposit (lihat bab 3.3). '
     'Kolom Landed Cost Product / Charge menjadi read-only.'],
    ['11', 'Akun deposit 1720002 / 1720003',
     'Deposit Account memakai akun 1720002 Uang Muka Jaminan Container dan '
     '1720003 Uang Muka Jaminan Sewa Container (di bawah 1720 Uang Muka Pembelian). '
     'Akun lama 1700002/1700003 tidak digunakan lagi.'],
    ['12', 'Dokumen Cancelled bersifat final',
     'Tombol Set to Draft disembunyikan pada status Cancelled; dokumen yang '
     'sudah dibatalkan tidak dapat dibuka kembali. Buat dokumen CDM baru bila diperlukan.'],
    ['13', 'Daftar Bills dari CDM dibatasi',
     'List Vendor Bills / Refunds yang dibuka dari dokumen CDM tidak lagi menampilkan '
     'tombol New, Upload, dan Create Landed Costs. Register Payment di-highlight '
     'sebagai aksi utama.'],
    ['14', 'Tombol Cancel pada daftar Bills CDM',
     'Membatalkan bill terpilih (ditolak jika sudah ada pembayaran) dan melepas '
     'tautannya dari baris deposit, sehingga dokumen kembali seperti sebelum '
     'Create Deposit Bill diklik dan tombol tersebut tersedia lagi.'],
    ['15', 'Register Payment CDM pintar',
     'Draft bill otomatis di-Post sebelum wizard payment; bill multi-vendor diblokir; '
     'journal entry payment memakai sequence journal Bank/Kas (BB/…, KB/…) yang sudah '
     'dikonfigurasi, menyambung nomor terakhir.'],
    ['16', 'Settlement lock (klik Settlement ke-2)',
     'Klik Settlement pertama membuka input Refund Amount. Klik Settlement lagi '
     'mengunci baris (settlement_locked). Hanya Set to Draft yang membuka kunci.'],
    ['17', 'Set to Draft dari tahap settlement',
     'Jika deposit bill sudah dibayar, Set to Draft dari Waiting Settlement s.d. Done '
     'mengembalikan ke Waiting Settlement (bukan Draft) agar Refund Amount bisa dikoreksi. '
     'Tab Deposit tetap terkunci karena bill sudah dibayar. Status Cancelled bersifat final '
     '(tanpa Set to Draft).'],
    ['18', 'Cancel disembunyikan di tahap settlement',
     'Tombol Cancel tidak tampil pada Waiting Settlement s.d. Approved; cukup pakai Set to Draft.'],
    ['19', 'Highlight tombol dinamis',
     'Waiting Settlement terkunci: Set to Draft + Settlement Received hijau. '
     'Setelah Set to Draft: Settlement hijau. Approved: Create Refund CN + Set to Draft hijau. '
     'Setelah refund paid: Create Refund CN & Set to Draft hilang; Create FTM Landed Cost hijau.'],
    ['20', 'Form Bill/CN dari CDM dirapikan',
     'Form yang dibuka dari CDM tanpa tombol CREATE STTF / VIEW STTF; Reset to Draft hanya satu tombol.'],
    ['21', 'COMPUTE pada FTM Landed Cost CDM',
     'Landed Cost yang dibuat dari CDM dapat di-Compute meski tertaut FTM '
     '(melewati blokir viin_foreign_trade "cannot recompute").'],
    ['22', 'Tab Journal Items pada Landed Cost',
     'Setelah LC di-Validate (ada Journal Entry, mis. JLC/…), form Landed Cost menampilkan '
     'tab Journal Items berisi baris Debit–Credit dari journal accounting tersebut '
     '(Account, Label, Debit, Credit). Tab tersembunyi selama LC masih Draft.'],
])

# ============ 3 ============
h1('3. Prasyarat Instalasi & Master Data')
h2('3.1 Sebelum Install / Upgrade')
number('Pastikan modul custom_import, stock_landed_costs, sequence_reset_period, dan od_journal_sequence sudah terpasang.')
number('Install/upgrade terlebih dahulu di database testing/UAT — jangan langsung production.')
number('Pastikan Chart of Accounts memiliki akun aktif berikut:')
table(['Kode Akun', 'Nama / Fungsi', 'Pemakaian'], [
    ['1720002', 'Uang Muka Jaminan Container', 'Deposit Account untuk produk jaminan container'],
    ['1720003', 'Uang Muka Jaminan Sewa Container', 'Deposit Account untuk produk jaminan sewa'],
    ['6130006', 'Biaya Sewa Container', 'Charge Account settlement untuk deposit sewa container'],
    ['6130016', 'Biaya Perbaikan dan Kebersihan Container', 'Charge Account settlement untuk deposit jaminan container'],
])
para('Catatan: Saat install/upgrade, modul akan mereaktivasi akun 1720002 dan 1720003 jika sempat '
     'di-deprecate, serta menyesuaikan prefix sequence dokumen secara otomatis.', italic=True)

h2('3.2 Product Master yang Diizinkan (Deposit Lines)')
para('Pada tab Deposit / Initial Charges, Product / Charge hanya boleh:')
table(['Product', 'Deposit Account Auto'], [
    ['Uang Muka Jaminan Container', '1720002'],
    ['Uang Muka Jaminan Sewa Container', '1720003'],
])
para('Deposit Account terisi otomatis: sistem memakai Expense Account yang dikonfigurasi pada product '
     'bila kodenya sesuai (1720002/1720003), atau mencari akun tersebut langsung di Chart of Accounts.', italic=True)

h2('3.3 Product untuk Settlement (Landed Cost) — Auto-fill Mapping')
para('Saat tombol Settlement diklik, kolom Landed Cost Product / Charge dan Charge Account pada tab '
     'Settlement terisi otomatis (read-only) berdasarkan tabel mapping berikut:')
table(['Deposit / Initial Charges (Product)', 'Landed Cost Product / Charge (Auto)', 'Charge Account (Auto)'], [
    ['Uang Muka Jaminan Sewa Container', 'Biaya Sewa Container (Demurrage)', '6130006 Biaya Sewa Container'],
    ['Uang Muka Jaminan Container', 'Biaya Perbaikan dan Kebersihan Container', '6130016 Biaya Perbaikan dan Kebersihan Container'],
])
para('Product landed cost hasil mapping harus ber-flag Is a Landed Cost = True. Pastikan kedua product '
     'tersebut ada di master data. JANGAN mengaktifkan produk Uang Muka Jaminan sebagai landed cost.', italic=True)

h2('3.4 Journal')
bullet('Landed Cost Journal (type: General) — otomatis terisi saat FTM Reference dipilih.')
bullet('Purchase Journal — untuk Vendor Bill deposit & Vendor Credit Note refund. '
       'Pastikan sequence journal: BILL/%(range_year)s/%(rom_month)s/ dan refund RBILL/%(range_year)s/%(rom_month)s/.')
bullet('Bank/Cash Journal — untuk Register Payment. Penomoran entry payment mengikuti Entry Sequence '
       'journal tersebut (contoh BB/%(range_year)s/%(range_rom_month)s/ atau KB/…), reset bulanan.')

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
    ['5', 'Waiting Settlement', 'waiting_settlement', 'Input/kunci refund & potongan; Cancel disembunyikan', 'Finance (Set to Draft → Waiting Settlement)'],
    ['6', 'Settlement Received', 'settlement_received', 'Nilai settlement sudah dikunci/diterima', 'Finance (Set to Draft → Waiting Settlement)'],
    ['7', 'Waiting Approval', 'waiting_approval', 'Menunggu approval (balance harus 0)', 'Finance (Set to Draft → Waiting Settlement)'],
    ['8', 'Approved', 'approved', 'Disetujui; buat Refund CN & FTM Landed Cost', 'Management (Set to Draft → Waiting Settlement; Cancel disembunyikan)'],
    ['9', 'Done', 'done', 'Mark Posted diklik; dokumen accounting terposting; proses selesai', 'Accounting (Set to Draft → Waiting Settlement bila deposit sudah dibayar)'],
    ['10', 'Cancelled', 'cancel', 'Dibatalkan (final); Set to Draft disembunyikan', '—'],
])
para('Administrator memiliki full permission pada seluruh status di atas.', italic=True)
para('Catatan: Tombol Cancel disembunyikan pada Waiting Settlement, Settlement Received, Waiting Approval, '
     'dan Approved. Koreksi settlement memakai Set to Draft. Status Cancelled bersifat final (tanpa Set to Draft).', italic=True)

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
    ['Deposit Account', '1720002/1720003 auto dari product', 'Tidak (read-only)', 'Hide (default)'],
    ['Vendor Bill', 'Link bill yang dibuat', 'Tidak (read-only)', 'Hide (default)'],
    ['Note', 'Catatan baris', 'Tidak (read-only)', 'Hide (default)'],
])
para('Baris dapat diedit saat state: Draft, Waiting Confirmation — kecuali deposit bill sudah dibayar '
     '(deposit_bills_paid): tab Deposit tetap read-only meskipun dokumen dikembalikan ke Draft / Waiting Settlement.', italic=True)

h2('7.4 Tab Settlement: Refund / Deduction / Charges')
table(['Kolom', 'Fungsi', 'Editable', 'Show/Hide'], [
    ['Source Deposit Line', 'Baris deposit asal (auto saat Settlement)', 'Tidak', 'Hide (default)'],
    ['Landed Cost Product / Charge', 'Auto dari mapping produk deposit (bab 3.3)', 'Tidak (read-only)', 'Selalu tampil'],
    ['Description', 'Deskripsi charge', 'Tidak', 'Hide (default)'],
    ['Container Vendor', 'Vendor settlement', 'Tidak', 'Show (default)'],
    ['Original Deposit Amount', 'Nilai deposit asal', 'Tidak', 'Show (default)'],
    ['Refund Amount', 'Jumlah yang dikembalikan vendor', 'Ya', 'Selalu tampil'],
    ['Taxes', 'Pajak untuk Refund Credit Note', 'Ya', 'Show (default)'],
    ['Final Deducted Charge', 'Auto = Original − Refund', 'Tidak (auto)', 'Show (default)'],
    ['Charge Type', 'detention/demurrage/rental/cleaning/repair/admin/other', 'Ya', 'Selalu tampil'],
    ['Landed Cost Split Method', 'Metode split landed cost', 'Tidak', 'Hide (default)'],
    ['Charge Account', 'Auto dari mapping (6130006 / 6130016)', 'Tidak', 'Hide (default)'],
    ['Refund Credit Note', 'Link CN refund', 'Tidak', 'Hide (default)'],
    ['FTM Landed Cost', 'Link stock.landed.cost', 'Tidak', 'Hide (default)'],
    ['Note', 'Catatan', 'Tidak', 'Hide (default)'],
])
para('Kolom yang dapat diedit saat Waiting Settlement (belum terkunci) hanya: Refund Amount, Taxes, '
     'Charge Type. Setelah Settlement diklik lagi (Save/kunci) atau Settlement Received, baris menjadi '
     'read-only. Set to Draft membuka kunci dan mengembalikan ke Waiting Settlement (jika deposit '
     'sudah dibayar). Tab Deposit terkunci permanen setelah deposit bill dibayar.', italic=True)

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
para('Pada setiap stage di bawah ini disertakan keterangan apakah Journal Accounting tercipta. '
     'Jika ya, ditampilkan contoh Debit–Credit dengan akun COA yang dipakai di database Karusindo '
     '(angka contoh bersifat ilustrasi; nilai aktual mengikuti dokumen Anda).')

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
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 2 — Submit → Waiting Confirmation (Group: User)')
number('Klik tombol Submit.')
number('Validasi: minimal 1 baris deposit harus ada.')
number('Status berubah menjadi Waiting Confirmation.')
para('Tombol aktif: Confirm (Management) | Print Container Deposit | Set to Draft | Cancel', bold=True)
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 3 — Confirm → Confirmed (Group: Management)')
para('Tujuan: Konfirmasi pengajuan dari user impor. Hanya group Management (atau Administrator) '
     'yang dapat melihat dan mengeksekusi tombol Confirm.')
number('Management memeriksa dokumen (bisa dari print out Container Deposit).')
number('Klik Confirm. Sistem re-sync data FTM (PO, picking, operasi).')
number('Status → Confirmed.')
para('Tombol aktif: Create Deposit Bill (Finance) | Mark Deposit Paid (Finance) | Set to Draft | Cancel', bold=True)
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 4a — Create Deposit Bill (Group: Finance)')
para('Tujuan: Membuat Vendor Bill untuk pencatatan uang muka jaminan.')
number('Klik Create Deposit Bill.')
number('Sistem membuat 1 Vendor Bill per Vendor (group by vendor). Saat create, bill masih Draft '
       '(nomor "/") — belum ada journal.')
number('Buka daftar Bills → pilih bill → klik Register Payment. Bill yang masih Draft akan '
       'otomatis di-Post terlebih dahulu, lalu wizard pembayaran terbuka.')
para('Pembayaran dilakukan per vendor: jika bill yang dipilih berasal dari vendor yang berbeda, '
     'Register Payment diblokir dengan pop-up yang menampilkan daftar vendornya. Pilih hanya '
     'bill dari vendor yang sama, lalu ulangi Register Payment untuk masing-masing vendor.', italic=True)
para('Daftar Bills dari CDM: Register Payment highlighted; tanpa New / Upload / Create Landed Costs. '
     'Cancel pada daftar Bills melepas tautan bill (jika belum ada payment).', italic=True)
para('Setelah semua baris ter-bill: Create Deposit Bill tersembunyi; Mark Deposit Paid highlighted.', italic=True)

para('Journal Accounting Terbentuk: YA — saat Vendor Bill di-Post, lalu saat Register Payment.', bold=True)
para('Contoh 1 — Post Vendor Bill (BILL/YYYY/Romawi/####), deposit Sewa Container Rp 2.500.000 + PPN 11%:')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Uang Muka Jaminan Sewa Container', '1720003', '2.500.000', '—',
     'Mencatat uang muka jaminan sebagai aset sementara (bukan biaya impor)'],
    ['PPN Masukan Lokal', '1500001', '275.000', '—',
     'PPN Masukan atas bill deposit (jika baris memakai pajak PPN Lokal 11%)'],
    ['Hutang Dagang IDR', '2101001', '—', '2.775.000',
     'Kewajiban kepada vendor container atas bill deposit'],
])
para('Jika product = Uang Muka Jaminan Container, Debit memakai 1720002 (bukan 1720003).', italic=True)
para('Contoh 2 — Register Payment bill di atas melalui Bank BCA (entry BB/YYYY/Romawi/####):')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Hutang Dagang IDR', '2101001', '2.775.000', '—',
     'Melunasi hutang vendor atas deposit bill'],
    ['Bank BCA - 3863018877', '1102001', '—', '2.775.000',
     'Kas keluar dari bank; jika bayar via Kas Besar → Credit 1101040'],
])
para('Penomoran: Bill = BILL/YYYY/Romawi/####; Payment = sequence journal Bank/Kas (BB/… atau KB/…).', italic=True)

h2('Stage 4b — Mark Deposit Paid → Deposit Paid (Group: Finance)')
number('Setelah pembayaran dilakukan, klik Mark Deposit Paid.')
number('Validasi: Deposit Amount > 0; Vendor Bill deposit harus sudah dibuat; dan SEMUA bill harus '
       'berstatus Posted serta Paid / In Payment. Jika ada bill yang belum dibayar penuh, sistem '
       'menampilkan daftar bill tersebut dan status tidak berubah.')
number('Status → Deposit Paid.')
para('Jurnal Accounting: tidak ada.', bold=True)
para('(Hanya mengubah status dokumen CDM; journal sudah terbentuk di Stage 4a.)', italic=True)

h2('Stage 5 — Settlement → Waiting Settlement (Group: Finance)')
para('Tujuan: Memulai proses settlement setelah container dikembalikan vendor.')
number('Klik Settlement (klik pertama).')
number('Sistem generate baris settlement dari baris deposit. Landed Cost Product / Charge dan '
       'Charge Account otomatis terisi dari tabel mapping (bab 3.3) dan bersifat read-only.')
number('Status → Waiting Settlement. Tombol Settlement tetap highlighted (hijau) — input masih terbuka.')
number('Isi Refund Amount per baris; Final Deducted Charge otomatis = Original − Refund.')
number('Sesuaikan Charge Type dan Taxes bila perlu, lalu klik Settlement lagi (klik kedua = Save).')
number('Baris settlement terkunci (settlement_locked). Tombol yang di-highlight hijau: '
       'Set to Draft dan Settlement Received. Refund Amount tidak bisa diedit tanpa Set to Draft.')
para('Koreksi Refund Amount: klik Set to Draft → kembali Waiting Settlement, kunci dibuka → perbaiki → '
     'klik Settlement lagi untuk mengunci. Tombol Cancel disembunyikan di tahap ini.', italic=True)
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 6 — Settlement Received (Group: Finance)')
number('Klik Settlement Received setelah nilai settlement final dari vendor diterima.')
number('Validasi: settlement lines ada; refund/charge tidak negatif.')
number('Status → Settlement Received.')
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 7 — Request Approval → Waiting Approval (Group: Finance)')
number('Klik Request Approval.')
number('Validasi: Settlement Balance harus = 0.')
number('Status → Waiting Approval.')
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 8 — Approve → Approved (Group: Management)')
number('Management memeriksa dan klik Approve.')
number('Status → Approved.')
para('Tombol aktif (sebelum refund dibayar): Create Refund Credit Note (hijau) | Set to Draft (hijau) | '
     'Create FTM Landed Cost (polos) | Mark Posted (polos). Cancel disembunyikan.', bold=True)
para('Jurnal Accounting: tidak ada.', bold=True)

h2('Stage 9a — Create Refund Credit Note (Group: Accounting)')
para('Tujuan: Membuat Vendor Credit Note untuk nilai refund dari vendor.')
number('Klik Create Refund Credit Note.')
number('Sistem membuat CN per vendor untuk baris refund > 0 yang belum ber-CN (masih Draft — belum journal).')
number('Form CN dari CDM: tanpa CREATE STTF / VIEW STTF; Reset to Draft hanya satu tombol.')
number('Buka CN → Post → Register Payment / rekonsiliasi hingga status Paid.')
para('Setelah SEMUA Refund Credit Note Posted & Paid: Create Refund Credit Note dan Set to Draft '
     'hilang; Create FTM Landed Cost menjadi hijau.', italic=True)

para('Journal Accounting Terbentuk: YA — saat Credit Note di-Post, lalu saat Register Payment (kas masuk).', bold=True)
para('Contoh 1 — Post Vendor Credit Note (RBILL/YYYY/Romawi/####), refund Rp 500.000 + PPN 11% '
     '(contoh dari settlement Sewa Container):')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Hutang Dagang IDR', '2101001', '555.000', '—',
     'Mengurangi hutang / membentuk saldo hutang negatif siap direkonsiliasi dengan refund'],
    ['Uang Muka Jaminan Sewa Container', '1720003', '—', '500.000',
     'Clear sebagian aset uang muka sesuai nilai refund'],
    ['PPN Masukan Lokal', '1500001', '—', '55.000',
     'Menyesuaikan PPN Masukan terkait refund (jika CN memakai pajak)'],
])
para('Contoh 2 — Register Payment / penerimaan refund ke Bank BCA:')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Bank BCA - 3863018877', '1102001', '555.000', '—',
     'Kas masuk dari vendor atas refund deposit'],
    ['Hutang Dagang IDR', '2101001', '—', '555.000',
     'Merealisasikan pelunasan / rekonsiliasi CN refund'],
])
para('Penomoran: CN = RBILL/YYYY/Romawi/####; Payment = sequence journal Bank/Kas yang dipakai.', italic=True)

h2('Stage 9b — Create FTM Landed Cost (Group: Accounting)')
para('Tujuan: Membebankan HANYA Final Deducted Charge ke biaya barang impor.')
number('Pastikan Transfers/Receipts dari FTM ada dan setiap baris charge > 0 memiliki Landed Cost Product.')
number('Klik Create FTM Landed Cost → sistem membuat draft stock.landed.cost tertaut FTM & CDM '
       '(belum ada journal; tab Journal Items belum tampil).')
number('Buka Landed Cost → klik Compute (diizinkan untuk LC dari CDM sejak v49) → Validate.')
number('Setelah Validate berhasil: status LC Posted/Done, field Journal Entry terisi (mis. JLC/2026/VIII/0001), '
       'dan tab Journal Items muncul di samping Additional Costs serta Valuation Adjustments.')
para('Tab Journal Items (sejak modul v16.0.1.0.50): menampilkan baris account.move.line dari journal entry LC '
     '(Account, Label, Debit, Credit — read-only, dengan total). Gunakan tab ini untuk memeriksa '
     'transaksi accounting tanpa membuka form Journal Entry terpisah.', italic=True)
para('Catatan: Original Value = stock valuation layer receipt (bukan Taxable Value FTM). '
     'Additional Landed Cost = Final Deduction. Saat Validate: porsi qty on-hand → nilai stok (1300000); '
     'porsi sudah keluar (“already out”) → HPP/COGS produk (5201000) melalui 1320002.', italic=True)

para('Journal Accounting Terbentuk: YA — saat Landed Cost di-Validate (bukan saat Create / Compute).', bold=True)
para('Contoh — Validate LC Final Deduction Rp 1.900.000 (semua qty masih di gudang), '
     'charge account Biaya Sewa Container:')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Persediaan Penjualan', '1300000', '1.900.000', '—',
     'Menambah nilai persediaan sesuai Additional Landed Cost (porsi on-hand)'],
    ['Biaya Sewa Container (Demurrage)', '6130006', '—', '1.900.000',
     'Contra / clearing akun charge LC; untuk jaminan container biasanya 6130016'],
])
para('Jika seluruh qty sudah keluar saat Validate, net Persediaan = 0 dan seluruh Additional LC masuk '
     'Debit 5201000 (terlihat di tab Journal Items sebagai baris berlabel “already out”). '
     'Itu perilaku standar Odoo, bukan kesalahan distribusi.', italic=True)

h2('Stage 10 — Mark Posted → Done (Group: Accounting)')
para('Tujuan: Menyelesaikan proses. Posted dan Done adalah satu langkah.')
number('Klik Mark Posted.')
number('Validasi: jika ada Final Deducted Charge > 0, FTM Landed Cost harus sudah dibuat.')
number('Status langsung → Done. Proses Container Deposit Management selesai.')
para('Jurnal Accounting: tidak ada.', bold=True)
para('(Hanya menutup status dokumen CDM; journal sudah tercipta di Stage 4a, 9a, dan 9b.)', italic=True)

# ============ 9 ============
h1('9. Fungsi Setiap Tombol')
h2('9.1 Tombol Header (Action Buttons)')
table(['Tombol', 'Terlihat di Status', 'Group', 'Fungsi / Validasi Utama'], [
    ['Submit', 'Draft', 'User', 'Kirim ke Waiting Confirmation; minimal 1 deposit line'],
    ['Print Container Deposit', 'Draft, Waiting Confirmation, Confirmed', 'User', 'Cetak PDF pengajuan ke Management'],
    ['Confirm', 'Waiting Confirmation', 'Management', 'Konfirmasi + sync FTM'],
    ['Set to Draft', 'Semua kecuali Draft; hilang di Approved setelah refund paid', 'Sesuai owner status',
     'Jika deposit sudah dibayar & dari tahap settlement+: kembali ke Waiting Settlement + buka kunci. '
     'Selain itu → Draft. Deposit bill yang sudah dibayar tidak dibatalkan.'],
    ['Create Deposit Bill', 'Confirmed, Deposit Paid (hilang jika semua baris ter-bill)', 'Finance', 'Buat Vendor Bill per vendor (BILL/…)'],
    ['Mark Deposit Paid', 'Confirmed (highlighted setelah semua baris ter-bill)', 'Finance', 'Tandai deposit dibayar; semua bill wajib Posted & Paid/In Payment'],
    ['Settlement', 'Deposit Paid, Waiting Settlement', 'Finance',
     'Klik-1: generate lines + buka input (hijau). Klik-2: kunci settlement (settlement_locked)'],
    ['Settlement Received', 'Waiting Settlement (hijau saat terkunci)', 'Finance', 'Settlement diterima; amount ≥ 0; mengunci baris'],
    ['Request Approval', 'Settlement Received', 'Finance', 'Ajukan approval; Settlement Balance = 0'],
    ['Approve', 'Waiting Approval', 'Management', 'Setujui settlement'],
    ['Create Refund Credit Note', 'Approved (hijau; hilang setelah refund paid)', 'Accounting', 'Buat Vendor Credit Note refund (RBILL/…)'],
    ['Create FTM Landed Cost', 'Approved (hijau setelah refund paid; polos sebelumnya)', 'Accounting', 'Buat draft Landed Cost FTM; Compute diizinkan'],
    ['Mark Posted', 'Approved (polos)', 'Accounting', 'Selesaikan dokumen → Done; landed cost wajib jika ada deduction'],
    ['Cancel', 'Draft s.d. Deposit Paid & Done (disembunyikan di tahap settlement/Approved)', 'Sesuai owner status',
     'Batalkan dokumen; deposit bill yang sudah dibayar tidak dibatalkan'],
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
para('Cancel tersedia pada Draft s.d. Deposit Paid serta Done; disembunyikan pada Waiting Settlement, '
     'Settlement Received, Waiting Approval, dan Approved (koreksi settlement memakai Set to Draft). '
     'Set to Draft tersedia pada semua status selain Draft dan Cancelled (dan hilang di Approved setelah refund paid). '
     'Jika deposit Vendor Bill masih Paid, tombol Set to Draft (reopen ke Draft) dan Cancel disembunyikan/diblokir. '
     'Status Cancelled bersifat final: Set to Draft disembunyikan dan diblokir di server.')

h2('10.1 Perilaku Set to Draft setelah deposit dibayar')
bullet('Dari Waiting Settlement / Settlement Received / Waiting Approval / Approved / Done: '
       'status kembali ke Waiting Settlement; kunci settlement dibuka (Refund Amount bisa diedit). '
       'Jalur ini TETAP diizinkan meskipun deposit bill masih Paid.')
bullet('Dari Cancelled: Set to Draft TIDAK tersedia (dokumen final).')
bullet('Dari Confirmed / Deposit Paid: reopen penuh ke Draft DIBLOKIR selama deposit Vendor Bill masih '
       'Paid / In Payment / Partial. Blokir dicabut setelah bill di-Reverse dan refund dibayar '
       '(payment status menjadi Reversed), atau payment dibatalkan sehingga bill tidak lagi paid.')
bullet('Deposit Vendor Bill yang masih paid tidak dibatalkan dan tetap tertaut pada jalur unlock settlement.')
bullet('Refund Credit Note / journal settlement / Landed Cost draft yang belum dibayar dibatalkan dan dilepas tautannya.')

h2('10.2 Validasi Otomatis')
bullet('DIBLOKIR jika dokumen sudah Cancelled — Set to Draft tidak diizinkan.')
bullet('DIBLOKIR jika ada FTM Landed Cost yang sudah divalidasi (state Done) — reverse landed cost terlebih dahulu.')
bullet('DIBLOKIR jika ada dokumen settlement (Refund CN / journal) yang sudah dibayar — batalkan payment-nya dulu.')
bullet('DIBLOKIR Set to Draft (ke Draft) / Cancel jika deposit Vendor Bill masih Paid / In Payment / Partial — '
       'reverse bill + lunasi refund hingga status Reversed, baru blokir dicabut.')

h2('10.3 Yang Dilakukan Sistem Saat Cancel / Set to Draft')
number('Dokumen settlement terkait yang belum dibayar di-set draft lalu dibatalkan.')
number('Landed Cost draft dibatalkan.')
number('Link refund/landed cost/journal pada settlement dibersihkan; link deposit bill yang masih paid dipertahankan '
       '(jalur unlock settlement). Deposit bill yang sudah Reversed dilepas tautannya agar Create Deposit Bill bisa diulang.')
number('Status → Cancelled (Cancel) atau Waiting Settlement / Draft (Set to Draft, tergantung apakah deposit masih paid '
       'dan stage settlement).')
para('Untuk Stage 4a (Deposit Bill), 9a (Refund Credit Note), dan 9b (FTM Landed Cost) yang sudah membentuk '
     'journal accounting, ikuti SOP detail di Bab 11 (prasyarat reverse/cancel, contoh Debit–Credit, dan dampak audit).', italic=True)

# ============ 11 ============
h1('11. SOP Cancel pada Stage 4a, 9a, dan 9b (Journal & Audit)')
para('Bab ini menjelaskan proses yang harus dilakukan SEBELUM Cancel / Set to Draft dapat dijalankan '
     'dengan bersih pada tiga stage yang menghasilkan journal accounting, lengkap dengan contoh Debit–Credit '
     'dan dampaknya terhadap audit. Akun contoh mengikuti COA Karusindo; angka bersifat ilustrasi.')

h2('11.1 Prinsip Umum')
bullet('Tombol Cancel / Set to Draft pada form CDM tidak menghapus jejak akuntansi di Bank/Kas atau valuasi stok.')
bullet('Yang dibatalkan otomatis oleh CDM hanya dokumen yang belum dibayar dan belum mengubah valuasi inventori.')
bullet('Jika uang sudah keluar/masuk atau Landed Cost sudah Validate, balikkan transaksi accounting dulu (SOP), '
       'baru dokumen CDM dibatalkan atau dibuka ulang.')
bullet('Jangan menghapus journal posted dari database. Auditor mengharapkan jejak: transaksi awal → reverse/cancel → alasan.')

h2('11.2 Stage 4a — Create Deposit Bill (Post Bill + Register Payment)')
para('Dokumen yang biasanya sudah terbentuk: Vendor Bill posted (BILL/…) dan Payment posted (BB/… atau KB/…).')
para('Contoh journal saat terbentuk (deposit Sewa Container Rp 2.500.000 + PPN 11%):')
table(['Saat', 'Akun', 'Kode', 'Debit', 'Credit'], [
    ['Post Bill', 'Uang Muka Jaminan Sewa Container', '1720003', '2.500.000', '—'],
    ['Post Bill', 'PPN Masukan Lokal', '1500001', '275.000', '—'],
    ['Post Bill', 'Hutang Dagang IDR', '2101001', '—', '2.775.000'],
    ['Payment', 'Hutang Dagang IDR', '2101001', '2.775.000', '—'],
    ['Payment', 'Bank BCA (atau Kas Besar)', '1102001 / 1101040', '—', '2.775.000'],
])

para('Proses wajib sebelum Cancel / Set to Draft CDM diizinkan (Confirmed / Deposit Paid):', bold=True)
number('Reverse deposit Vendor Bill dan lunasi refund (atau batalkan / reverse Payment hingga bill tidak lagi Paid).')
number('Pastikan payment status bill menjadi Reversed (atau unpaid setelah payment dibatalkan) — '
       'baru tombol Set to Draft / Cancel aktif kembali.')
number('Jika bill sudah unpaid: Bill → Reset to Draft → Cancel; atau di list Bills CDM pakai tombol Cancel '
       '(hanya jika belum ada payment).')
number('Baru Cancel / Set to Draft pada dokumen CDM.')
para('Catatan CDM: selama deposit Vendor Bill masih Paid / In Payment / Partial, Set to Draft (ke Draft) '
     'dan Cancel diblokir di UI dan server. Setelah reverse + refund paid (status Reversed), blokir dicabut '
     'dan tautan bill reversed dilepas agar Create Deposit Bill dapat diulang.', italic=True)

para('Contoh journal saat reverse/cancel Stage 4a:')
table(['Langkah', 'Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Reverse Payment', 'Bank BCA', '1102001', '2.775.000', '—', 'Netralisasi kas keluar'],
    ['Reverse Payment', 'Hutang Dagang IDR', '2101001', '—', '2.775.000', 'Hutang muncul lagi (bill unpaid)'],
    ['Cancel Bill', 'Hutang Dagang IDR', '2101001', '2.775.000', '—', 'Hapus hutang'],
    ['Cancel Bill', 'Uang Muka Jaminan Sewa Container', '1720003', '—', '2.500.000', 'Hapus aset uang muka'],
    ['Cancel Bill', 'PPN Masukan Lokal', '1500001', '—', '275.000', 'Hapus PPN masukan'],
])

h2('11.3 Stage 9a — Create Refund Credit Note (Post CN + Terima Refund)')
para('Dokumen yang biasanya sudah terbentuk: Vendor Credit Note posted (RBILL/…) dan Payment / penerimaan refund.')
para('Contoh journal saat terbentuk (refund Rp 500.000 + PPN 11%):')
table(['Saat', 'Akun', 'Kode', 'Debit', 'Credit'], [
    ['Post CN', 'Hutang Dagang IDR', '2101001', '555.000', '—'],
    ['Post CN', 'Uang Muka Jaminan Sewa Container', '1720003', '—', '500.000'],
    ['Post CN', 'PPN Masukan Lokal', '1500001', '—', '55.000'],
    ['Terima refund', 'Bank BCA', '1102001', '555.000', '—'],
    ['Terima refund', 'Hutang Dagang IDR', '2101001', '—', '555.000'],
])

para('Proses wajib sebelum Set to Draft CDM:', bold=True)
number('CDM memblokir jika Refund CN sudah paid/partial — batalkan / reverse payment refund terlebih dahulu.')
number('CN → Reset to Draft → Cancel (atau biarkan dibatalkan otomatis oleh Set to Draft CDM setelah unpaid).')
number('Set to Draft pada form CDM (kembali ke Waiting Settlement untuk koreksi Refund Amount). '
       'Tombol Cancel disembunyikan di tahap Approved; jalur koreksi = Set to Draft.')

para('Contoh journal saat reverse/cancel Stage 9a:')
table(['Langkah', 'Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Reverse penerimaan refund', 'Hutang Dagang IDR', '2101001', '555.000', '—', 'Saldo CN terbuka lagi'],
    ['Reverse penerimaan refund', 'Bank BCA', '1102001', '—', '555.000', 'Netralisasi kas masuk'],
    ['Cancel Credit Note', 'Uang Muka Jaminan Sewa Container', '1720003', '500.000', '—', 'Kembalikan aset uang muka'],
    ['Cancel Credit Note', 'PPN Masukan Lokal', '1500001', '55.000', '—', 'Kembalikan PPN'],
    ['Cancel Credit Note', 'Hutang Dagang IDR', '2101001', '—', '555.000', 'Hapus dampak CN'],
])
para('Setelah koreksi angka Refund Amount, buat Credit Note baru (nomor RBILL baru). '
     'Jangan mengedit CN posted lama tanpa jejak.', italic=True)

h2('11.4 Stage 9b — Create FTM Landed Cost (Compute + Validate)')
para('Draft LC (baru Create/Compute) belum membentuk journal. Journal terbentuk saat Validate.')
para('Contoh journal saat Validate (semua qty masih di gudang, Final Deduction Rp 1.900.000):')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Persediaan Penjualan', '1300000', '1.900.000', '—', 'Naikkan nilai stok (porsi on-hand)'],
    ['Biaya Sewa Container (Demurrage)', '6130006', '—', '1.900.000', 'Clearing charge LC (jaminan container: 6130016)'],
])
para('Jika sebagian qty sudah keluar, porsi terjual biasanya Debit 5201000 Pembelian Barang Penjualan (COGS).', italic=True)

para('Proses wajib sebelum Cancel / Set to Draft CDM:', bold=True)
number('CDM memblokir jika LC state = done (sudah Validate).')
number('Reverse Landed Cost di form LC (prosedur inventori) — menghasilkan journal balik dan koreksi stock valuation layer.')
number('Setelah LC tidak lagi done / sudah di-reverse, baru Set to Draft atau Cancel CDM.')
number('Jika LC masih draft: CDM dapat membatalkan LC draft tanpa journal (karena journal belum ada).')

para('Contoh journal saat Reverse Landed Cost:')
table(['Akun', 'Kode', 'Debit', 'Credit', 'Keterangan'], [
    ['Biaya Sewa Container (Demurrage)', '6130006', '1.900.000', '—', 'Balik clearing charge'],
    ['Persediaan Penjualan', '1300000', '—', '1.900.000', 'Turunkan kembali nilai stok'],
])
para('Qty stok tidak berubah; yang berubah hanya nilai. Jika ada porsi COGS 5201000, porsi itu juga dibalik.', italic=True)

h2('11.5 Ringkasan: Kapan Bisa Cancel Langsung')
table(['Stage', 'Kondisi dokumen', 'Cancel / Set to Draft CDM langsung?', 'Yang harus dilakukan dulu'], [
    ['4a', 'Bill draft', 'Ya (atau Cancel di list Bills)', '—'],
    ['4a', 'Bill posted, belum bayar', 'Ya / Cancel list Bills', '—'],
    ['4a', 'Bill paid', 'Diblokir (Set to Draft ke Draft / Cancel)', 'Reverse bill + refund paid (status Reversed) → baru Set to Draft / Cancel'],
    ['9a', 'CN draft / posted unpaid', 'Ya (Set to Draft)', '—'],
    ['9a', 'CN paid', 'Diblokir', 'Reverse payment refund → Set to Draft'],
    ['9b', 'LC draft', 'Ya', 'CDM batalkan LC draft'],
    ['9b', 'LC validated (done)', 'Diblokir', 'Reverse LC terlebih dahulu'],
])

h2('11.6 Dampak terhadap Audit Accounting')
bullet('Audit trail tetap utuh: nomor BILL / RBILL / BB / KB / LC serta journal reverse tetap di General Ledger — ini yang diharapkan auditor.')
bullet('Berbahaya bagi audit: mengubah status CDM tanpa membalik journal terkait → CDM “kosong/ulang” tetapi Bank, Hutang, Uang Muka, atau Persediaan masih berisi angka lama.')
bullet('Dokumentasikan alasan di chatter CDM dan pada dokumen accounting (kesalahan input, koreksi refund, LC salah, dll.).')
bullet('Perhatian cut-off: reverse di periode berbeda dari transaksi awal muncul sebagai koreksi periode berjalan — siapkan penjelasan management.')
bullet('Stage 9b paling sensitif (valuasi inventori & HPP). Stage 4a/9a lebih ke kas, hutang, dan uang muka.')
bullet('Jangan menghapus entry posted dari database; selalu gunakan Cancel / Reverse standar Odoo.')

# ============ 12 ============
h1('12. Ringkasan Jurnal Accounting per Langkah')
table(['Langkah', 'Membuat Journal?', 'Jenis Dokumen', 'Pola Jurnal (sederhana)'], [
    ['Submit / Confirm', 'Tidak', '—', '—'],
    ['Create Deposit Bill + Post Bill', 'Ya', 'Vendor Bill (BILL/YYYY/Romawi/####)', 'Dr Uang Muka 1720002/03 | Cr Utang Usaha'],
    ['Register Payment Bill', 'Ya', 'Payment', 'Dr Utang Usaha | Cr Bank'],
    ['Mark Deposit Paid', 'Tidak', 'Status saja', '—'],
    ['Settlement / Received / Request / Approve', 'Tidak', '—', '—'],
    ['Create Refund CN + Post CN', 'Ya', 'Vendor Credit Note (RBILL/YYYY/Romawi/####)', 'Dr Utang Usaha | Cr Uang Muka 1720002/03'],
    ['Payment / settle CN refund', 'Ya', 'Payment', 'Dr Bank | Cr Utang Usaha (kas masuk)'],
    ['Create + Validate FTM Landed Cost', 'Ya', 'stock.landed.cost via Landed Cost Journal', 'Dr Stock/Expense | Cr Interim/Contra (hanya Final Deduction)'],
    ['Mark Posted (→ Done) / Cancel', 'Tidak', 'Status saja', '—'],
])

h2('12.1 Penomoran Dokumen Accounting')
bullet('Draft bill/CN selalu bernomor "/" sampai di-Post.')
bullet('Saat Post: Vendor Bill mengikuti sequence journal BILL/YYYY/Romawi/#### dan Credit Note '
       'RBILL/YYYY/Romawi/####, menyambung nomor terakhir pada bulan berjalan.')
bullet('Journal entry payment dari CDM mengikuti Entry Sequence journal Bank/Kas yang dipilih '
       '(contoh BB/YYYY/Romawi/#### atau KB/YYYY/Romawi/####), menyambung nomor terakhir journal.')
bullet('Dokumen lama berformat CD-BILL-*/CD-CN-* (versi sebelumnya) tidak diubah.')

h2('12.2 Apa yang TIDAK boleh masuk Landed Cost')
bullet('Nilai penuh deposit awal (uang muka jaminan) — tetap di aset 1720002/1720003 sampai '
       'di-clear oleh refund/deduction.')
bullet('Produk Uang Muka Jaminan Container/Sewa — jangan diaktifkan sebagai Landed Cost product.')

# ============ 13 ============
h1('13. Aturan Settlement Balance & Validasi')
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

# ============ 14 ============
h1('14. Contoh Kasus End-to-End')
para('Skenario: Import FTM-ABC; deposit container Rp 10.000.000; setelah return, vendor refund '
     'Rp 7.500.000 dan potong detention Rp 2.500.000.')
h2('14.1 Langkah Operasional')
number('[User] Buat dokumen CD → pilih FTM → isi baris Uang Muka Jaminan Container Rp 10.000.000 (akun 1720002 auto) → Print Container Deposit → Submit.')
number('[Management] Confirm.')
number('[Finance] Create Deposit Bill → Post Bill (BILL/2026/VII/…) → Register Payment Rp 10.000.000 → Mark Deposit Paid (tombol highlighted setelah bill dibayar).')
number('[Finance] Settlement (klik-1) → auto-fill product & account → isi Refund 7.500.000 → '
       'Settlement (klik-2, kunci) → Settlement Received → Request Approval (balance 0).')
number('[Management] Approve.')
number('[Accounting] Create Refund Credit Note Rp 7.500.000 → Post (RBILL/…) → bayar/rekonsiliasi hingga Paid '
       '→ di form CDM tombol Create Refund CN & Set to Draft hilang; Create FTM Landed Cost hijau.')
number('[Accounting] Create FTM Landed Cost Rp 2.500.000 → Compute → Validate → cek tab Journal Items.')
number('[Accounting] Mark Posted → status langsung Done. Selesai.')
h2('14.2 Ringkasan Dampak Accounting')
table(['Event', 'Dampak'], [
    ['Bayar deposit', 'Aset Uang Muka +10jt; Bank −10jt'],
    ['Refund CN + kas masuk', 'Aset Uang Muka −7,5jt; Bank +7,5jt'],
    ['Validate Landed Cost', 'Biaya/Stock +2,5jt (final deduction saja)'],
    ['Saldo akhir Uang Muka terkait transaksi', '0'],
])

# ============ 15 ============
h1('15. Opsi Show/Hide Kolom (Tree View)')
para('Semua tree view mendukung pengaturan kolom melalui ikon pengaturan (⚙ / slider) di pojok kanan '
     'header tabel. Preferensi kolom tersimpan per user.')
h2('15.1 List Utama Container Deposit Management')
table(['Kolom', 'Default'], [
    ['Internal Reference, Status', 'Selalu tampil'],
    ['FTM Reference, Container Vendor, Deposit Amount, Settlement Balance', 'Show'],
    ['Form No, Custom Doc Number, AWB/BL, Clearance Date', 'Hide'],
    ['Initial Charge, Refund Amount, Final Deducted Charge', 'Hide'],
    ['Vendor Bills / Refunds / Landed Costs (jumlah)', 'Hide'],
])
h2('15.2 Tab pada Form')
bullet('Deposit / Initial Charges: Description, Deposit Account, Vendor Bill, Note dapat di-show/hide (default hide).')
bullet('Settlement: Source Deposit Line, Description, Split Method, Charge Account, Refund Credit Note, FTM Landed Cost, Note dapat di-show/hide (default hide).')
bullet('FTM Operations: UOM, Currency, dan Taxable Value dapat di-show/hide (default hide).')

# ============ 16 ============
h1('16. Troubleshooting Umum')
table(['Gejala / Error', 'Penyebab Umum', 'Solusi'], [
    ['Please input at least one deposit line', 'Submit tanpa baris', 'Tambah baris deposit'],
    ['You are not allowed to … this Container Deposit document', 'User tidak punya group yang sesuai', 'Assign group yang benar di Settings → Users'],
    ['Deposit amount must be greater than zero', 'Mark Deposit Paid tanpa nilai', 'Isi amount > 0'],
    ['The following Vendor Bills are not fully paid yet', 'Mark Deposit Paid sebelum semua bill Posted & Paid', 'Post dan Register Payment seluruh deposit bill terlebih dahulu'],
    ['Settlement balance must be zero…', 'Refund + Deduction ≠ Deposit', 'Sesuaikan angka hingga balance 0'],
    ['No receipt/transfer linked from FTM', 'FTM tanpa picking', 'Pastikan FTM punya Transfers'],
    ['Product must have Landed Cost enabled', 'Produk landed cost hasil mapping belum ber-flag Is a Landed Cost', 'Aktifkan Is a Landed Cost pada produk Biaya Sewa Container / Biaya Perbaikan dan Kebersihan Container'],
    ['Account 1720002/03 not found', 'Akun belum ada / deprecated', 'Buat/aktifkan akun; upgrade modul'],
    ['Deposit Account must be either 1720002 … or 1720003 …', 'Akun deposit di luar 1720002/1720003 (mis. akun lama 1700002/1700003)', 'Pastikan Expense Account product = 1720002/1720003; upgrade modul ke 16.0.1.0.49'],
    ['Cannot cancel … validated FTM Landed Cost', 'Landed cost sudah Validate', 'Reverse landed cost dahulu bila perlu dibuka'],
    ['Cannot cancel … settlement document … paid', 'Refund CN/journal settlement sudah dibayar', 'Batalkan payment settlement dahulu'],
    ['Please create FTM landed cost before Posted', 'Ada deduction tapi belum LC', 'Create FTM Landed Cost dulu'],
    ['Nomor CN tampil "/"', 'CN masih draft (belum Post)', 'Post CN; nomor RBILL/… otomatis terisi'],
    ['Another entry with the same name already exists', 'Penomoran journal entry payment bentrok', 'Sudah ditangani: payment CDM memakai sequence journal Bank/Kas. Upgrade CDM + pastikan sequence_reset_period ≥ 15.0.1.0.1'],
    ['This landed cost was generated from custom declaration, so you can not recompute it', 'Blokir Compute dari viin_foreign_trade karena No FTM terisi', 'Upgrade CDM ≥ 16.0.1.0.49 — LC dari CDM boleh di-Compute'],
    ['Refund Amount masih bisa diedit setelah Settlement', 'Belum klik Settlement kedua kali (belum terkunci)', 'Klik Settlement lagi untuk Save/kunci; atau lanjut Settlement Received'],
    ['KeyError rom_month saat save', 'Modul od_journal_sequence versi lama', 'Upgrade od_journal_sequence ≥ 14.0.4.0.1'],
    ['Partner must have Vendor status', 'Partner bukan vendor', 'Centang Is Vendor pada partner'],
])

# ============ 17 ============
h1('17. Checklist UAT')
for item in [
    'Upgrade modul ke 16.0.1.0.49 di DB test; akun 1720002 & 1720003 aktif; sequence_reset_period ≥ 15.0.1.0.1.',
    'Nomor dokumen baru berformat CD/YYYY/Romawi/##### dan reset tiap bulan.',
    'Lima group (User, Management, Finance, Accounting, Administrator) muncul di Settings → Users.',
    'User tanpa group tidak melihat menu; setiap tombol hanya tampil untuk group-nya.',
    'Deposit Account terisi otomatis 1720002/1720003 saat pilih Product / Charge, dan dokumen bisa di-Save tanpa error.',
    'Print Container Deposit menghasilkan PDF pengajuan.',
    'Confirm hanya bisa oleh Management; Approve hanya oleh Management.',
    'Create Deposit Bill → daftar Bills tanpa New/Upload/Create Landed Cost; Register Payment hijau; multi-vendor diblokir.',
    'Register Payment: draft bill auto-Post; journal entry payment berformat BB/… atau KB/… sesuai journal.',
    'Setelah semua baris ter-bill: Create Deposit Bill hilang; Mark Deposit Paid highlighted.',
    'Mark Deposit Paid ditolak jika ada bill yang belum Posted & Paid/In Payment.',
    'Settlement klik-1: auto-fill product & account; klik-2: kunci Refund Amount; Set to Draft + Settlement Received hijau.',
    'Set to Draft setelah deposit paid: kembali Waiting Settlement (bukan Draft); tab Deposit tetap read-only; Cancel disembunyikan.',
    'Settlement: Final Deduction auto; Request Approval gagal jika balance ≠ 0.',
    'Approved: Create Refund CN + Set to Draft hijau; setelah refund Paid → keduanya hilang; Create FTM Landed Cost hijau.',
    'Form CN dari CDM tanpa CREATE STTF; Reset to Draft hanya satu tombol.',
    'Create FTM Landed Cost → Compute sukses → Validate → tab Journal Items tampil berisi Debit/Credit journal LC.',
    'Mark Posted langsung ke Done.',
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
    ['Versi yang dianalisis', '16.0.1.0.50 (file panduan tetap v16_1_0_49)'],
    ['Perubahan utama sejak 16.0.1.0.40',
     'Settlement lock + highlight dinamis; Set to Draft dari settlement → Waiting Settlement; '
     'Cancel disembunyikan di tahap settlement; form Bill/CN dari CDM dirapikan (tanpa STTF); '
     'setelah refund paid → Create FTM Landed Cost hijau; COMPUTE LC dari CDM diizinkan; '
     'payment Bank/Kas mengikuti sequence journal standar; Bab 11 SOP Cancel Stage 4a/9a/9b; '
     'tab Journal Items pada Landed Cost setelah Validate (v50)'],
    ['Format panduan', 'Microsoft Word (.docx)'],
    ['Bahasa', 'Indonesia'],
    ['Tanggal', '5 August 2026'],
])
para('Dokumen ini disusun berdasarkan evaluasi source code modul (models, views, hooks, security, report, '
     'migrations) hingga versi 16.0.1.0.50. Detail akun Debit/Kredit Landed Cost final dapat berbeda antar '
     'database tergantung konfigurasi COA, product category, dan inventory valuation method. '
     'Bab 11 merujuk contoh akun COA Karusindo untuk SOP Cancel Stage 4a/9a/9b. '
     'Tab Journal Items pada form LC muncul setelah Validate (field Journal Entry terisi).', italic=True)

doc.save(DOC_PATH)
print('Saved:', DOC_PATH)
