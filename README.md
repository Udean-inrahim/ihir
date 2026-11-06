# Inventaris Laboratorium Komputer

Aplikasi Flask untuk mencatat barang inventaris laboratorium. Data tersimpan di `instance/inventaris.db`.

## Menjalankan aplikasi

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app run --debug --port 5001
```

Buka `http://127.0.0.1:5001` di browser.

Fitur: ringkasan jumlah, pencarian, filter kategori dan kondisi, pengurutan, tambah, edit, hapus dengan konfirmasi, serta validasi server.

Sebelum aplikasi dipublikasikan, atur `SECRET_KEY` dari environment dan matikan mode debug.
