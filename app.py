import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for, g
from authlib.integrations.flask_client import OAuth

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "innovacoach.db")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

# Google OAuth configuration
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID", "")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET", "")

oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


COACHING_TOOLS = {
    "goal_tracker": {
        "name": "Goal Tracker",
        "description": "Definisci obiettivi SMART e monitora progressi settimanali.",
    },
    "habit_builder": {
        "name": "Habit Builder",
        "description": "Registra routine giornaliere e livello di costanza.",
    },
    "self_reflection": {
        "name": "Self Reflection",
        "description": "Annota riflessioni, apprendimenti e prossimi passi.",
    },
    "performance_review": {
        "name": "Performance Review",
        "description": "Valuta risultati con punteggi e azioni correttive.",
    },
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_sub TEXT NOT NULL,
            email TEXT NOT NULL,
            tool_key TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            score INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"), tools=COACHING_TOOLS)


@app.route("/login")
def login():
    if not app.config["GOOGLE_CLIENT_ID"] or not app.config["GOOGLE_CLIENT_SECRET"]:
        return (
            "Configura GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET nelle variabili ambiente.",
            500,
        )

    redirect_uri = url_for("authorize", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/authorize")
def authorize():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")
    if not user_info:
        user_info = google.parse_id_token(token)

    session["user"] = {
        "sub": user_info["sub"],
        "email": user_info.get("email", ""),
        "name": user_info.get("name", "Utente"),
        "picture": user_info.get("picture"),
    }
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = session["user"]
    db = get_db()
    rows = db.execute(
        """
        SELECT id, tool_key, title, notes, score, created_at
        FROM results
        WHERE google_sub = ?
        ORDER BY created_at DESC
        """,
        (user["sub"],),
    ).fetchall()
    return render_template("dashboard.html", user=user, tools=COACHING_TOOLS, rows=rows)


@app.route("/result", methods=["POST"])
@login_required
def save_result():
    user = session["user"]
    tool_key = request.form.get("tool_key", "")
    title = request.form.get("title", "").strip()
    notes = request.form.get("notes", "").strip()
    score = request.form.get("score", "").strip()

    if tool_key not in COACHING_TOOLS or not title:
        return redirect(url_for("dashboard"))

    parsed_score = int(score) if score.isdigit() else None

    db = get_db()
    db.execute(
        """
        INSERT INTO results (google_sub, email, tool_key, title, notes, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["sub"],
            user["email"],
            tool_key,
            title,
            notes,
            parsed_score,
            datetime.utcnow().isoformat(timespec="seconds") + "Z",
        ),
    )
    db.commit()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
