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
    # migration v3: Quiz 2.0 — question types + explanations. Old questions have
    # no qtype and are treated as plain multiple choice, so old decks keep working.
    for column in ("qtype", "extra", "explanation"):
        try:
            conn.execute(f"ALTER TABLE quiz ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists — nothing to do
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_best (
            deck_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            best_score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (deck_id, user_id)
        )
    """)
    # migration v4: "Ask your notes" chat. A new table only — old databases
    # are not touched, the chat simply starts empty for every existing deck.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
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
  "quiz": [
    {{"type": "mc", "question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, "explanation": "..."}},
    {{"type": "tf", "question": "...", "answer": true, "explanation": "..."}},
    {{"type": "fill", "question": "... ______ ...", "accepted": ["...", "..."], "explanation": "..."}},
    {{"type": "match", "question": "Match each term with its meaning", "pairs": [{{"left": "...", "right": "..."}}], "explanation": "..."}}
  ],
  "hangman": [{{"clue": "...", "answer": "WORD"}}]
}}

Rules for the study guide:
- {difficulty_instruction}
- 3-5 sections, each with a clear descriptive heading. Write full sentences, same language as the notes.
- 4-8 glossary terms with short, clear definitions.
- 4-6 takeaways: the facts a student absolutely must remember from these notes.
- 2-4 study tips that are concrete and specific to THIS material (not generic advice).

Rules for the quiz (exactly 10 questions):
- Mix of question types: 5-6 of type "mc", 2 of type "tf", 1-2 of type "fill", 1-2 of type "match". Mix the order, do not group same types together.
- "mc": 4 options, correct_index 0-3. Vary which option is correct.
- "tf": "answer" is true or false. The statement must be clearly true or clearly false.
- "fill": the question contains exactly one blank written as ______ (six underscores), and "accepted" lists 1-3 acceptable short answers.
- "match": "pairs" contains exactly 4 pairs, each {{"left": a short term, "right": its matching definition or translation}}. All "right" values must be different.
- EVERY question has an "explanation": 1-2 sentences that teach the student WHY the answer is correct.

Rules for the rest:
- 8-12 flashcards covering the most important facts. Keep answers short (1-3 words when possible).
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

CHAT_PROMPT = """You are Study Buddy, a friendly study assistant. A student pasted their own
course notes and asks you questions about them.

Rules:
- Answer ONLY using the STUDY MATERIAL below. If the answer is not in the material,
  say honestly that these notes do not cover it — do not invent facts.
- Keep answers short and clear: 1-4 sentences. For a list, put each item on its own line.
- Write in the same language the student uses in their question.
- Do NOT use markdown formatting (no **, no #). Plain text only.
- You may use the earlier conversation for context (e.g. "as I said before...").

STUDY MATERIAL:
{notes}

{history}STUDENT: {question}

STUDY BUDDY:"""


def clean_json(text: str) -> str:
    """Remove markdown code fences if the model added them anyway."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _gemini_request(prompt, as_json=True):
    """Send one prompt to Gemini, trying each model in order.
    Returns parsed JSON (as_json=True) or plain text (as_json=False)."""
    if as_json:
        generation = {"temperature": 0.4, "responseMimeType": "application/json"}
    else:
        generation = {"temperature": 0.3}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation,
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
                    if as_json:
                        return json.loads(clean_json(text))
                    return text.strip()
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


def call_gemini_chat(notes, history, question):
    """Answer a question about the student's own notes (grounded, with history)."""
    prompt = CHAT_PROMPT.format(notes=notes[:10000], history=history,
                                question=question[:1000])
    return _gemini_request(prompt, as_json=False)


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


QUIZ_TYPES = ("mc", "tf", "fill", "match")


def _clean_quiz_item(item):
    """Validate and normalise one quiz question returned by Gemini.

    Returns a tuple ready for the database
    (question, options, correct_index, qtype, extra, explanation),
    or None if the question is unusable — broken questions are skipped
    so one bad item can not ruin the whole quiz.
    """
    if not isinstance(item, dict):
        return None
    qtype = str(item.get("type", "mc")).strip().lower()
    if qtype not in QUIZ_TYPES:
        qtype = "mc"
    question = _strip_markdown(str(item.get("question", "")))
    explanation = _strip_markdown(str(item.get("explanation", "")))
    if not question:
        return None

    if qtype == "tf":
        answer = str(item.get("answer")).strip().lower()
        if answer == "true":
            correct_index = 0
        elif answer == "false":
            correct_index = 1
        else:
            return None  # no clear true/false — unusable
        return question, json.dumps(["True", "False"]), correct_index, "tf", None, explanation

    if qtype == "fill":
        if "___" not in question:
            return None  # the blank is missing — the question would be confusing
        accepted = []
        for value in item.get("accepted", []):
            text = _strip_markdown(str(value)).strip()
            if text and text not in accepted:
                accepted.append(text)
        if not accepted:
            return None
        return question, "[]", 0, "fill", json.dumps({"accepted": accepted[:5]}), explanation

    if qtype == "match":
        pairs = []
        for pair in item.get("pairs", []):
            if not isinstance(pair, dict):
                continue
            left = _strip_markdown(str(pair.get("left", "")))
            right = _strip_markdown(str(pair.get("right", "")))
            if left and right and all(p["left"] != left for p in pairs):
                pairs.append({"left": left, "right": right})
        if len(pairs) < 3:
            return None  # a matching question needs at least 3 pairs
        return question, "[]", 0, "match", json.dumps({"pairs": pairs[:6]}), explanation

    # default: multiple choice (also the only format decks made before Quiz 2.0 use)
    options = []
    for value in item.get("options", []):
        text = _strip_markdown(str(value)).strip()
        if text:
            options.append(text)
    if len(options) < 2:
        return None
    try:
        correct_index = int(item.get("correct_index", 0))
    except (TypeError, ValueError):
        correct_index = 0
    correct_index = max(0, min(correct_index, len(options) - 1))
    return question, json.dumps(options[:6]), correct_index, "mc", None, explanation


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
        row = _clean_quiz_item(item)
        if row is None:
            continue  # skip unusable questions, keep the rest
        conn.execute(
            "INSERT INTO quiz (deck_id, question, options, correct_index, qtype, extra, explanation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (deck_id, *row))
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
    for row in conn.execute(
            "SELECT question, options, correct_index, qtype, extra, explanation "
            "FROM quiz WHERE deck_id = ? ORDER BY id", (deck_id,)):
        item = dict(row)
        item["options"] = json.loads(item["options"] or "[]")
        item["qtype"] = item["qtype"] or "mc"
        extra = json.loads(item["extra"]) if item["extra"] else {}
        if item["qtype"] == "fill":
            item["accepted"] = extra.get("accepted", [])
        elif item["qtype"] == "match":
            item["pairs"] = extra.get("pairs", [])
        item["explanation"] = item["explanation"] or ""
        del item["extra"]
        quiz.append(item)
    hangman = [dict(r) for r in conn.execute(
        "SELECT clue, answer FROM hangman WHERE deck_id = ?", (deck_id,))]
    guide = None
    if deck_row["study_guide"]:
        try:
            guide = json.loads(deck_row["study_guide"])
        except ValueError:
            guide = None
    best = conn.execute(
        "SELECT best_score, total FROM quiz_best WHERE deck_id = ? AND user_id = ?",
        (deck_id, get_user_id())).fetchone()
    # "Ask your notes" conversation — newest last, capped so the page stays light
    chat_rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE deck_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT 60", (deck_id, get_user_id())).fetchall()
    chat = [dict(r) for r in reversed(chat_rows)]
    conn.close()
    return render_template("deck.html", deck=dict(deck_row),
                           flashcards=flashcards, quiz=quiz, hangman=hangman, guide=guide,
                           quiz_best=dict(best) if best else None, chat=chat)


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


def _format_chat_history(rows):
    """Turn stored chat messages into prompt text. Empty conversation -> no block."""
    if not rows:
        return ""
    lines = ["CONVERSATION SO FAR:"]
    for row in rows:
        who = "STUDENT" if row["role"] == "user" else "STUDY BUDDY"
        lines.append(f"{who}: {row['content']}")
    return "\n".join(lines) + "\n\n"


@app.route("/deck/<int:deck_id>/ask", methods=["POST"])
def ask_deck(deck_id):
    """Answer a question about the deck's notes, grounded in the notes only."""
    user_id = get_user_id()
    conn = get_db()
    deck_row = conn.execute("SELECT * FROM decks WHERE id = ? AND user_id = ?",
                            (deck_id, user_id)).fetchone()
    if deck_row is None:
        conn.close()
        return jsonify({"error": "Study set not found."}), 404

    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()[:1000]
    if len(question) < 2:
        conn.close()
        return jsonify({"error": "Please type a question first."}), 400

    # the last few turns give the AI conversation memory
    history_rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE deck_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT 12", (deck_id, user_id)).fetchall()
    history = _format_chat_history(list(reversed([dict(r) for r in history_rows])))
    conn.close()

    try:
        answer = call_gemini_chat(deck_row["notes"], history, question)
    except Exception as exc:
        # nothing is saved — the student can simply ask again
        return jsonify({"error": f"Could not reach the AI: {exc}"}), 500
    answer = str(answer or "").strip()
    if not answer:
        return jsonify({"error": "The AI returned an empty answer. Please try again."}), 502

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    conn.execute("INSERT INTO chat_messages (deck_id, user_id, role, content, created_at) "
                 "VALUES (?, ?, 'user', ?, ?)", (deck_id, user_id, question, now))
    conn.execute("INSERT INTO chat_messages (deck_id, user_id, role, content, created_at) "
                 "VALUES (?, ?, 'assistant', ?, ?)", (deck_id, user_id, answer, now))
    conn.commit()
    conn.close()
    return jsonify({"question": question, "answer": answer})


@app.route("/deck/<int:deck_id>/clear-chat", methods=["POST"])
def clear_chat(deck_id):
    """Delete the saved conversation for this study set."""
    conn = get_db()
    owner = conn.execute("SELECT id FROM decks WHERE id = ? AND user_id = ?",
                         (deck_id, get_user_id())).fetchone()
    if owner is None:
        conn.close()
        return jsonify({"error": "Study set not found."}), 404
    conn.execute("DELETE FROM chat_messages WHERE deck_id = ? AND user_id = ?",
                 (deck_id, get_user_id()))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/deck/<int:deck_id>/quiz-score", methods=["POST"])
def save_quiz_score(deck_id):
    """Remember the student's best quiz score for this study set."""
    user_id = get_user_id()
    conn = get_db()
    owner = conn.execute("SELECT id FROM decks WHERE id = ? AND user_id = ?",
                         (deck_id, user_id)).fetchone()
    if owner is None:
        conn.close()
        return jsonify({"error": "Study set not found."}), 404
    # the total always comes from the database, so it can not be faked
    total = conn.execute("SELECT COUNT(*) FROM quiz WHERE deck_id = ?",
                         (deck_id,)).fetchone()[0]
    data = request.get_json(silent=True) or {}
    try:
        score = int(data.get("score"))
    except (TypeError, ValueError):
        conn.close()
        return jsonify({"error": "Invalid score."}), 400
    if total <= 0 or not 0 <= score <= total:
        conn.close()
        return jsonify({"error": "Invalid score."}), 400

    row = conn.execute("SELECT best_score FROM quiz_best WHERE deck_id = ? AND user_id = ?",
                       (deck_id, user_id)).fetchone()
    if row is None:
        conn.execute("INSERT INTO quiz_best (deck_id, user_id, best_score, total, updated_at) "
                     "VALUES (?, ?, ?, ?, ?)",
                     (deck_id, user_id, score, total,
                      datetime.now().strftime("%Y-%m-%d %H:%M")))
        best, new_best = score, True
    elif score > row["best_score"]:
        conn.execute("UPDATE quiz_best SET best_score = ?, total = ?, updated_at = ? "
                     "WHERE deck_id = ? AND user_id = ?",
                     (score, total, datetime.now().strftime("%Y-%m-%d %H:%M"),
                      deck_id, user_id))
        best, new_best = score, True
    else:
        best, new_best = row["best_score"], False
    conn.commit()
    conn.close()
    return jsonify({"best": best, "total": total, "new_best": new_best})


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
    conn.execute("DELETE FROM quiz_best WHERE deck_id = ?", (deck_id,))
    conn.execute("DELETE FROM chat_messages WHERE deck_id = ?", (deck_id,))
    conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    conn.commit()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug)
