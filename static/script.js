// ---------- tabs ----------
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ---------- study guide ----------

// Safely show AI text: escapes HTML so nothing can break out of the page.
function esc(text) {
  const div = document.createElement('div');
  div.textContent = text == null ? '' : String(text);
  return div.innerHTML;
}

function renderGuide() {
  const root = document.getElementById('guide-root');
  if (!root || !GUIDE) return;   // old study sets have no guide — nothing to do

  let html = '';
  if (GUIDE.overview) {
    html += `<p class="guide-overview">${esc(GUIDE.overview)}</p>`;
  }

  (GUIDE.sections || []).forEach((s, i) => {
    html += `
      <div class="guide-section" id="guide-section-${i}">
        <h3>${esc(s.heading)}</h3>
        <p class="guide-section-text">${esc(s.content)}</p>
        <button class="btn-secondary btn-explain" onclick="explainSimpler(${i}, this)">✨ Explain simpler</button>
      </div>`;
  });

  if ((GUIDE.glossary || []).length) {
    html += '<h3 class="guide-block-title">🗂️ Key terms</h3><div class="glossary-grid">';
    GUIDE.glossary.forEach(g => {
      html += `<div class="glossary-card">
                 <div class="glossary-term">${esc(g.term)}</div>
                 <div class="glossary-def">${esc(g.definition)}</div>
               </div>`;
    });
    html += '</div>';
  }

  if ((GUIDE.takeaways || []).length) {
    html += '<h3 class="guide-block-title">⭐ Key takeaways</h3><ul class="guide-list takeaways">' +
      GUIDE.takeaways.map(t => `<li>${esc(t)}</li>`).join('') + '</ul>';
  }

  if ((GUIDE.tips || []).length) {
    html += '<h3 class="guide-block-title">💡 Study tips</h3><ul class="guide-list tips">' +
      GUIDE.tips.map(t => `<li>${esc(t)}</li>`).join('') + '</ul>';
  }

  root.innerHTML = html;
}

async function explainSimpler(i, btn) {
  const section = GUIDE.sections[i];
  if (!section || btn.disabled) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Simplifying…';
  try {
    const res = await fetch(`/deck/${DECK_ID}/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ heading: section.heading, content: section.content })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Something went wrong');
    GUIDE.sections[i].content = data.content;
    renderGuide();
    const el = document.getElementById('guide-section-' + i);
    if (el) {
      el.classList.add('just-simplified');
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = original;
    const note = document.createElement('p');
    note.className = 'explain-note';
    note.textContent = '⚠️ ' + err.message;
    btn.after(note);
    setTimeout(() => note.remove(), 5000);
  }
}

// ---------- flashcards ----------
let cardIndex = 0;

function renderCard() {
  if (FLASHCARDS.length === 0) {
    document.getElementById('card-question').textContent = 'No flashcards were generated.';
    return;
  }
  document.getElementById('card-question').textContent = FLASHCARDS[cardIndex].question;
  document.getElementById('card-answer').textContent = FLASHCARDS[cardIndex].answer;
  document.getElementById('card-counter').textContent = (cardIndex + 1) + ' / ' + FLASHCARDS.length;
  document.getElementById('flashcard').classList.remove('flipped');
}

function flipCard() { document.getElementById('flashcard').classList.toggle('flipped'); }
function nextCard() { if (cardIndex < FLASHCARDS.length - 1) { cardIndex++; renderCard(); } }
function prevCard() { if (cardIndex > 0) { cardIndex--; renderCard(); } }

// ---------- quiz ----------
let quizIndex = 0;
let quizScore = 0;

function startQuiz() {
  if (QUIZ.length === 0) {
    document.getElementById('quiz-question').textContent = 'No quiz questions were generated.';
    return;
  }
  quizIndex = 0;
  quizScore = 0;
  document.getElementById('quiz-final').style.display = 'none';
  document.getElementById('quiz-result').textContent = '';
  renderQuizQuestion();
}

function renderQuizQuestion() {
  if (quizIndex >= QUIZ.length) return endQuiz();
  const q = QUIZ[quizIndex];
  document.getElementById('quiz-progress').textContent = (quizIndex + 1) + ' / ' + QUIZ.length;
  document.getElementById('quiz-question').textContent = q.question;
  const box = document.getElementById('quiz-options');
  box.innerHTML = '';
  q.options.forEach((opt, i) => {
    const btn = document.createElement('button');
    btn.className = 'quiz-option';
    btn.textContent = opt;
    btn.onclick = () => answerQuiz(i, btn);
    box.appendChild(btn);
  });
}

function answerQuiz(chosen, btn) {
  const q = QUIZ[quizIndex];
  const buttons = document.querySelectorAll('.quiz-option');
  buttons.forEach(b => b.disabled = true);
  buttons[q.correct_index].classList.add('correct');
  if (chosen !== q.correct_index) btn.classList.add('wrong');
  if (chosen === q.correct_index) quizScore++;
  const res = document.getElementById('quiz-result');
  res.textContent = chosen === q.correct_index
    ? '✅ Correct!'
    : '❌ Wrong — the answer is: ' + q.options[q.correct_index];
  setTimeout(() => {
    res.textContent = '';
    quizIndex++;
    renderQuizQuestion();
  }, 1500);
}

function endQuiz() {
  document.getElementById('quiz-question').textContent = '';
  document.getElementById('quiz-options').innerHTML = '';
  document.getElementById('quiz-progress').textContent = '';
  document.getElementById('quiz-final').style.display = 'block';
  document.getElementById('quiz-score').textContent =
    `You scored ${quizScore} out of ${QUIZ.length}!`;
}

// ---------- hangman ----------
const HANGMAN_PARTS = ['hm-head', 'hm-body', 'hm-arm-l', 'hm-arm-r', 'hm-leg-l', 'hm-leg-r'];
const MAX_WRONG = 6;
let hmAnswer = '';
let hmGuessed = new Set();
let hmWrong = 0;
let hmOver = false;
let hmRemaining = [];

function newHangman() {
  if (HANGMAN.length === 0) return;
  if (hmRemaining.length === 0) hmRemaining = [...HANGMAN.keys()];
  const pick = hmRemaining.splice(Math.floor(Math.random() * hmRemaining.length), 1)[0];
  hmAnswer = HANGMAN[pick].answer.toUpperCase();
  hmGuessed = new Set();
  hmWrong = 0;
  hmOver = false;
  document.getElementById('hm-clue').textContent = '💡 ' + HANGMAN[pick].clue;
  document.getElementById('hm-message').textContent = '';
  HANGMAN_PARTS.forEach(id => document.getElementById(id).style.display = 'none');
  buildKeyboard();
  renderHangmanWord();
}

function buildKeyboard() {
  const kb = document.getElementById('hm-keyboard');
  kb.innerHTML = '';
  for (let i = 65; i <= 90; i++) {
    const letter = String.fromCharCode(i);
    const btn = document.createElement('button');
    btn.className = 'hm-key';
    btn.textContent = letter;
    btn.onclick = () => guessLetter(letter, btn);
    kb.appendChild(btn);
  }
}

function guessLetter(letter, btn) {
  if (hmOver || hmGuessed.has(letter)) return;
  hmGuessed.add(letter);
  if (btn) btn.disabled = true;
  if (hmAnswer.includes(letter)) {
    if (btn) btn.classList.add('correct');
    renderHangmanWord();
    checkWin();
  } else {
    if (btn) btn.classList.add('wrong');
    if (hmWrong < MAX_WRONG) {
      document.getElementById(HANGMAN_PARTS[hmWrong]).style.display = 'block';
    }
    hmWrong++;
    if (hmWrong >= MAX_WRONG) {
      hmOver = true;
      document.getElementById('hm-message').textContent = '💀 Game over! The word was: ' + hmAnswer;
    }
  }
}

function renderHangmanWord() {
  document.getElementById('hm-word').innerHTML = hmAnswer.split('').map(ch =>
    hmGuessed.has(ch)
      ? `<span class="hm-letter revealed">${ch}</span>`
      : `<span class="hm-letter">_</span>`
  ).join('');
}

function checkWin() {
  if (hmAnswer.split('').every(ch => hmGuessed.has(ch))) {
    hmOver = true;
    document.getElementById('hm-message').textContent = '🎉 You got it!';
  }
}

// physical keyboard support
document.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  const key = e.key.toUpperCase();
  if (!/^[A-Z]$/.test(key)) return;
  const btn = [...document.querySelectorAll('.hm-key')].find(b => b.textContent === key);
  if (btn && !btn.disabled) guessLetter(key, btn);
});

// ---------- init ----------
renderGuide();
renderCard();
startQuiz();
newHangman();