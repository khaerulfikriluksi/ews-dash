import os, json
from datetime import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, send_from_directory

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC = os.path.join(BASE, "public")

app = Flask(__name__, static_folder=PUBLIC, static_url_path="")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set!")
    return psycopg2.connect(
        DATABASE_URL,
        sslmode='require',
        connect_timeout=10
    )

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id SERIAL PRIMARY KEY,
                crawling_date TEXT NOT NULL,
                summary TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                priority INTEGER NOT NULL,
                tanggal TEXT NOT NULL,
                platform TEXT NOT NULL,
                kategori TEXT NOT NULL,
                topik TEXT NOT NULL,
                sentimen TEXT NOT NULL,
                url TEXT NOT NULL,
                normalized_url TEXT UNIQUE NOT NULL,
                react TEXT
            )
        """)

        cur.execute("SELECT COUNT(*) FROM posts")
        if cur.fetchone()[0] == 0:
            default_summary = [
                "Priority 1 - 2 postingan, Negative terkait Fraud (SMS Phishing poin kartu kredit link palsu mandiri-mi.biz.id & Telepon penipuan catut nama Bank Mandiri)",
                "Priority 2 - 6 postingan, Negative terkait Livin, Livin Merchant, dan Employee / HR (Saldo hilang 1.7 juta, Livin Merchant diblokir & pencairan dana tertahan Rp10,75 juta, Livin error 18 Nov, Dugaan paksaan order Livin Food)",
                "Per platform: Threads 4, Facebook 2, Instagram 2"
            ]
            cur.execute(
                "INSERT INTO metadata (crawling_date, summary) VALUES (%s, %s)",
                ("18-Nov-2026 18:20:00", json.dumps(default_summary))
            )

            initial_posts = [
                (1, "16-Nov-2026 07:04:10", "Threads", "Fraud", "SMS Phishing Mengatasnamakan MANDIRI - 13999 Poin Kartu Kredit Kedaluwarsa Disita Permanen, Link Palsu mandiri-mi.biz.id", "Negative", "https://www.threads.com/@yulianitadevia/post/DfyBoMWE8qL", "6 Comments"),
                (1, "17-Nov-2026 13:17:46", "Instagram", "Fraud", "Telepon Penipuan Mengatasnamakan Bank Mandiri - Caller Ngaku Rizki dari Bank Mandiri, Konfirmasi Transaksi Kartu Kredit Shopee / Tokopedia Rp3 Juta, Korban Balik Ejek 'Ada Pesanan Mamamu Pak', Banyak Komentar Dapat Telepon Sama", "Negative", "https://www.instagram.com/reel/Df1Q5HqP_Td/", "3.9K Likes"),
                (2, "16-Nov-2026 07:20:49", "Facebook", "Livin", "Saldo 4.7 Juta Jadi 3 Juta Hilang 1.7 Juta Tanpa Sepengetahuan, Tidak Bisa Buat Akun Livin, PIN Hanya Diketahui Sendiri, Cabang Sungai Penuh Jauh", "Negative", "https://www.facebook.com/asti.ananta.448921/posts/pfbid02XG1BBhsZraRvd9kyzWa5X2Fn4JREKEmu1j5G7BGKmA5r7NTsKQGUWUpay3uFs61Cl", "30 Comments"),
                (2, "17-Nov-2026 10:21:41", "Threads", "Livin Merchant", "Livin Merchant Diblokir Setelah Pembayaran Kartu Kredit 20 Kodi Gamis - Berkas Lengkap Tapi Dana Belum Masuk Sejak 30 Sep", "Negative", "https://www.threads.com/@bapakmudagabut/post/Df09BrjH_Ca", "1 Likes, 2 Comments"),
                (2, "17-Nov-2026 18:26:01", "Threads", "Livin Merchant", "QRIS Statis Transaksi Terpotong Tapi Dana Tidak Masuk ke Merchant, Tidak Muncul di Livin Merchant, Call Center Tidak Bisa Dihubungi", "Negative", "https://www.threads.com/@neokwards/post/Df10dHPAQ0u", "4 Comments"),
                (2, "17-Nov-2026 23:46:47", "Threads", "Livin Merchant", "Livin Merchant Pencairan Terkendala - 2 Merchant Dana Tertahan Total Rp10.751.000, Transaksi 11-12 Nov, Dilaporkan 12 Nov, Telepon Helpdesk 14021 Berulang, CS Ubah Estimasi 3-5 Hari Jadi 90 Hari, Banyak Merchant Lain Validasi di Komentar, Pertimbangkan Pindah ke GoPay / Dana Merchant", "Negative", "https://www.threads.com/@firmansyahanggoro_/post/Df2ZKckkzkd", "23 Likes"),
                (2, "18-Nov-2026 06:52:14", "Facebook", "Livin", "Livin Tidak Bisa Dibuka / Error 18 Nov - 3 Laporan Terpisah Pagi-Sore, Brimo Juga Kena, Pengguna Tanya Apakah Ada Yang Sama", "Negative", "https://www.facebook.com/permalink.php?story_fbid=pfbid02qWaU9QA8PCTHf7PnDBxa1hxf9QZziJKhHGbZ27xAqmuQ6auwgJyPo41gheTThWUTl&id=61557929993332", "18 Comments"),
                (2, "18-Nov-2026 18:20:00", "Instagram", "Employee / HR", "Mandiri Diduga Paksa Karyawan Order Livin Food Harian Pakai Dana Pribadi Untuk KPI - Reimbursement Tidak Konsisten Capped Rp50k, Monitoring Duta Transaksi, Order Weekend Wajib", "Negative", "https://www.instagram.com/p/Df4Ym_NFCGs/", "6900 Likes")
            ]

            for p in initial_posts:
                raw_url = p[6]
                norm_url = raw_url.strip().lower()
                cur.execute("""
                    INSERT INTO posts (priority, tanggal, platform, kategori, topik, sentimen, url, normalized_url, react)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (normalized_url) DO NOTHING
                """, (p[0], p[1], p[2], p[3], p[4], p[5], raw_url, norm_url, p[7]))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Database init warning:", e)

try:
    init_db()
except Exception as e:
    print("Database init warning:", e)

def normalize_url(u: str) -> str:
    if not u:
        return ""
    return u.strip().lower()

def split_pipe(line):
    out = []
    cur = ""
    inQ = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if inQ and i + 1 < len(line) and line[i + 1] == '"':
                cur += '"'
                i += 1
            else:
                inQ = not inQ
        elif ch == "|" and not inQ:
            out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    out.append(cur)
    return [s.strip().strip('"') for s in out]

def parse_csv_text(text):
    lines = [l for l in text.splitlines() if l.strip() != ""]
    if len(lines) < 2:
        return []
    header = split_pipe(lines[0])
    def idx(n):
        target = n.lower().strip()
        for j, h in enumerate(header):
            if h.lower().strip() == target:
                return j
        for j, h in enumerate(header):
            if target in h.lower().strip():
                return j
        return -1

    iP, iT, iPl, iK, iTo, iS, iU, iR = (
        idx("priority"), idx("tanggal"), idx("platform"),
        idx("kategori"), idx("topik"), idx("sentimen"),
        idx("url"), idx("react")
    )
    rows = []
    for line in lines[1:]:
        c = split_pipe(line)
        def get(i):
            return c[i].strip() if 0 <= i < len(c) else ""
        try:
            pr = int(get(iP))
        except Exception:
            pr = 4
        rows.append({
            "priority": pr,
            "tanggal": get(iT),
            "platform": get(iPl),
            "kategori": get(iK),
            "topik": get(iTo),
            "sentimen": get(iS),
            "url": get(iU),
            "react": get(iR)
        })
    return rows

def sort_rows(rows):
    MONTHS = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    def parse_dt(s):
        try:
            parts = s.split(" ")
            d = parts[0].split("-")
            t = parts[1].split(":") if len(parts) > 1 else ["0","0","0"]
            return datetime(int(d[2]), MONTHS.get(d[1], 1), int(d[0]), int(t[0]), int(t[1]), int(t[2]))
        except Exception:
            return datetime.min
    return sorted(rows, key=lambda r: (r["priority"], r["kategori"], -parse_dt(r["tanggal"]).timestamp()))

@app.route("/")
def index():
    return send_from_directory(PUBLIC, "index.html")

@app.route("/dashboard-data", methods=["GET"])
def get_dashboard_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT crawling_date, summary FROM metadata ORDER BY id DESC LIMIT 1")
        meta = cur.fetchone()
        crawling_date = meta["crawling_date"] if meta else "18-Nov-2026 18:20:00"
        summary = json.loads(meta["summary"]) if meta and meta["summary"] else []

        cur.execute("SELECT priority, tanggal, platform, kategori, topik, sentimen, url, react FROM posts")
        rows = [dict(r) for r in cur.fetchall()]

        cur.close()
        conn.close()

        rows = sort_rows(rows)
        return jsonify({
            "success": True,
            "crawling_date": crawling_date,
            "summary": summary,
            "total": len(rows),
            "rows": rows
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "File CSV tidak ditemukan"}), 400
    f = request.files["file"]
    crawling_date = request.form.get("crawling_date", "").strip()
    if not crawling_date:
        return jsonify({"success": False, "error": "crawling_date wajib diisi"}), 400

    try:
        raw_summary = request.form.get("summary", "[]")
        summary = json.loads(raw_summary)
    except Exception:
        return jsonify({"success": False, "error": "summary harus berupa JSON Array berisi string"}), 400

    try:
        text = f.read().decode("utf-8-sig")
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal membaca file CSV: {e}"}), 400

    parsed_rows = parse_csv_text(text)
    if not parsed_rows:
        return jsonify({"success": False, "error": "File CSV kosong atau format header tidak sesuai"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT normalized_url FROM posts")
        existing_urls = {r["normalized_url"] for r in cur.fetchall()}

        inserted_count = 0
        skipped_count = 0

        for r in parsed_rows:
            raw_url = (r.get("url") or "").strip()
            norm_url = normalize_url(raw_url)

            if not norm_url or norm_url in existing_urls:
                skipped_count += 1
                continue

            existing_urls.add(norm_url)
            try:
                cur.execute("""
                    INSERT INTO posts (priority, tanggal, platform, kategori, topik, sentimen, url, normalized_url, react)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (normalized_url) DO NOTHING
                """, (
                    r["priority"], r["tanggal"], r["platform"],
                    r["kategori"], r["topik"], r["sentimen"],
                    raw_url, norm_url, r["react"]
                ))
                inserted_count += 1
            except Exception:
                skipped_count += 1

        cur.execute("SELECT crawling_date, summary FROM metadata ORDER BY id DESC LIMIT 1")
        last_meta = cur.fetchone()
        summary_json = json.dumps(summary)
        if not last_meta or last_meta["crawling_date"] != crawling_date or last_meta["summary"] != summary_json:
            cur.execute("INSERT INTO metadata (crawling_date, summary) VALUES (%s, %s)", (crawling_date, summary_json))
        conn.commit()

        cur.execute("SELECT priority, tanggal, platform, kategori, topik, sentimen, url, react FROM posts")
        all_rows = sort_rows([dict(row) for row in cur.fetchall()])

        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "crawling_date": crawling_date,
            "summary": summary,
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "total": len(all_rows),
            "rows": all_rows
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=False)
