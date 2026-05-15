from flask import Flask, jsonify, request, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import os
import random
import sqlite3

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "robben-dev-secret")

DB_FILE = "robben_users.db"

cards = []


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            daily_correct INTEGER DEFAULT 0,
            last_day TEXT DEFAULT '',
            known_cards TEXT DEFAULT '',
            UNIQUE(user_id, language),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def load_cards():
    loaded_cards = []

    with open("data/cards.csv", encoding="utf-8-sig") as file:
        reader = csv.reader(file, delimiter=";")
        next(reader, None)

        for row in reader:
            if not row:
                continue

            if len(row) >= 8:
                loaded_cards.append({
                    "language": row[0].strip().lower(),
                    "id": row[1],
                    "type": row[2],
                    "category": row[3],
                    "front": row[4],
                    "back": row[5],
                    "hint": row[6],
                    "example": row[7],
                    "correct": 0,
                    "wrong": 0,
                    "score": 0
                })

            elif len(row) >= 7:
                loaded_cards.append({
                    "language": "farsi",
                    "id": row[0],
                    "type": row[1],
                    "category": row[2],
                    "front": row[3],
                    "back": row[4],
                    "hint": row[5],
                    "example": row[6],
                    "correct": 0,
                    "wrong": 0,
                    "score": 0
                })

    return loaded_cards


cards = load_cards()
init_db()


def current_user_id():
    return session.get("user_id")


def pick_card(language=None, category=None):
    filtered = cards

    if language:
        filtered = [
            card for card in filtered
            if card["language"].strip().lower() == language.strip().lower()
        ]

    if category:
        filtered = [
            card for card in filtered
            if card["category"].strip().lower() == category.strip().lower()
        ]

    if not filtered:
        return None

    sorted_cards = sorted(filtered, key=lambda c: c["score"])
    weakest = sorted_cards[:3]

    return random.choice(weakest)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if len(username) < 3:
        return jsonify({
            "status": "error",
            "message": "Benutzername muss mindestens 3 Zeichen haben."
        }), 400

    if len(password) < 4:
        return jsonify({
            "status": "error",
            "message": "Passwort muss mindestens 4 Zeichen haben."
        }), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )

        conn.commit()

        user_id = cur.lastrowid
        session["user_id"] = user_id
        session["username"] = username

        return jsonify({
            "status": "ok",
            "username": username
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": "Benutzername ist schon vergeben."
        }), 400

    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

    user = cur.fetchone()
    conn.close()

    if user is None:
        return jsonify({
            "status": "error",
            "message": "Account nicht gefunden."
        }), 400

    if not check_password_hash(user["password_hash"], password):
        return jsonify({
            "status": "error",
            "message": "Falsches Passwort."
        }), 400

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "status": "ok",
        "username": user["username"]
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "status": "ok"
    })


@app.route("/api/me")
def me():
    if current_user_id() is None:
        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "username": session.get("username")
    })


@app.route("/api/progress/<language>")
def get_progress(language):
    user_id = current_user_id()

    if user_id is None:
        return jsonify({
            "logged_in": False
        }), 401

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM progress WHERE user_id = ? AND language = ?",
        (user_id, language)
    )

    row = cur.fetchone()

    if row is None:
        cur.execute("""
            INSERT INTO progress
            (user_id, language, xp, correct, wrong, streak, daily_correct, last_day, known_cards)
            VALUES (?, ?, 0, 0, 0, 0, 0, '', '')
        """, (user_id, language))

        conn.commit()

        data = {
            "xp": 0,
            "correct": 0,
            "wrong": 0,
            "streak": 0,
            "dailyCorrect": 0,
            "lastDay": "",
            "knownCards": []
        }

    else:
        known_cards = []

        if row["known_cards"]:
            known_cards = row["known_cards"].split(",")

        data = {
            "xp": row["xp"],
            "correct": row["correct"],
            "wrong": row["wrong"],
            "streak": row["streak"],
            "dailyCorrect": row["daily_correct"],
            "lastDay": row["last_day"],
            "knownCards": known_cards
        }

    conn.close()

    return jsonify(data)


@app.route("/api/progress/<language>", methods=["POST"])
def save_progress(language):
    user_id = current_user_id()

    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Nicht eingeloggt."
        }), 401

    data = request.json or {}

    known_cards = data.get("knownCards", [])

    if isinstance(known_cards, list):
        known_cards_text = ",".join(str(card_id) for card_id in known_cards)
    else:
        known_cards_text = ""

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO progress
        (user_id, language, xp, correct, wrong, streak, daily_correct, last_day, known_cards)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, language)
        DO UPDATE SET
            xp = excluded.xp,
            correct = excluded.correct,
            wrong = excluded.wrong,
            streak = excluded.streak,
            daily_correct = excluded.daily_correct,
            last_day = excluded.last_day,
            known_cards = excluded.known_cards
    """, (
        user_id,
        language,
        int(data.get("xp", 0)),
        int(data.get("correct", 0)),
        int(data.get("wrong", 0)),
        int(data.get("streak", 0)),
        int(data.get("dailyCorrect", 0)),
        data.get("lastDay", ""),
        known_cards_text
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok"
    })


@app.route("/next")
def next_card():
    card = pick_card()

    if card is None:
        return jsonify({
            "language": "",
            "id": "",
            "front": "",
            "hint": "Keine Karten gefunden",
            "back": "",
            "example": ""
        })

    return jsonify(card)


@app.route("/next/<value>")
def next_by_value(value):
    known_languages = ["farsi", "greek"]

    if value.strip().lower() in known_languages:
        card = pick_card(language=value)
    else:
        card = pick_card(category=value)

    if card is None:
        return jsonify({
            "language": "",
            "id": "",
            "front": "",
            "hint": "Keine Karten gefunden",
            "back": "",
            "example": ""
        })

    return jsonify(card)


@app.route("/next/<language>/<category>")
def next_by_language_and_category(language, category):
    card = pick_card(language=language, category=category)

    if card is None:
        return jsonify({
            "language": language,
            "id": "",
            "front": "",
            "hint": "Keine Karten in dieser Auswahl",
            "back": "",
            "example": ""
        })

    return jsonify(card)


@app.route("/rate", methods=["POST"])
def rate():
    data = request.json or {}

    rating = data.get("rating")
    card_id = data.get("card", {}).get("id")
    language = data.get("card", {}).get("language", "farsi")

    for card in cards:
        if card["id"] == card_id and card["language"] == language:
            if rating == 1:
                card["correct"] += 1
                card["score"] += 1
            else:
                card["wrong"] += 1
                card["score"] -= 1

            print("Bewertung:", card)
            break

    return jsonify({
        "status": "ok"
    })


@app.route("/stats")
def stats():
    result = {}

    for card in cards:
        language = card["language"]

        if language not in result:
            result[language] = {
                "cards": 0,
                "correct": 0,
                "wrong": 0
            }

        result[language]["cards"] += 1
        result[language]["correct"] += card["correct"]
        result[language]["wrong"] += card["wrong"]

    return jsonify(result)


@app.route("/languages")
def languages():
    available_languages = sorted(
        list(set(card["language"] for card in cards))
    )

    return jsonify({
        "languages": available_languages
    })

@app.route("/api/leaderboard/<language>")
def leaderboard(language):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            users.username,
            progress.xp,
            progress.correct,
            progress.streak
        FROM progress
        JOIN users
            ON users.id = progress.user_id
        WHERE progress.language = ?
        ORDER BY progress.xp DESC
        LIMIT 5
    """, (language,))

    rows = cur.fetchall()

    conn.close()

    result = []

    for row in rows:
        result.append({
            "username": row["username"],
            "xp": row["xp"],
            "correct": row["correct"],
            "streak": row["streak"]
        })

    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    print("🦭 Robben-Server startet...")
    print("Lokal: http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=port
    )