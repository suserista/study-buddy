"""Study Buddy — turn your course notes into flashcards, quizzes and games, powered by Google Gemini."""

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
GEMINI_MODELS = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-flash-latest"]

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
    # migration v2: structured study guide. Decks created before this feature
    # keep working — they simply have no guide and fall back to the old summary.
    try:
        conn.execute("ALTER TABLE decks ADD COLUMN study_guide TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists — nothing to do
    conn.commit()
    conn.close()


init_db()


# ---------- Gemini API ----------

# Guide depth chosen on the home page — changes what the AI is asked to write.
DIFFICULTY_LEVELS = {
    "quick": (
        "QUICK OVERVIEW mode: keep it high-level. Short sections (2-3 sentences each), "
        "focus on the big picture, skip minor details."
    ),
    "standard": (
        "STANDARD mode: balanced depth. Sections of 3-5 sentences covering the main "
        "ideas and the most useful details."
    ),
    "exam": (
        "EXAM PREP mode: written for exam preparation. Longer, detailed sections with "
        "definitions, relationships between concepts and the points most likely to "
        "appear in an exam."
    ),
}

PROMPT_TEMPLATE = """You are Study Buddy. You turn study notes into learning material.

Read the NOTES below and respond with ONLY a valid JSON object (no markdown, no extra text) in exactly this structure:

{{
  "title": "short title for the study set (max 6 words)",
  "guide": {{
    "overview": "2-3 sentence overview of what the notes are about",
    "sections": [{{"heading": "short descriptive heading", "content": "the section text"}}],
    "glossary": [{{"term": "key term", "definition": "one clear sentence"}}],
    "takeaways": ["the most important point", "..."],
    "tips": ["concrete study tip for this material", "..."]
  }},
  "flashcards": [{{"question": "...", "answer": "..."}}],
  "quiz": [{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0}}],
  "hangman": [{{"clue": "...", "answer": "WORD"}}]
}}

Rules for the study guide:
- {difficulty_instruction}
- 3-5 sections, each with a clear descriptive heading. Write full sentences, same language as the notes.
- 4-8 glossary terms with short, clear definitions.
- 4-6 takeaways: the facts a student absolutely must remember from these notes.
- 2-4 study tips that are concrete and specific to THIS material (not generic advice).

Rules for the rest:
- 8-12 flashcards covering the most important facts. Keep answers short (1-3 words when possible).
- 5-6 quiz questions, each with exactly 4 options and correct_index 0-3. Vary which option is correct.
- 6-8 hangman items. The answer must be ONE single word, UPPERCASE, using only letters A-Z (no spaces, digits, or special letters like Å, Ä, Ö). The clue must hint at the word without containing it.
- Write everything in the same language as the notes.
- Do NOT use markdown formatting (no **, no #, no bullet dashes) anywhere in the text.

NOTES:
{notes}"""

EXPLAIN_PROMPT = """You are Study Buddy. A student finds one section of their study guide hard to read.
Rewrite the section below in simpler, easier language.

Rules:
- Write in the same language as the section text.
- Keep every fact and the meaning of the heading; use shorter sentences and everyday words.
- Do NOT use markdown formatting.
- Respond with ONLY a valid JSON object: {{"content": "the rewritten section text"}}

SECTION HEADING: {heading}

SECTION TEXT:
{content}"""


def clean_json(text: str) -> str:
    """Remove markdown code fences if the model added them anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _gemini_request(prompt):
    """Send one prompt to Gemini, trying each model in order. Returns parsed JSON."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
    }
    last_error = None
    for model in GEMINI_MODELS:
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        for attempt in range(2):          # 2 attempts per model
            try:
                response = requests.post(url, params={"key": GEMINI_API_KEY},
                                         json=payload, timeout=45)
                if response.status_code == 200:
                    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(clean_json(text))
                last_error = RuntimeError(
                    f"Gemini API error {response.status_code} on {model}: {response.text[:300]}")
                if response.status_code != 503:   # only "busy" gets retried
                    break
            except (requests.RequestException, ValueError):
                # network failure, or the model returned broken JSON -> try next model
                last_error = RuntimeError(f"Request failed on model {model}.")
                break
            time.sleep(3)
    raise last_error


def call_gemini(notes, difficulty="standard"):
    """Generate the full study set (guide, flashcards, quiz, hangman) from notes."""
    prompt = PROMPT_TEMPLATE.format(
        difficulty_instruction=DIFFICULTY_LEVELS.get(difficulty, DIFFICULTY_LEVELS["standard"]),
        notes=notes[:12000])
    return _gemini_request(prompt)


def call_gemini_explain(heading, content):
    """Rewrite ONE study guide section in simpler language."""
    result = _gemini_request(EXPLAIN_PROMPT.format(heading=heading, content=content))
    return str(result.get("content", "")).strip()


def _strip_markdown(text):
    """The prompt forbids markdown, but models add it anyway — remove the basics."""
    text = text.replace("**", "")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def clean_guide(guide):
    """Validate and normalise the guide object returned by Gemini.
    Returns a clean guide dict, or None if the guide is unusable
    (in that case the app falls back to the old plain summary)."""
    if not isinstance(guide, dict):
        return None

    def text_list(value, limit):
        if not isinstance(value, list):
            return []
        return [_strip_markdown(str(v)) for v in value if str(v).strip()][:limit]

    sections = []
    if isinstance(guide.get("sections"), list):
        for s in guide["sections"][:8]:
            if not isinstance(s, dict):
                continue
            heading = _strip_markdown(str(s.get("heading", "")))
            content = _strip_markdown(str(s.get("content", "")))
            if heading and content:
                sections.append({"heading": heading, "content": content})

    glossary = []
    if isinstance(guide.get("glossary"), list):
        for g in guide["glossary"][:10]:
            if not isinstance(g, dict):
                continue
            term = _strip_markdown(str(g.get("term", "")))
            definition = _strip_markdown(str(g.get("definition", "")))
            if term and definition:
                glossary.append({"term": term, "definition": definition})

    cleaned = {
        "overview": _strip_markdown(str(guide.get("overview", ""))),
        "sections": sections,
        "glossary": glossary,
        "takeaways": text_list(guide.get("takeaways"), 8),
        "tips": text_list(guide.get("tips"), 6),
    }
    if not cleaned["overview"] and not cleaned["sections"]:
        return None
    return cleaned


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
    difficulty = request.form.get("difficulty", "standard")
    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = "standard"
    if len(notes) < 40:
        return jsonify({"error": "Please paste more text (at least a few sentences)."}), 400
    try:
        result = call_gemini(notes, difficulty)
    except Exception as exc:
        return jsonify({"error": f"Generation failed: {exc}"}), 500

    guide = clean_guide(result.get("guide"))
    # The old plain-text summary stays as a fallback: if the guide is missing,
    # the study set still opens and shows the summary like before.
    if guide and guide["overview"]:
        summary_text = guide["overview"]
    else:
        summary_text = _strip_markdown(str(result.get("summary", "")))[:1000]

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO decks (user_id, title, summary, notes, created_at, study_guide) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (get_user_id(), result.get("title", "Untitled study set"), summary_text, notes,
         datetime.now().strftime("%Y-%m-%d %H:%M"),
         json.dumps(guide) if guide else None))
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
    guide = None
    if deck_row["study_guide"]:
        try:
            guide = json.loads(deck_row["study_guide"])
        except ValueError:
            guide = None
    conn.close()
    return render_template("deck.html", deck=dict(deck_row),
                           flashcards=flashcards, quiz=quiz, hangman=hangman, guide=guide)


@app.route("/deck/<int:deck_id>/explain", methods=["POST"])
def explain_section(deck_id):
    """Rewrite one guide section in simpler language."""
    conn = get_db()
    owner = conn.execute("SELECT id FROM decks WHERE id = ? AND user_id = ?",
                         (deck_id, get_user_id())).fetchone()
    conn.close()
    if owner is None:
        return jsonify({"error": "Study set not found."}), 404

    data = request.get_json(silent=True) or {}
    heading = str(data.get("heading", ""))[:200]
    content = str(data.get("content", ""))[:4000]
    if len(content) < 10:
        return jsonify({"error": "Nothing to simplify."}), 400
    try:
        simpler = call_gemini_explain(heading, content)
    except Exception as exc:
        return jsonify({"error": f"Could not simplify this section: {exc}"}), 500
    if not simpler:
        return jsonify({"error": "The AI returned an empty answer. Please try again."}), 502
    return jsonify({"content": simpler})


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
