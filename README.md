# Inventaris Laboratorium Komputer

Aplikasi Flask untuk mencatat barang inventaris laboratorium. Data tersimpan di SQLite lokal atau PostgreSQL saat `DATABASE_URL` tersedia.

## Menjalankan aplikasi lokal

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m flask --app app run --debug --port 5001
```

Buka `http://127.0.0.1:5001` di browser.

## Deploy dengan Vercel dan Neon

1. Buat project PostgreSQL gratis di Neon, lalu salin connection string.
2. Impor repository GitHub ke Vercel.
3. Tambahkan environment variable `DATABASE_URL` dengan connection string Neon.
4. Tambahkan `SECRET_KEY` dengan nilai acak panjang.
5. Deploy. Vercel mengenali Flask dari `app.py`.
