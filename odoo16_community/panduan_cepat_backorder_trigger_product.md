# Setting Backorder + Trigger per Product

**Odoo 16 Community — cara paling mudah dan paling cepat**

Dua field saja yang perlu diisi di **setiap product**:

| Field di Odoo | Artinya | Isi yang dipakai |
| --- | --- | --- |
| **Min Quantity** | Quantity backorder / ambang stok | Angka ambang, misalnya `20` |
| **Trigger** | Kapan Odoo bertindak | `Manual` = hanya informasi; `Auto` = otomatis buat RFQ |

Tidak ada field bernama "Backorder" di form product. Kedua field itu ada di **Reordering Rules**.

---

## A. Sekali saja: tampilkan kolom Trigger (wajib)

Tanpa langkah ini, field Trigger sering **tersembunyi**.

1. Login sebagai user yang bisa mengatur Inventory (misalnya Administrator / Warehouse Manager).
2. Klik aplikasi **Inventory**.
3. Menu atas: **Configuration → Reordering Rules**.
   - Jika menu tidak ada: **Settings** (gear) → aktifkan **Developer Mode**, lalu ulangi langkah 3.
   - Nama menu Indonesia: **Inventaris → Konfigurasi → Aturan Pemesanan Ulang**.
4. Anda melihat daftar aturan (boleh masih kosong).
5. Di **paling kanan header kolom**, klik ikon **slider / tiga garis / adjust settings** (bukan menu Action).
6. Di daftar kolom, **centang Trigger**.
7. Tutup panel kolom. Kolom **Trigger** sekarang tampil (nilai `Auto` atau `Manual`).

Lakukan ini **satu kali per database / per user**. Setelah itu kolom tetap kelihatan.

---

## B. Setting 1 product (klik per klik)

Ulangi blok ini untuk setiap product.

### B1. Buka product

1. **Inventory → Products → Products**.
2. Ketik nama / internal reference di kotak search, Enter.
3. Klik nama product sampai form terbuka.

### B2. Pastikan product bisa di-backorder

Di form product, cek 4 hal ini. Jika sudah benar, lanjut ke B3.

1. Di bawah nama product, **Can be Purchased** harus **tercentang**.
2. Tab **General Information**:
   - **Product Type** = `Storable Product`.
   - Jika masih `Consumable` atau `Service`: ubah ke `Storable Product`, klik **Save**.
3. Tab **Inventory**:
   - Centang rute **Buy** (product dibeli) **atau** **Manufacture** (product diproduksi).
   - **Jangan** centang **Replenish on Order (MTO)** jika Anda ingin ambang Min Quantity dipakai sebagai buffer.
4. Tab **Purchase** (jika rute Buy):
   - Minimal 1 baris **Vendor** (nama vendor + harga).
   - Jika kosong: **Add a line** → pilih Vendor → isi Price → **Save**.

Tanpa Vendor (Buy) atau BoM (Manufacture), Trigger **Auto** tidak bisa membuat RFQ/MO. Trigger **Manual** tetap bisa menampilkan informasi.

### B3. Buat / buka Reordering Rule

1. Di **bagian atas** form product, klik smart button **Reordering Rules**.
   - Angka di tombol = jumlah rule yang sudah ada (`0` = belum ada).
2. Jika daftar kosong, klik **Create**.
3. Jika sudah ada 1 baris, **klik baris itu** sampai form rule terbuka (atau edit langsung di list jika tampilan list bisa diketik).

### B4. Isi backorder dan trigger

Isi persis seperti ini, lalu **Save**:

| Urutan | Field | Apa yang diketik / dipilih | Contoh |
| --- | --- | --- | --- |
| 1 | **Product** | Biarkan. Sudah terisi nama product. | Filter Oli |
| 2 | **Location** | Pilih lokasi stok utama. Jangan kosong. | `WH/Stock` |
| 3 | **Min Quantity** | Quantity backorder. Informasi muncul jika Forecasted **lebih kecil** dari angka ini. | `20` |
| 4 | **Max Quantity** | Target stok setelah diisi. Harus **≥ Min**. | `40` |
| 5 | **Multiple Quantity** | Isi `0` jika tidak perlu kelipatan pack. | `0` |
| 6 | **Trigger** | `Manual` = info saja. `Auto` = Odoo buat draft pembelian sendiri. | `Manual` |

Jika **Trigger tidak ada di form**:

1. Kembali ke **Inventory → Configuration → Reordering Rules**.
2. Ulangi bagian **A** (tampilkan kolom Trigger).
3. Cari product di search bar.
4. Di kolom **Trigger** pada baris itu, klik dan pilih `Manual` atau `Auto`.
5. Klik di luar sel, atau tekan Enter. Odoo menyimpan otomatis.

### B5. Cek 10 detik

1. Kembali ke form product (breadcrumb atau tombol back).
2. Smart button **Reordering Rules** sekarang bernilai **1** (atau lebih).
3. Buka lagi rule: Min dan Trigger sesuai yang Anda isi.

Product ini selesai. Lanjut product berikutnya dari **B1**.

---

## C. Cara lebih cepat: banyak product dari satu layar

Pakai ini jika product sudah Storable + ada Vendor. Anda tidak perlu buka form satu-satu.

1. **Inventory → Configuration → Reordering Rules**.
2. Pastikan kolom **Trigger**, **Min Quantity**, **Max Quantity** tampil (bagian A).
3. Klik **Create**.
4. Di baris baru:
   1. **Product**: ketik nama, pilih dari dropdown.
   2. **Location**: `WH/Stock`.
   3. **Min Quantity**: angka backorder.
   4. **Max Quantity**: target stok.
   5. **Trigger**: `Manual` atau `Auto`.
5. Klik **Create** lagi untuk baris berikutnya. Jangan tutup layar.
6. Setelah semua baris terisi, klik **Save** (jika tombol ada) atau klik di luar sel.

Satu product = satu baris. Jangan buat dua rule untuk product + lokasi yang sama.

---

## D. Cara paling cepat untuk puluhan / ratusan product (Import)

Pakai ini jika Anda sudah punya daftar product + angka ambang di Excel.

### D1. Ambil template

1. **Inventory → Configuration → Reordering Rules**.
2. Jika daftar masih kosong, buat **1 rule contoh** dulu (bagian B atau C) supaya kolom export lengkap.
3. Centang 1 baris contoh → **Action → Export**.
4. Pilih field berikut (klik Add):

   - `Product / External ID` **atau** `Product`
   - `Location / External ID` **atau** `Location`
   - `Min Quantity`
   - `Max Quantity`
   - `Trigger`
   - `To Update` (opsional, biarkan kosong)

5. Format **CSV** atau **Excel** → **Export**.

### D2. Isi file

Satu baris per product. Contoh CSV:

```text
product_id,location_id,product_min_qty,product_max_qty,trigger
[Produk] Filter Oli,WH/Stock,20,40,manual
[Produk] Filter Udara,WH/Stock,10,25,manual
[Produk] Ban Dalam 14,WH/Stock,15,30,auto
```

Aturan isi:

- **product_min_qty** = quantity backorder.
- **product_max_qty** ≥ product_min_qty.
- **trigger** hanya `manual` atau `auto` (huruf kecil).
- Nama Product dan Location harus **persis** sama dengan di Odoo. Lebih aman pakai External ID hasil export.

### D3. Import

1. **Inventory → Configuration → Reordering Rules**.
2. **Favorites → Import records** (ikon atas, atau menu Favorites).
3. Upload file.
4. Pastikan mapping kolom:
   - Product → Product
   - Location → Location
   - Min Quantity → Min Quantity
   - Max Quantity → Max Quantity
   - Trigger → Trigger
5. **Test** dulu. Jika 0 error, klik **Import**.

---

## E. Pilih Trigger yang mana

| Trigger | Klik / pilih ini jika | Yang terjadi |
| --- | --- | --- |
| **Manual** | Anda hanya ingin **tahu** product mana stoknya di bawah backorder | Product muncul di **Inventory → Operations → Replenishment**. Tidak ada RFQ otomatis. |
| **Auto** | Stok harus selalu terisi tanpa dicek setiap hari | Scheduler (default 1× sehari) membuat draft RFQ (rute Buy) atau MO (rute Manufacture). |

Ubah Trigger kapan saja di **Configuration → Reordering Rules**, kolom Trigger.

Jalan pintas di **Inventory → Operations → Replenishment**:

- Ikon **panah putar (Automate Orders)** di kanan baris = ubah ke **Auto**.
- Setelah Auto, tombol itu tidak perlu diklik lagi.

---

## F. Lihat hasil (product yang stoknya di bawah backorder)

1. **Inventory → Operations → Replenishment**.
2. Filter default **To Reorder** menampilkan product dengan **Forecasted < Min Quantity**.
3. Baca baris:

   - **On Hand** = stok fisik.
   - **Forecasted** = On Hand + Incoming − Outgoing.
   - **Min** = quantity backorder yang Anda set.
   - **Trigger** = Manual atau Auto.
   - **To Order** = usulan pesan (Max − Forecasted).

4. Jika Trigger Manual dan Anda ingin pesan sekarang: isi **To Order** jika perlu, klik **Order Once**.

---

## G. Contoh 1 product, dari nol sampai selesai

Product **Filter Oli**, stok sekarang 8, Anda ingin info jika stok forecasted di bawah 20, tanpa otomatis beli.

1. **Inventory → Products → Products** → buka **Filter Oli**.
2. Can be Purchased = ya. Product Type = Storable Product. Rute Buy = ya. Vendor = ada. **Save**.
3. Klik **Reordering Rules** → **Create**.
4. Location = `WH/Stock`.
5. Min Quantity = `20`.
6. Max Quantity = `40`.
7. Multiple Quantity = `0`.
8. Trigger = `Manual`.
9. **Save**.
10. **Inventory → Operations → Replenishment** → Filter Oli tampil (karena 8 < 20).

Selesai untuk product itu. Product berikutnya: ulangi langkah 1–9 dengan nama dan angka yang berbeda.

---

## H. Kalau tersendat

| Yang terjadi | Lakukan ini |
| --- | --- |
| Tidak ada tombol **Reordering Rules** | Product Type belum Storable. Ubah, Save, refresh. |
| Tidak ada kolom **Trigger** | Ulangi bagian A. |
| Tidak ada menu **Reordering Rules** | Aktifkan Developer Mode. Pastikan app Inventory terpasang. Login sebagai admin. |
| Product tidak muncul di Replenishment | Forecasted masih ≥ Min, atau rule belum disimpan, atau Location salah. Cek rule di Configuration → Reordering Rules. |
| Trigger Auto tetapi RFQ tidak muncul | Isi Vendor + centang rute Buy. Lalu **Inventory → Operations → Run Scheduler** (perlu Developer Mode). |
| Dua rule untuk 1 product | Buka keduanya. Archive yang Location-nya salah. Sisakan 1 rule per product per lokasi. |

---

## I. Urutan kerja yang disarankan

Untuk **beberapa product** (di bawah ±20):

1. Bagian A sekali.
2. Bagian **C** (satu layar list).
3. Bagian F untuk memastikan yang stoknya rendah tampil.

Untuk **banyak product**:

1. Bagian A sekali.
2. Bagian **D** (import).
3. Bagian F.

Jangan set Create Backorder di Operation Types untuk pekerjaan ini. Itu setting pengiriman parsial, bukan ambang per product.
