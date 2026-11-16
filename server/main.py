import os, json
from datetime import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, send_from_directory

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC = os.path.join(BASE, "public")

app = Flask(__name__, static_folder=PUBLIC, static_url_path="")

# Ambil Connection URL dari Environment Variable Vercel (DATABASE_URL)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Buat tabel metadata (menyimpan crawling_date & summary terakhir)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id SERIAL PRIMARY KEY,
                crawling_date TEXT NOT NULL,
                summary TEXT NOT NULL
            )
        """)
        
        # Buat tabel posts (menyimpan data postingan EWS dengan unique constraint pada normalized_url)
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
        
        # Seed data awal jika tabel posts masih kosong
        cur.execute("SELECT COUNT(*) FROM posts")
        if cur.fetchone()[0] == 0:
            default_summary = [
                "Priority 1 - 6 postingan, Negative terkait Fraud, Security, dan Reputational Risk (Catut nama MTF/Mandiri Taspen, Dugaan ATO Livin, Rumor serangan siber ATM Nangapinoh, Joki BSU, Demo AMPB)",
                "Priority 2 - 4 postingan, Negative terkait Gangguan Sistem (Klaster gangguan Livin massal 08-11 Nov, KOPRA gangguan 2 hari, ATM error, Kartu debit terblokir)",
                "Priority 3 - 1 postingan, Negative terkait Layanan Cabang (Antrean padat KCP Bogor Gunung Putri)",
                "Priority 4 - 3 postingan, Positive terkait Program & Promo (Livin MARKT Senayan City, Promo Wingstop, Promo Super Indo)",
                "Per platform: Facebook 5, Threads 5, Instagram 4"
            ]
            cur.execute(
                "INSERT INTO metadata (crawling_date, summary) VALUES (%s, %s)",
                ("11-Nov-2026 13:21:52", json.dumps(default_summary))
            )
            
            initial_posts = [
                (1, "09-Nov-2026 16:34:42", "Instagram", "Fraud", "Waspada Penipuan Mengatasnamakan Mandiri Tunas Finance - peringatan resmi MTF soal penipuan catut nama Mandiri", "Negative", "https://www.instagram.com/p/DfhBWwiEgY9/", "42 Likes"),
                (1, "08-Nov-2026 15:38:39", "Instagram", "Fraud", "Edukasi anti-fraud Bank Mandiri Taspen - Pesan minta OTP tapi ngaku Mandiri = penipuan, Terasa Janggal Stop Dulu", "Negative", "https://www.instagram.com/p/DfeWJaYH73N/", "2 Likes"),
                (1, "09-Nov-2026 20:16:46", "Facebook", "Security", "Klaim ada orang lain login ke Livin milik nasabah - dugaan Account Take Over, perlu verifikasi (kasus tunggal, bukan massal)", "Negative", "https://www.facebook.com/tengku.nilawana/posts/pfbid09XH9CyiRnuFg1ucq8pxQSfqAgrCUn1zJnGzamEEh15bR9JBRrbdW9PHf76uBBqWwl", "Unaccessible"),
                (1, "08-Nov-2026 23:17:15", "Threads", "Security", "Rumor serangan siber bank Indonesia dikaitkan dengan gagal tarik tunai tanpa kartu di ATM Mandiri Nangapinoh - struk TRANSACTION DECLINED / UNABLE TO DISPENSE", "Negative", "https://www.threads.com/@hengkyrandebua/post/DffKoQvE1M_", "Unaccessible"),
                (1, "10-Nov-2026 17:47:11", "Threads", "Fraud", "Klaster joki / farming pembukaan rekening Mandiri untuk BSU - tawar buka rekening jarak jauh, iming-iming Rp45.000-Rp150.000, souvenir, panduan via DM - risiko penyalahgunaan identitas / rekening mule", "Negative", "https://www.threads.com/@momomochidobbie/post/DfjucioGFr1", "33 Likes"),
                (1, "08-Nov-2026 09:34:12", "Facebook", "Reputational Risk", "Gema kasus blokir Rp80,9 juta milik Koordinator AMPB Botok (kasus Agustus, sudah dibuka 26-Agu-2026) - video gunting kartu Mandiri + narasi netizen ramai pindahkan dana dari Livin + agenda demo AMPB di Bank Mandiri 09-Nov", "Negative", "https://www.facebook.com/reel/1478584697522145/", "63.9K Views"),
                (2, "11-Nov-2026 04:06:27", "Facebook", "Livin", "Klaster gangguan Livin massal 08-11 Nov - forced password reset, Belum berhasil terhubung Status ID 80000, Layanan tidak tersedia untuk sementara, loading stuck, transfer tidak masuk, QRIS saldo terpotong - 7+ akun berbeda di Threads/Facebook", "Negative", "https://www.facebook.com/LennyMarlinaHS/posts/pfbid02c9kUHVXQoy3hK7LM1WgJ2WqLyFQ9gqiNaQP1XjmYSpRyJcekk4bTNfuF1saGxhil", "Unaccessible"),
                (2, "09-Nov-2026 18:03:48", "Threads", "KOPRA", "KOPRA Mandiri gangguan 2 hari - login web tidak bisa, transfer di KOPRA Mobile loading terus", "Negative", "https://www.threads.com/@navagia/post/DfhLjbPE4W4", "7 Likes"),
                (2, "09-Nov-2026 13:59:36", "Facebook", "ATM", "ATM Mandiri error - kartu sudah masuk, PIN dan nominal sudah dipilih, transaksi gagal / ATM error", "Negative", "https://www.facebook.com/reel/1610280993636968/", "78.4K Views"),
                (2, "09-Nov-2026 14:23:23", "Facebook", "Debit Card", "Kartu Debit Mandiri terblokir - overlay Ups kartu terblokir di cabang, klaster dengan video kartu debit diblokir 11-Nov", "Negative", "https://www.facebook.com/reel/1130189796476325/", "42.8K Views"),
                (3, "10-Nov-2026 08:53:46", "Threads", "Customer Service", "Antrean padat di KCP Bank Mandiri Bogor Gunung Putri sebelum pukul 09.00 - lobby penuh", "Negative", "https://www.facebook.com/ach.014/post/DfixZuhiS3c", "1.5K Views"),
                (4, "08-Nov-2026 13:13:36", "Threads", "Digital Banking", "Visa Presents Livin MARKT 5-8 Nov di Senayan City - kurasi brand lokal, kuliner, travel, promo kartu Mandiri", "Positive", "https://www.threads.com/@bliblidotcom/post/DfeFjDkkQM-", "3.9K Likes"),
                (4, "08-Nov-2026 17:19:15", "Instagram", "Livin", "Promo Wingstop x Bank Mandiri 1-24 Nov 2026", "Positive", "https://www.instagram.com/p/DfehoF8hOaH/", "3.3K Likes"),
                (4, "09-Nov-2026 13:59:40", "Instagram", "Digital Banking", "Promo pembayaran Super Indo - Makin Hemat dengan promo pembayaran termasuk Bank Mandiri", "Positive", "https://www.instagram.com/p/DfgvnPmk4mx/", "2.8K Likes")
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
        for j, h in enumerate(header):
            if n.lower() in h.lower():
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
        crawling_date = meta["crawling_date"] if meta else "11-Nov-2026 13:21:52"
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

        cur.execute("INSERT INTO metadata (crawling_date, summary) VALUES (%s, %s)", (crawling_date, json.dumps(summary)))
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
