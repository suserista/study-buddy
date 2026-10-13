""" Study Buddy — turn your course notes into flashcards, quizzes and games, powered by Google Gemini. """

import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              + GEMINI_MODEL + ":generateContent")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studybuddy.db")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")


def get_user_id():
    """Every visitor gets a random ID stored in a browser cookie (Flask session)."""
    if "user_id" not in session:
        session["user_id"] = uuid.uuid4().hex
    return session["user_id"]


# ---------- database ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_index INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS hangman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            clue TEXT NOT NULL,
            answer TEXT NOT NULL
        );
    """)
    # migration: databases created before user separation don't have the column yet
    try:
        conn.execute("ALTER TABLE decks ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists — nothing to do
    conn.commit()
    conn.close()


init_db()


# ---------- Gemini API ----------

PROMPT_TEMPLATE = """You are Study Buddy. You turn study notes into learning material.

Read the NOTES below and respond with ONLY a valid JSON object (no markdown, no extra text) in exactly this structure:

{{
  "title": "short title for the study set (max 6 words)",
  "summary": "clear summary of the notes, 150-250 words, same language as the notes",
  "flashcards": [{{"question": "...", "answer": "..."}}],
  "quiz": [{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0}}],
  "hangman": [{{"clue": "...", "answer": "WORD"}}]
}}

Rules:
- 8-12 flashcards covering the most important facts. Keep answers short (1-3 words when possible).
- 5-6 quiz questions, each with exactly 4 options and correct_index 0-3. Vary which option is correct.
- 6-8 hangman items. The answer must be ONE single word, UPPERCASE, using only letters A-Z (no spaces, digits, or special letters like Å, Ä, Ö). The clue must hint at the word without containing it.
- Write questions, clues and options in the same language as the notes.

NOTES:
{notes}"""


def clean_json(text: str) -> str:
    """Remove markdown code fences if the model added them anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_gemini(notes: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(notes=notes[:12000])}]}],
        "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
    }
    last_error = None
    for attempt in range(3):          # up to 3 attempts
        try:
            response = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY},
                                     json=payload, timeout=45)
            if response.status_code == 200:
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(clean_json(text))
            last_error = RuntimeError(
                f"Gemini API error {response.status_code}: {response.text[:300]}")
            if response.status_code != 503:   # only "busy" errors get retried
                raise last_error
        except requests.RequestException:     # network hiccups get retried too
            last_error = RuntimeError("Network error while contacting the Gemini API.")
        if attempt < 2:
            time.sleep(5)   # wait 5 seconds before trying again
    raise last_error


# ---------- routes ----------

@app.route("/")
def index():
    conn = get_db()
    decks = conn.execute(
        "SELECT id, title, created_at FROM decks WHERE user_id = ? ORDER BY id DESC",
        (get_user_id(),)).fetchall()
    conn.close()
    return render_template("index.html", decks=decks)


@app.route("/generate", methods=["POST"])
def generate():
    notes = request.form.get("notes", "").strip()
    if len(notes) < 40:
        return jsonify({"error": "Please paste more text (at least a few sentences)."}), 400
    try:
        result = call_gemini(notes)
    except Exception as exc:
        return jsonify({"error": f"Generation failed: {exc}"}), 500

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO decks (user_id, title, summary, notes, created_at) VALUES (?, ?, ?, ?, ?)",
        (get_user_id(), result.get("title", "Untitled study set"), result.get("summary", ""), notes,
         datetime.now().strftime("%Y-%m-%d %H:%M")))
    deck_id = cur.lastrowid

    for card in result.get("flashcards", []):
        conn.execute("INSERT INTO flashcards (deck_id, question, answer) VALUES (?, ?, ?)",
                     (deck_id, card.get("question", ""), card.get("answer", "")))
    for item in result.get("quiz", []):
        conn.execute("INSERT INTO quiz (deck_id, question, options, correct_index) VALUES (?, ?, ?, ?)",
                     (deck_id, item.get("question", ""), json.dumps(item.get("options", [])),
                      int(item.get("correct_index", 0))))
    for item in result.get("hangman", []):
        answer = re.sub(r"[^A-Z]", "", str(item.get("answer", "")).upper())
        if answer:
            conn.execute("INSERT INTO hangman (deck_id, clue, answer) VALUES (?, ?, ?)",
                         (deck_id, item.get("clue", ""), answer))
    conn.commit()
    conn.close()
    return jsonify({"deck_id": deck_id})


@app.route("/deck/<int:deck_id>")
def deck(deck_id):
    conn = get_db()
    deck_row = conn.execute("SELECT * FROM decks WHERE id = ? AND user_id = ?",
                            (deck_id, get_user_id())).fetchone()
    if deck_row is None:
        conn.close()
        return "Deck not found", 404
    flashcards = [dict(r) for r in conn.execute(
        "SELECT question, answer FROM flashcards WHERE deck_id = ?", (deck_id,))]
    quiz = []
    for row in conn.execute("SELECT question, options, correct_index FROM quiz WHERE deck_id = ?", (deck_id,)):
        item = dict(row)
        item["options"] = json.loads(item["options"])
        quiz.append(item)
    hangman = [dict(r) for r in conn.execute(
        "SELECT clue, answer FROM hangman WHERE deck_id = ?", (deck_id,))]
    conn.close()
    return render_template("deck.html", deck=dict(deck_row),
                           flashcards=flashcards, quiz=quiz, hangman=hangman)


@app.route("/deck/<int:deck_id>/delete", methods=["POST"])
def delete_deck(deck_id):
    conn = get_db()
    owner = conn.execute("SELECT id FROM decks WHERE id = ? AND user_id = ?",
                         (deck_id, get_user_id())).fetchone()
    if owner is None:
        conn.close()
        return redirect("/")
    conn.execute("DELETE FROM flashcards WHERE deck_id = ?", (deck_id,))
    conn.execute("DELETE FROM quiz WHERE deck_id = ?", (deck_id,))
    conn.execute("DELETE FROM hangman WHERE deck_id = ?", (deck_id,))
    conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    conn.commit()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)