# Dashboard EWS (Flask + Supabase PostgreSQL di Vercel)

Dashboard Early Warning System dengan backend Python Flask, database cloud **Supabase (PostgreSQL)**, dan konfigurasi `pyproject.toml` agar sukses di-deploy ke Vercel.

## Struktur Folder
```
.
├── server/
│   ├── main.py                ← Backend Flask (koneksi psycopg2 & Supabase)
│   └── requirements.txt       ← Flask & psycopg2-binary
├── public/
│   └── index.html             ← Frontend Dashboard + Form Upload
├── pyproject.toml             ← Konfigurasi entrypoint Flask untuk Vercel
└── README.md
```

## Cara Deploy ke Vercel
1. Hubungkan repository GitHub Anda ke Vercel.
2. Di pengaturan proyek Vercel, masuk ke bagian **Environment Variables** lalu tambahkan:
   - **Key:** `DATABASE_URL`
   - **Value:** `postgresql://postgres:KeyRule13%40%40%40@db.dozuebcfmhspmuaotwqh.supabase.co:5432/postgres`
3. Klik **Deploy**.
