import os
import sqlite3
import string
import random
from flask import Flask, request, redirect, render_template, g, abort

app = Flask(__name__)
DATABASE = "urls.db"


@app.route("/favicon.ico")
def favicon():
    return "", 204


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                clicks INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()


def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    db = get_db()
    while True:
        code = "".join(random.choices(chars, k=length))
        existing = db.execute("SELECT id FROM urls WHERE short_code = ?", (code,)).fetchone()
        if not existing:
            return code


@app.route("/", methods=["GET", "POST"])
def index():
    short_url = None
    error = None

    if request.method == "POST":
        original_url = request.form.get("url", "").strip()
        if not original_url:
            error = "Please enter a URL."
        elif not (original_url.startswith("http://") or original_url.startswith("https://")):
            original_url = "https://" + original_url

        if not error:
            db = get_db()
            existing = db.execute(
                "SELECT short_code FROM urls WHERE original_url = ?", (original_url,)
            ).fetchone()
            if existing:
                code = existing["short_code"]
            else:
                code = generate_code()
                db.execute(
                    "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                    (code, original_url),
                )
                db.commit()
            short_url = request.host_url + code

    return render_template("index.html", short_url=short_url, error=error)


@app.route("/stats")
def stats():
    db = get_db()
    urls = db.execute(
        "SELECT short_code, original_url, clicks, created_at FROM urls ORDER BY clicks DESC"
    ).fetchall()
    total_clicks = sum(row["clicks"] for row in urls)
    return render_template("stats.html", urls=urls, total_clicks=total_clicks, host=request.host_url)


@app.route("/<code>")
def redirect_url(code):
    db = get_db()
    row = db.execute("SELECT original_url FROM urls WHERE short_code = ?", (code,)).fetchone()
    if row is None:
        abort(404)
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (code,))
    db.commit()
    return redirect(row["original_url"], code=302)


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
