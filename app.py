from datetime import date
import os
from pathlib import Path
import sqlite3
import re

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "instance" / "inventaris.db"
CATEGORIES = [
    "Perangkat Komputer",
    "Perangkat Input",
    "Perangkat Output",
    "Jaringan",
    "Aksesori",
    "Lainnya",
]
CONDITIONS = ["Baik", "Rusak", "Dalam Perbaikan"]

app = Flask(__name__, static_folder="public/static", static_url_path="/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-before-deployment")


def connect_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        return connection

    import psycopg
    from psycopg.rows import dict_row

    class PostgresConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, query, params=()):
            query = re.sub(r"\s+COLLATE NOCASE", "", query, flags=re.IGNORECASE)
            return self.connection.execute(query.replace("?", "%s"), params)

        def commit(self):
            self.connection.commit()

        def close(self):
            self.connection.close()

    return PostgresConnection(psycopg.connect(database_url, row_factory=dict_row))


def get_db():
    if "db" not in g:
        g.db = connect_db()
        database_url = os.environ.get("DATABASE_URL")
        id_column = "SERIAL PRIMARY KEY" if database_url else "INTEGER PRIMARY KEY AUTOINCREMENT"
        code_column = "TEXT NOT NULL UNIQUE" if database_url else "TEXT NOT NULL COLLATE NOCASE UNIQUE"
        g.db.execute(
            f"""CREATE TABLE IF NOT EXISTS barang (
                id {id_column},
                kode_barang {code_column},
                nama_barang TEXT NOT NULL,
                kategori TEXT NOT NULL,
                jumlah INTEGER NOT NULL CHECK (jumlah > 0),
                kondisi TEXT NOT NULL,
                lokasi TEXT NOT NULL,
                tanggal_masuk TEXT,
                keterangan TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        if database_url:
            g.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS barang_kode_lower ON barang (LOWER(kode_barang))")
        g.db.commit()
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def dashboard_data():
    db = get_db()
    summary = db.execute(
        """SELECT COUNT(*) AS jenis, COALESCE(SUM(jumlah), 0) AS unit,
                  COALESCE(SUM(CASE WHEN kondisi = 'Baik' THEN jumlah ELSE 0 END), 0) AS baik,
                  COALESCE(SUM(CASE WHEN kondisi = 'Rusak' THEN jumlah ELSE 0 END), 0) AS rusak,
                  COALESCE(SUM(CASE WHEN kondisi = 'Dalam Perbaikan' THEN jumlah ELSE 0 END), 0) AS perbaikan
           FROM barang"""
    ).fetchone()
    return summary


def validate_form(item_id=None):
    values = {
        "kode_barang": request.form.get("kode_barang", "").strip(),
        "nama_barang": request.form.get("nama_barang", "").strip(),
        "kategori": request.form.get("kategori", "").strip(),
        "jumlah": request.form.get("jumlah", "").strip(),
        "kondisi": request.form.get("kondisi", "").strip(),
        "lokasi": request.form.get("lokasi", "").strip(),
        "tanggal_masuk": request.form.get("tanggal_masuk", "").strip(),
        "keterangan": request.form.get("keterangan", "").strip(),
    }
    errors = {}
    for key, label in (("kode_barang", "Kode barang"), ("nama_barang", "Nama barang"), ("kategori", "Kategori"), ("jumlah", "Jumlah"), ("kondisi", "Kondisi"), ("lokasi", "Lokasi")):
        if not values[key]:
            errors[key] = f"{label} wajib diisi."
    try:
        quantity = int(values["jumlah"])
        if quantity < 1:
            errors["jumlah"] = "Jumlah harus bilangan bulat lebih dari 0."
    except ValueError:
        quantity = 0
        if values["jumlah"]:
            errors["jumlah"] = "Jumlah harus berupa bilangan bulat."
    if values["kategori"] and values["kategori"] not in CATEGORIES:
        errors["kategori"] = "Pilih kategori yang tersedia."
    if values["kondisi"] and values["kondisi"] not in CONDITIONS:
        errors["kondisi"] = "Pilih kondisi yang tersedia."
    if values["tanggal_masuk"]:
        try:
            date.fromisoformat(values["tanggal_masuk"])
        except ValueError:
            errors["tanggal_masuk"] = "Gunakan tanggal yang valid."
    duplicate = get_db().execute(
        "SELECT id FROM barang WHERE LOWER(kode_barang) = LOWER(?) AND id != ?",
        (values["kode_barang"], item_id or 0),
    ).fetchone()
    if duplicate:
        errors["kode_barang"] = "Kode barang sudah digunakan."
    values["jumlah"] = quantity
    return values, errors


@app.get("/")
def index():
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("kategori", "")
    condition = request.args.get("kondisi", "")
    sort = request.args.get("urut", "baru")
    sort_sql = {
        "nama": "nama_barang COLLATE NOCASE ASC",
        "jumlah": "jumlah ASC, nama_barang COLLATE NOCASE ASC",
        "kategori": "kategori COLLATE NOCASE ASC, nama_barang COLLATE NOCASE ASC",
        "kondisi": "CASE kondisi WHEN 'Baik' THEN 1 WHEN 'Dalam Perbaikan' THEN 2 ELSE 3 END, nama_barang COLLATE NOCASE ASC",
        "baru": "id DESC",
    }.get(sort, "id DESC")
    clauses, params = [], []
    if search:
        clauses.append("(kode_barang LIKE ? OR nama_barang LIKE ? OR kategori LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if category in CATEGORIES:
        clauses.append("kategori = ?")
        params.append(category)
    if condition in CONDITIONS:
        clauses.append("kondisi = ?")
        params.append(condition)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    items = db.execute(f"SELECT * FROM barang {where} ORDER BY {sort_sql}", params).fetchall()
    return render_template(
        "index.html", items=items, summary=dashboard_data(), search=search,
        selected_category=category, selected_condition=condition, selected_sort=sort,
        categories=CATEGORIES, conditions=CONDITIONS,
    )


@app.route("/barang/tambah", methods=["GET", "POST"])
def create_item():
    values = {}
    errors = {}
    if request.method == "POST":
        values, errors = validate_form()
        if not errors:
            db = get_db()
            db.execute(
                """INSERT INTO barang (kode_barang, nama_barang, kategori, jumlah, kondisi, lokasi, tanggal_masuk, keterangan)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(values[key] for key in ("kode_barang", "nama_barang", "kategori", "jumlah", "kondisi", "lokasi", "tanggal_masuk", "keterangan")),
            )
            db.commit()
            flash("Barang berhasil ditambahkan.", "success")
            return redirect(url_for("index"))
    return render_template("form.html", item=values, errors=errors, categories=CATEGORIES, conditions=CONDITIONS, page_title="Tambah barang")


@app.route("/barang/<int:item_id>/edit", methods=["GET", "POST"])
def edit_item(item_id):
    item = get_db().execute("SELECT * FROM barang WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        abort(404)
    values = dict(item)
    errors = {}
    if request.method == "POST":
        values, errors = validate_form(item_id)
        if not errors:
            db = get_db()
            db.execute(
                """UPDATE barang SET kode_barang=?, nama_barang=?, kategori=?, jumlah=?, kondisi=?, lokasi=?,
                   tanggal_masuk=?, keterangan=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (*[values[key] for key in ("kode_barang", "nama_barang", "kategori", "jumlah", "kondisi", "lokasi", "tanggal_masuk", "keterangan")], item_id),
            )
            db.commit()
            flash("Perubahan barang berhasil disimpan.", "success")
            return redirect(url_for("index"))
    return render_template("form.html", item=values, errors=errors, categories=CATEGORIES, conditions=CONDITIONS, page_title="Ubah barang")


@app.post("/barang/<int:item_id>/hapus")
def delete_item(item_id):
    db = get_db()
    cursor = db.execute("DELETE FROM barang WHERE id = ?", (item_id,))
    db.commit()
    if cursor.rowcount:
        flash("Barang berhasil dihapus.", "success")
    else:
        flash("Barang tidak ditemukan.", "error")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
