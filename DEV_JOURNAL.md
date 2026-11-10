Entry 1 — Research \& Planning (2026-10-12)
Phase: Research

Read the assignment requirements:

App with Generative AI as a central feature
Hosted on AWS (public link), simple web server
Code on GitHub
English documentation + video (min 4 min, English)
Idea chosen: Study Buddy — paste course notes, AI generates a summary, flashcards, a quiz, and a hangman-style word game from key terms.

Tools chosen and why:

Python + Flask — simple, beginner-friendly, well documented
Google Gemini API — free tier, reliable JSON output
SQLite — built into Python, no separate database server
AWS EC2 (free tier) — required by assignment
Hybrid AI workflow — Claude for architecture/code, Antigravity for running commands \& git
Plan: 1) build \& test locally → 2) push to GitHub → 3) deploy on EC2 → 4) docs + video

Problem: Hard to pick an app idea. Solution: Chose an idea where AI is clearly the core feature (a requirement) and which is easy to demo on video.

Entry 2 — API key format confusion
Phase: Implementation (setup)

Problem: During setup, the AI assistant (Claude) claimed my Gemini API key was wrong because it did not start with "AIza" — the older key format from its training data. The keys created by Google AI Studio today start with "AQ." instead, so following the Ai's advice would have led me to discard a perfectly valid key.

Solution: Verified against the actual source — the Google AI Studio API keys page —which labels both keys as genuine "Gemini API Keys". Kept the original key; no change needed. Lesson learned: AI assistants can state outdated information with full confidence. Always verify critical claims (credentials, versions, syntax) against the official source before acting on them. This shaped how I worked with AI for the rest of the project: AI drafts, human verifies.

Entry 3 — Commands run in the wrong folder
Problem: I opened the terminal from the Start menu, so it started in C:\\Users\\Q instead of the project folder. This created the virtual environment in the wrong location, and later commands (python app.py, pip install) would fail because they look for files in the folder the terminal is "standing" in.

Solution: Deleted the misplaced venv, opened the terminal directly inside the project folder (typing "cmd" in File Explorer's address bar), and re-ran the setup there. Lesson: the terminal's current folder matters — always verify with "dir" before running commands.

Entry 4 — PowerShell execution policy blocked venv activation
Problem: The terminal opened as PowerShell, which blocks running scripts by default(Windows execution policy). Running "venv\\Scripts\\activate" failed with "running scripts is disabled on this system", stopping the setup before dependencies could be installed.

Solution: Switched the same window to cmd by typing "cmd" (cmd does not enforce the script policy), then re-ran the activation and continued with pip install.
Lesson: on Windows, knowing which shell you are in matters; cmd and PowerShell behave differently with scripts.

Entry 5 — Retired Gemini model name
Problem: Generation failed with a 404 error: "This model models/gemini-2.0-flash is no longer available." The model name in the code came from the AI assistant's training data, which predated Google's model update.

Solution: Read the error message carefully — it named the replacement model directly. Updated GEMINI\_MODEL in app.py to "gemini-3.8-flash" and retested.
Lesson: error messages often contain the exact fix. Read them fully before changing anything, and expect AI-generated code to contain outdated library/API versions that need updating.

Entry 6 — Gemini API temporarily overloaded (503)
Problem: After fixing the model name, generation failed with error 503:"This model is currently experiencing high demand." The request itself was now correct, but Google's servers were temporarily overloaded.

Solution: First retried manually after a short wait, which worked. Then improved robustness: updated call\_gemini() to automatically retry up to 3 times with 5-second waits whenever it receives a 503 or a network error, so temporary outages are invisible to the user.
Lesson: external APIs can fail for reasons outside your own code —robust applications expect transient errors and retry instead of crashing.

Entry 7 — First successful generation (milestone)
Phase: Implementation

After the fixes, the full pipeline worked end-to-end for the first time: pasted real course notes → Gemini returned structured study material → the app saved it and rendered the summary, flashcards, quiz and hangman all working. Had to click retry a few times through 503 "high demand" responses, which motivated adding automatic retries to the code.



Entry 8 — Published to GitHub
Phase: Implementation

Pushed the project to GitHub using an AI agent (Antigravity) with explicit security instructions: before committing, verified via the commit file list that .env (the secret API key file) was excluded by .gitignore — 9 files committed, no secrets included. The repository now serves as backup and as the deployment source for AWS: the EC2server will clone the code directly from GitHub.

Problem: Risk of accidentally publishing the API key. Solution: .gitignore plus manual verification of the committed file list before pushing.

Entry 9 — Wrong OS on the EC2 instance (Amazon Linux vs Ubuntu)
Problem: First attempt to install packages on the server failed with "sudo: apt: command not found". The launch wizard defaults to Amazon Linux, and I had not actively selected Ubuntu. Amazon Linux uses yum/dnf instead of apt, and a different default username (ec2-user instead of ubuntu), so none of the setup commands matched.

Solution: Identified the OS from the terminal prompt (ec2-user = Amazon Linux), terminated the empty instance, and launched a new one explicitly selecting Ubuntu Server 24.04 LTS. Reused the existing security group (port 5000 rule already configured). Verified the newprompt reads ubuntu@... before continuing.
Lesson: cloud launch wizards have defaults — always confirm the OS/AMI selection matches your instructions, and use the shell prompt as a quick sanity check of what you're connected to.

Entry 10 — Deployed on AWS EC2 (milestone)
Phase: Implementation → Completion

After relaunching with Ubuntu, completed the full setup: cloned the repo from GitHub, created the venv, installed dependencies, added the .env key on the server, and verified the app responded through the public IP (smoke test via Flask's development server).

Then replaced the dev server with gunicorn and registered it as a systemd service(Restart=always), so the app starts on boot and survives crashes and disconnects —verified by closing the SSH session while the app kept serving.

Key insight: "venv activation" only affects the current shell; the systemd unit uses absolute paths into the venv, so the service is independent of any terminal session.

Entry 11 — Shared history across visitors (self-identified UX flaw)
Phase: Completion / improvements

Problem: While testing from two devices, I noticed the "Your study sets" list was shared —every visitor saw (and could delete) everyone's study sets. The app had a single database and no concept of users at all.

Solution: Implemented per-visitor separation using Flask sessions: each browser receives a random user ID in a signed cookie; decks are tagged with that ID on creation, and listing, viewing and deleting are all filtered by it. Added a database migration (ALTER TABLE wrapped in try/except) so existing databases upgrade automatically. Verified with an incognito window acting as a second user with an empty, separate history.

Future improvement: real user accounts with login, so history survives across devices —out of scope for the deadline.

Entry 12 — Server returned HTML instead of JSON (frontend crash)

Problem: Testing from my phone after deployment, generation failed with a cryptic browser error: "Unexpected token '<'... is not valid JSON". The page loaded fine — the server was answering the generate request with an HTML error page, and the frontend JavaScript crashed trying to parse it as JSON, hiding the real cause.

Diagnosis: Read the server logs (journalctl -u studybuddy) instead of guessing. Root cause: gunicorn's default 30-second worker timeout killed the worker while the Gemini retry logic was still waiting for an answer.

Fixes applied:

Raised the gunicorn worker timeout from the 30s default to 180s — the retry logic can legitimately need over 30 seconds when the Gemini API is busy, but gunicorn killed the worker first. The layer timeouts must fit together (requests timeout reduced to 45s so the worst case stays under 180s).

Frontend now detects non-JSON responses and shows a readable error message instead of a raw parser error.

Lesson: when a client shows a parsing error, the real bug is on the server — read the server logs. And timeouts across layers must be designed together, not individually.



Entry 13 — Model-specific Gemini outage, diagnosed with a controlled experiment

Problem: After the timeout fixes, generation still failed — now with "Network error while contacting the Gemini API" after \~2.5 minutes (matching 3 attempts x 45s exactly).

Diagnosis (controlled experiments, one variable at a time):

Ran a minimal request to Gemini directly from the server (bypassing the app): no answer for 120 seconds even for a one-word prompt -> the app was not the problem.

Ran the identical request from my home PC: identical failure -> not an AWS/network problem.

Queried Google's List Models API and pinged each flash model individually: some models answered in under 1 second while gemini-3.8-flash (the one the earlier error message had recommended) returned silence. Conclusion: a model-specific outage at Google.

Solution: Switched to a working model (gemini-flash-lite-latest) and added a fallback list — the app now tries models in order and only fails if ALL are down. Within 24 hours I had seen three different models fail in three different ways (404 retired, 503 busy, silent timeout), which is exactly why fallback chains are standard practice for external APIs.

Lesson: When an external dependency fails:
(1) test the dependency directly, bypassing your own code;
(2) test from a second location to rule out local network issues;
(3) consult the dependency's own discovery endpoints for ground truth instead of trusting cached knowledge.



Entry 14 — Structured Study Guide with Depth Levels and "Explain Simpler" Feature
Phase: Implementation / Feature Enhancement

Problem: The original version only generated a single flat summary paragraph. For richer study sessions, learners need structured breakdowns with headings, key terms, takeaways, and study tips, as well as the ability to choose guide depth or request simpler explanations for hard-to-understand sections.

Solution:
- Upgraded the prompt in app.py to generate a structured JSON study guide (overview, titled sections, key terms with definitions, takeaways, and tips) instead of just plain summary text.
- Added guide depth selection (Quick overview, Standard, Exam prep) directly from the home page.
- Added an "Explain simpler" feature (/deck/<id>/explain endpoint) allowing users to trigger a targeted AI rewrite for any individual section on demand.
- Implemented automatic, backward-compatible SQLite migration: added a `study_guide` column dynamically on startup without breaking existing decks. If the AI returns an unexpected structure, the app cleanly falls back to the classic summary text.
- Updated templates (index.html, deck.html) and styled the new components (depth buttons, section cards, key term grid) maintaining responsive mobile/desktop design.



Entry 15 — Quiz 2.0: mixed question types, explanations, best score (2026-11-09)
Phase: Feature enhancement

What was built:
- The quiz was rebuilt from plain multiple choice into a 10-question round mixing four types: multiple choice, true/false, fill-in-the-blank and matching. Questions and answer options are reshuffled every round, so memorising the order does not help.
- Every answer is followed by a short explanation of WHY it is correct, and the end screen shows a full answer review of all 10 questions.
- The best score per study set is saved on the server and shown as a gold badge, with a "new best score" highlight.

Problems solved:
- Fill-in-the-blank was judged too strictly — one typo failed the whole answer. Solution: answers are normalised (case, punctuation, spacing) and answers of 5+ characters may still pass with one small typo.
- The physical-keyboard listener for the hangman game also captured letters typed into the new quiz answer fields. Solution: the listener now ignores keystrokes that happen inside input, select and textarea elements.
- One malformed AI question could break the whole quiz. Solution: every question is validated before saving, and unusable items are skipped instead of crashing the round.
- A quiz score sent from the browser can be faked. Solution: the total is always counted from the database, and score range and ownership are checked on the server.

Commit: 5d68623 "Quiz 2.0: mixed question types, explanations, best score + footer on deck page"
Deployed and verified live: 2026-11-09



Entry 16 — "Ask your notes": grounded chat about each study set (2026-11-10)
Phase: Feature enhancement

What was built:
- A new "Ask" tab on every study set: the student types questions and the AI answers ONLY from that set's notes — same language as the question.
- The prompt forbids inventing facts: if the notes do not cover the question, the AI must say so honestly.
- The conversation is saved per study set and per visitor, so it survives a page refresh; the last 12 turns are sent back to the AI so it has memory of the conversation; a Clear chat button deletes everything.

Problems solved:
- A plain chatbot could have invented plausible-sounding facts. Solution: strict grounding prompt ("answer ONLY using the STUDY MATERIAL below") plus the honest "not in your notes" rule.
- Sending the whole history every time would grow the token cost with every question. Solution: only the last 12 turns are included; the page shows up to 60.
- Refreshing the page used to lose the conversation. Solution: history is stored in a new chat_messages table (automatic migration), rendered newest-last on load.

Commit: 2a703b9 "Ask your notes: grounded chat about each study set"
Deployed and verified live: 2026-11-10



Entry 17 — Quick wins, credit guard and project polish (2026-11-10)
Phase: Completion / hardening

What was built:
- "Try the example" button on the home page: a ready-made Photosynthesis study set appears instantly with ZERO Gemini calls, so the app can be demonstrated without notes and without spending budget. A second click returns the same deck instead of creating a duplicate.
- Flashcard upgrades: shuffle, keyboard shortcuts (arrows, Space, S, G), "got it" tracking with a Still-learning mode (saved in the browser, survives refresh), read-aloud using the browser's built-in speech synthesis (free), and one-click export to Anki as a tab-separated file.
- API rate limiting: every route that calls Gemini first checks a per-visitor limit (20 per hour, 60 per day) and a global daily cap (300), and answers with a friendly "take a break" message instead of a raw error.
- Professional README with screenshots, GitHub About section with topics, and journal catch-up (Entries 15-17 plus the root cause filled into Entry 12).

Problems solved:
- Rate-limit counters stored in a Python variable would be wrong twice: gunicorn runs several worker processes (each with its own memory), and a restart would forget everything. Solution: the counters live in a new SQLite api_hits table — shared between workers and permanent.
- The new flashcard shortcuts (S for shuffle, G for got-it) clashed with the hangman game, which listens for letters. Solution: hangman now only listens while its tab is open — which also fixes letters being "guessed" invisibly while browsing other tabs.
- A real .apkg export would have needed a new Python package and a changed deployment. Solution: plain tab-separated text, which Anki imports natively (File > Import) — deployment stays `git pull` + restart.

Commits: "Quick wins: example deck, flashcard upgrades, Anki export + API rate limiting" and "Add README with screenshots and complete the DEV_JOURNAL"
Deployed and verified live: 2026-11-10
