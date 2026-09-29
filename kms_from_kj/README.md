# Database KMS dari dump KJ (Odoo 16 Community)

Membuat **database terpisah** untuk **PT. Karusindo Mega Saintifik (KMS)** dari backup
**PT. Karunia Jasindo (KJ)**: master data disalin, transaksi & beginning balance dihapus.

## Data yang dipertahankan

| Area | Model / data |
|------|----------------|
| Accounting setup | COA (`account.account`), journals, account groups |
| Perpajakan | `account.tax`, tax groups, fiscal positions |
| Partners | Customer & vendor (`res.partner`) |
| Products | `product.template` / `product.product`, categories, UoM |
| Inventory master | Warehouses, locations, routes (tanpa stock qty/moves) |

## Data yang dibersihkan / diganti

- Semua transaksi: SO/PO, invoice/bill, payment, journal entries, stock moves/pickings, valuation
- Beginning balance / opening entries
- Identitas perusahaan → diganti ke KMS
- Sequence dokumen di-reset (mulai ulang untuk KMS)
- UUID database (otomatis berubah jika duplicate via DB manager; dicek ulang di skrip)

## Prasyarat

1. Odoo 16 Community + **modul custom yang sama** dengan KJ (path addons sama).
2. PostgreSQL yang sama dengan instance Odoo.
3. File dump KJ (salah satu):
   - `kj.dump` (custom format `pg_dump -Fc`), atau
   - `kj.sql`, atau
   - ZIP dari Odoo DB manager (berisi dump + filestore).
4. Filestore KJ (jika restore dari `pg_dump` saja): salin ke
   `~/.local/share/Odoo/filestore/<nama_db_kms>` (path bisa berbeda sesuai `data_dir`).

## Alur kerja (ringkas)

```text
[1] Backup KJ (aman)
[2] Restore dump → database baru, mis. kms
[3] Salin filestore (jika perlu)
[4] Jalankan Odoo terhadap DB kms (modul custom harus load)
[5] odoo-bin shell -d kms < sanitize_kms.py
[6] Verifikasi checklist di bawah
[7] Ganti master password / user admin bila perlu; set email server KMS
```

Detail perintah: lihat `restore_db.sh` dan `sanitize_kms.py`.

## Data perusahaan KMS yang perlu Anda isi

Edit `company_kms.json` sebelum menjalankan sanitasi:

- `name`, `street`, `city`, `zip`, `phone`, `email`, `website`
- `vat` (NPWP)
- `company_registry` (NIB / TDP jika dipakai)
- opsional: bank account perusahaan KMS

## Verifikasi setelah sanitasi

- [ ] Settings → Companies: nama **PT. Karusindo Mega Saintifik**
- [ ] Accounting → Chart of Accounts: COA KJ masih ada, saldo akun = 0
- [ ] Accounting → Taxes: pajak KJ masih ada
- [ ] Contacts: customer/vendor masih ada
- [ ] Inventory → Products: produk masih ada
- [ ] Inventory → Configuration → Warehouses / Locations: masih ada
- [ ] Tidak ada invoice/bill/payment/SO/PO/picking terbuka
- [ ] Inventory valuation / on-hand qty = 0 (kecuali Anda sengaja men-seed stock nanti)
- [ ] Buat invoice test: nomor sequence mulai dari prefix KMS (bukan sisa KJ)

## Keamanan

- Jangan jalankan sanitasi pada database KJ produksi.
- Selalu kerja pada **copy** hasil restore dengan nama DB berbeda (`kms` / `kms_prod`).
- Simpan dump KJ asli sebagai arsip sebelum mulai.

## Status environment Cursor

Skrip ini siap dipakai di **server Odoo Anda**. Agent belum bisa mengeksekusi restore
sampai file dump KJ diunggah / path server diberikan.
