Crypto Investment
=================

Custom module **Odoo 16 Community** untuk usaha/investasi jual-beli cryptocurrency.

Fitur
-----

* **Master Crypto Assets** — symbol, harga pasar, quantity held, cost basis, market value, unrealized/realized P&L
* **Beginning Balance** — saldo awal kas + holding crypto, posting ke jurnal accounting
* **Buy / Sell** — transaksi dengan harga, fee, average-cost COGS, histori per crypto, jurnal otomatis
* **Accounting mapping** — cash, crypto asset, opening equity, gain, loss, fee accounts (Settings)
* **Laporan Untung/Rugi** — wizard filter tanggal + PDF
* **Dashboard** — ringkasan portfolio + board treeview
* **Price History** — histori harga harian
* **Proyeksi 14 hari** — regresi linear (naik/turun/sideways) per crypto

Instalasi
---------

1. Salin folder ``addons/crypto_investment`` ke addons path Odoo 16 Anda
   (atau tambahkan ``/path/to/repo/addons`` ke ``addons_path``).
2. Update Apps list, cari **Crypto Investment**, Install.
3. Beri hak akses group **Crypto Investment / User** atau **Manager**.
4. Settings → Crypto Investment: map akun accounting.
5. Opsional: load demo data saat create database untuk sample BTC/ETH trades.

Alur kerja singkat
------------------

1. Pastikan aset crypto ada (BTC, ETH, … sudah di-seed).
2. Buat **Beginning Balance** (kas + holding) → Post.
3. Catat **Buy / Sell** → Confirm (membuat journal entry + price history).
4. Update **Current Market Price** di asset, atau Record Price History.
5. Jalankan **Proyeksi 14 Hari** → Compute Projection.
6. Buka **Profit & Loss by Date** untuk laporan L/R per periode.

Metode akuntansi
----------------

* Inventory cost: **Weighted Average Cost**
* Buy: Debit Crypto Asset (+ fee expense), Credit Cash
* Sell: Debit Cash, Credit Crypto Asset (at avg cost), Credit/Debit Gain/Loss
* Beginning: Debit Crypto Asset / Cash, Credit Opening Equity

Proyeksi harga
--------------

Regresi linear atas price history (lookback default 30 hari) → forecast
``horizon_days`` (default 14). Trend:

* **Naik** jika Δ% > 1%
* **Turun** jika Δ% < -1%
* **Sideways** selainnya

Confidence berdasarkan R² dan jumlah sample (informasi, bukan saran investasi).

Technical
---------

* Compatible: Odoo 16.0 Community
* Depends: ``base``, ``mail``, ``account``, ``board``
* License: LGPL-3
