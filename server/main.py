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
                data_date TEXT NOT NULL,
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

        cur.execute("SELECT COUNT(*) FROM metadata")
        if cur.fetchone()[0] == 0:
            sample_metadata = [
                ("11-Nov-2026", json.dumps([
                    "[Priority 2] [Facebook] Livin Tidak Bisa Login / Layanan Tidak Tersedia - Gagal Verifikasi Tanggal Lahir, Error Status ID 80000. Indikasi gangguan login Livin. Tanggal: 11-Nov-2026 04:06:27, Sentimen: Negative.",
                    "[Priority 2] [Threads] Livin Ke Blokir, Daftar Ulang Gangguan, Upload KTP Gagal, CS Lama Direspon. Tanggal: 10-Nov-2026 08:53:46, Sentimen: Negative."
                ])),
                ("12-Nov-2026", json.dumps([
                    "[Priority 2] [Threads] Livin Terblokir Karena Salah Password 3x, Tidak Punya Nomor Kartu Debit. Tanggal: 11-Nov-2026 16:09:17, Sentimen: Negative."
                ])),
                ("13-Nov-2026", json.dumps([
                    "[Priority 2] [Facebook] Livin Registrasi Gagal Loop Sudah Terdaftar Butuh Kartu Debit/Kredit. Tanggal: 12-Nov-2026 18:03:42, Sentimen: Negative."
                ])),
                ("14-Nov-2026", json.dumps([
                    "[Priority 1] [Instagram] Modus Mengatasnamakan Call Center Bank Mandiri - Uang Hilang dari Livin Setelah Ikuti Arahan Nonaktifkan Rekening. Tanggal: 13-Nov-2026 17:37:05, Sentimen: Negative."
                ])),
                ("15-Nov-2026", json.dumps([
                    "[Priority 1] [Instagram] Modus Mengatasnamakan Call Center Bank Mandiri - Uang Hilang dari Livin. Tanggal: 13-Nov-2026 17:37:05, Sentimen: Negative.",
                    "[Priority 2] [Facebook] Livin Proses Belum Dapat Dilanjutkan RPT-O2. Tanggal: 14-Nov-2026 13:58:47, Sentimen: Negative."
                ]))
            ]
            for m_date, m_sum in sample_metadata:
                cur.execute("INSERT INTO metadata (data_date, summary) VALUES (%s, %s)", (m_date, m_sum))

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

        cur.execute("SELECT data_date, summary FROM metadata ORDER BY id ASC")
        meta_rows = cur.fetchall()
        
        metadata_list = []
        for m in meta_rows:
            try:
                s_parsed = json.loads(m["summary"]) if m["summary"] else []
            except Exception:
                s_parsed = []
            metadata_list.append({
                "data_date": m["data_date"],
                "summary": s_parsed
            })

        cur.execute("SELECT priority, tanggal, platform, kategori, topik, sentimen, url, react FROM posts")
        rows = [dict(r) for r in cur.fetchall()]

        cur.close()
        conn.close()

        rows = sort_rows(rows)
        return jsonify({
            "success": True,
            "metadata_list": metadata_list,
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
    
    data_date = request.form.get("data_date", "").strip() or request.form.get("date_data", "").strip() or request.form.get("crawling_date", "").strip()
    if not data_date:
        return jsonify({"success": False, "error": "data_date wajib diisi"}), 400

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

        summary_json = json.dumps(summary)
        cur.execute("INSERT INTO metadata (data_date, summary) VALUES (%s, %s)", (data_date, summary_json))
        conn.commit()

        cur.execute("SELECT data_date, summary FROM metadata ORDER BY id ASC")
        meta_rows = cur.fetchall()
        metadata_list = [{"data_date": m["data_date"], "summary": json.loads(m["summary"]) if m["summary"] else []} for m in meta_rows]

        cur.execute("SELECT priority, tanggal, platform, kategori, topik, sentimen, url, react FROM posts")
        all_rows = sort_rows([dict(row) for row in cur.fetchall()])

        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "metadata_list": metadata_list,
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "total": len(all_rows),
            "rows": all_rows
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=False)
