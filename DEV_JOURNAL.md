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

Problem: Hard to pick an app idea. 
Solution: Chose an idea where AI is clearly the core feature (a requirement) and which is easy to demo on video.

Entry 2 — API key format confusion
Phase: Implementation (setup)

Problem: During setup, the AI assistant (Claude) claimed my Gemini API key was wrong because it did not start with "AIza" — the older key format from its training data. The keys created by Google AI Studio today start with "AQ." instead, so following the AI's advice would have led me to discard a perfectly valid key.

Solution: Verified against the actual source — the Google AI Studio API keys page —which labels both keys as genuine "Gemini API Keys". Kept the original key; no change needed. Lesson learned: AI assistants can state outdated information with full confidence. Always verify critical claims (credentials, versions, syntax) against the official source before acting on them. 

This shaped how I worked with AI for the rest of the project: AI drafts, human verifies.

Entry 4 — PowerShell execution policy blocked venv activation
Problem: The terminal opened as PowerShell, which blocks running scripts by default(Windows execution policy). Running "venv\Scripts\activate" failed with"running scripts is disabled on this system", stopping the setup before dependenciescould be installed.

Solution: Switched the same window to cmd by typing "cmd" (cmd does not enforce thescript policy), then re-ran the activation and continued with pip install.Lesson: on Windows, knowing which shell you are in matters; cmd and PowerShell behavedifferently with scripts.

