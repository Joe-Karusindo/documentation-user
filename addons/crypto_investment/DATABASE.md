# Database Schema — Crypto Investment (Odoo 16)

Tables dibuat otomatis oleh ORM Odoo saat modul di-install (`-i crypto_investment`).

## Models / Tables

| Model                         | Table                           | Fungsi                                      |
|-------------------------------|---------------------------------|---------------------------------------------|
| `crypto.asset`                | `crypto_asset`                  | Master aset crypto + valuasi holdings       |
| `crypto.beginning.balance`    | `crypto_beginning_balance`      | Dokumen saldo awal kas & holding            |
| `crypto.beginning.balance.line` | `crypto_beginning_balance_line` | Baris holding awal per crypto             |
| `crypto.transaction`          | `crypto_transaction`            | Histori beli / jual / beginning             |
| `crypto.price.history`        | `crypto_price_history`          | Histori harga harian                        |
| `crypto.price.projection`     | `crypto_price_projection`       | Batch proyeksi 14 hari                      |
| `crypto.price.projection.line`| `crypto_price_projection_line`  | Hasil proyeksi per crypto                   |
| `crypto.dashboard`            | *(transient)*                   | Ringkasan dashboard                         |
| `crypto.pnl.wizard`           | *(transient)*                   | Wizard laporan L/R                          |
| `crypto.pnl.line`             | *(transient)*                   | Baris hasil laporan L/R                     |

## Company accounting fields (`res_company`)

- `crypto_cash_account_id`
- `crypto_asset_account_id`
- `crypto_opening_equity_account_id`
- `crypto_gain_account_id`
- `crypto_loss_account_id`
- `crypto_fee_account_id`

## Key relations

```
crypto_asset 1───* crypto_transaction
crypto_asset 1───* crypto_price_history
crypto_beginning_balance 1───* crypto_beginning_balance_line *───1 crypto_asset
crypto_price_projection 1───* crypto_price_projection_line *───1 crypto_asset
crypto_transaction *───? account_move   (journal entry)
```

## Install database

```bash
# Tambahkan addons path, lalu:
odoo-bin -d crypto_db -i crypto_investment --without-demo=False
```

Atau buat DB baru dari UI dengan **Load demonstration data** dicentang.
