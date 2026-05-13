from flask import Flask, jsonify, request, render_template
import csv
import os
import random

app = Flask(__name__)

cards = []


def load_cards():
    loaded_cards = []

    with open("data/cards.csv", encoding="utf-8-sig") as file:
        reader = csv.reader(file, delimiter=";")
        header = next(reader, None)

        for row in reader:
            if not row:
                continue

            # Neues Format:
            # language;id;type;category;front;back;hint;example
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

            # Altes Format:
            # id;type;category;front;back;hint;example
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


def pick_card(language=None, category=None):
    filtered = cards

    if language is not None:
        filtered = [
            card for card in filtered
            if card["language"].strip().lower() == language.strip().lower()
        ]

    if category is not None:
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


# Standard: alle Karten
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


# Kompatibel mit alter App:
# /next/food = Kategorie
# /next/farsi = Sprache
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


# Neues Format:
# /next/farsi/food
# /next/greek/basic
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

    return jsonify({"status": "ok"})


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    print("🦭 Robben-Server startet...")
    print("Lokal: http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=port
    )