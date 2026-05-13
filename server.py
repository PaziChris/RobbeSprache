from flask import Flask, jsonify, request, render_template
import csv
import random

app = Flask(__name__)

cards = []

with open("data/cards.csv", encoding="utf-8-sig") as file:

    reader = csv.reader(file, delimiter=";")

    next(reader, None)

    for row in reader:

        if len(row) < 7:
            continue

        cards.append({
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

index = 0


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/next")
def next_card():

    if not cards:
        return jsonify({
            "front": "",
            "hint": "Keine Karten gefunden",
            "back": "",
            "example": ""
        })

    sorted_cards = sorted(cards, key=lambda c: c["score"])

    weakest = sorted_cards[:3]

    card = random.choice(weakest)

    return jsonify(card)


@app.route("/next/<category>")
def next_card_by_category(category):

    filtered = [
        card for card in cards
        if card["category"].strip().lower() == category.strip().lower()
    ]

    if not filtered:
        return jsonify({
            "front": "",
            "hint": "Keine Karten in dieser Kategorie",
            "back": "",
            "example": ""
        })

    sorted_cards = sorted(filtered, key=lambda c: c["score"])

    weakest = sorted_cards[:3]

    card = random.choice(weakest)

    return jsonify(card)


@app.route("/rate", methods=["POST"])
def rate():

    data = request.json

    rating = data.get("rating")

    card_id = data.get("card", {}).get("id")

    for card in cards:

        if card["id"] == card_id:

            if rating == 1:

                card["correct"] += 1

                card["score"] += 1

            else:

                card["wrong"] += 1

                card["score"] -= 1

            print(card)

            break

    return jsonify({
        "status": "ok"
    })


@app.route("/stats")
def stats():

    total_correct = 0
    total_wrong = 0

    for card in cards:
        total_correct += card["correct"]
        total_wrong += card["wrong"]

    return jsonify({
        "cards": len(cards),
        "correct": total_correct,
        "wrong": total_wrong
    })


if __name__ == "__main__":

    print("🦭 Robben-Server startet...")
    print("PC: http://127.0.0.1:5000")
    print("iPhone: http://192.168.0.212:5000")

    app.run(
        host="192.168.0.153",
        port=5000,
        debug=True
    )