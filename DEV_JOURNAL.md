Entry 1 — Research & Planning (2026-10-12)
Phase: Research

Read the assignment requirements:

App with Generative AI as a central feature
Hosted on AWS (public link), simple web server
Code on GitHub
English documentation + video (min 4 min, English)
Idea chosen: Study Buddy — paste course notes, AI generates a summary,flashcards, a quiz, and a hangman-style word game from key terms.

Tools chosen and why:

Python + Flask — simple, beginner-friendly, well documented
Google Gemini API — free tier, reliable JSON output
SQLite — built into Python, no separate database server
AWS EC2 (free tier) — required by assignment
Hybrid AI workflow — Claude for architecture/code, Antigravity for running commands & git
Plan: 1) build & test locally → 2) push to GitHub → 3) deploy on EC2 → 4) docs + video

Problem: Hard to pick an app idea.Solution: Chose an idea where AI is clearly the core feature (a requirement) and which is easy to demo on video.

Entry 2 — API key format confusion
Phase: Implementation (setup)

Problem: During setup, the AI assistant (Claude) claimed my Gemini API key was wrong because it did not start with "AIza" — the older key format from its training data. The keys created by Google AI Studio today start with "AQ." instead, so following the Ai's advice would have led me to discard a perfectly valid key.

Solution: Verified against the actual source — the Google AI Studio API keys page —which labels both keys as genuine "Gemini API Keys". Kept the original key; no change needed. Lesson learned: AI assistants can state outdated information with full confidence. Always verify critical claims (credentials, versions, syntax) against the official source before acting on them. This shaped how I worked with AI for the rest of the project: AI drafts, human verifies.

Entry 3 — Commands run in the wrong folder
Problem: I opened the terminal from the Start menu, so it started in C:\Users\Q instead of the project folder. This created the virtual environment in the wrong location, and later commands (python app.py, pip install) would fail because they look for files in the folder the terminal is "standing" in.

Solution: Deleted the misplaced venv, opened the terminal directly inside the project folder (typing "cmd" in File Explorer's address bar), and re-ran the setup there. Lesson: the terminal's current folder matters — always verify with "dir" before running commands.

Entry 4 — PowerShell execution policy blocked venv activation
Problem: The terminal opened as PowerShell, which blocks running scripts by default(Windows execution policy). Running "venv\Scripts\activate" failed with "running scripts is disabled on this system", stopping the setup before dependencies could be installed.

Solution: Switched the same window to cmd by typing "cmd" (cmd does not enforce the script policy), then re-ran the activation and continued with pip install. 
Lesson: on Windows, knowing which shell you are in matters; cmd and PowerShell behave differently with scripts.

Entry 5 — Retired Gemini model name
Problem: Generation failed with a 404 error: "This model models/gemini-2.0-flash is no longer available." The model name in the code came from the AI assistant's training data, which predated Google's model update.

Solution: Read the error message carefully — it named the replacement model directly. Updated GEMINI_MODEL in app.py to "gemini-3.8-flash" and retested. 
Lesson: error messages often contain the exact fix. Read them fully before changing anything, and expect AI-generated code to contain outdated library/API versions that need updating.

Entry 6 — Gemini API temporarily overloaded (503)
Problem: After fixing the model name, generation failed with error 503:"This model is currently experiencing high demand." The request itself was now correct, but Google's servers were temporarily overloaded.

Solution: First retried manually after a short wait, which worked. Then improved robustness: updated call_gemini() to automatically retry up to 3 times with 5-second waits whenever it receives a 503 or a network error, so temporary outages are invisible to the user. 
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

