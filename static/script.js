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

// ---------- ask your notes (chat) ----------
const CHAT_SUGGESTIONS = [
  'Explain the main idea in simple words',
  'What should I memorize for the exam?',
  'Give me an example from the notes'
];
let chatBusy = false;

function chatScroll() {
  const box = document.getElementById('chat-messages');
  box.scrollTop = box.scrollHeight;
}

function renderChatMessage(role, content) {
  const box = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble ' + role;
  bubble.textContent = content;   // plain text only — AI answers can never inject HTML
  box.appendChild(bubble);
  return bubble;
}

function renderChatSuggestions() {
  const wrap = document.getElementById('chat-suggestions');
  wrap.innerHTML = '';
  if (CHAT.length) return;   // conversation already started — no starter questions needed
  CHAT_SUGGESTIONS.forEach(text => {
    const chip = document.createElement('button');
    chip.className = 'chat-chip';
    chip.textContent = text;
    chip.onclick = () => sendChat(text);
    wrap.appendChild(chip);
  });
}

function renderChat() {
  document.getElementById('chat-messages').innerHTML = '';
  CHAT.forEach(m => renderChatMessage(m.role, m.content));
  renderChatSuggestions();
  chatScroll();
}

function showChatError(message) {
  const box = document.getElementById('chat-messages');
  const note = document.createElement('p');
  note.className = 'chat-error';
  note.textContent = '⚠️ ' + message;
  box.appendChild(note);
  chatScroll();
  setTimeout(() => note.remove(), 6000);
}

async function sendChat(prefilled) {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const question = (prefilled || input.value).trim();
  if (chatBusy) return;
  if (!question) {
    input.classList.add('shake');
    setTimeout(() => input.classList.remove('shake'), 400);
    input.focus();
    return;
  }
  chatBusy = true;
  sendBtn.disabled = true;
  if (!prefilled) { input.value = ''; input.style.height = 'auto'; }
  document.getElementById('chat-suggestions').innerHTML = '';
  const userBubble = renderChatMessage('user', question);
  const thinking = renderChatMessage('assistant thinking', '…');
  chatScroll();
  try {
    const res = await fetch('/deck/' + DECK_ID + '/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Something went wrong');
    CHAT.push({ role: 'user', content: question });
    CHAT.push({ role: 'assistant', content: data.answer });
    thinking.classList.remove('thinking');
    thinking.textContent = data.answer;
  } catch (err) {
    // nothing was saved on the server — take the question back
    thinking.remove();
    userBubble.remove();
    showChatError(err.message);
    if (!prefilled) input.value = question;
  } finally {
    chatBusy = false;
    sendBtn.disabled = false;
    input.focus();
    chatScroll();
  }
}

async function clearChat() {
  if (chatBusy || !CHAT.length) return;
  if (!confirm('Clear the whole conversation for this study set?')) return;
  try {
    const res = await fetch('/deck/' + DECK_ID + '/clear-chat', { method: 'POST' });
    if (!res.ok) throw new Error('Could not clear the chat.');
  } catch (err) {
    showChatError(err.message);
    return;
  }
  CHAT.length = 0;
  renderChat();
  document.getElementById('chat-input').focus();
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

// ---------- quiz 2.0 ----------
let quizOrder = [];   // question indices, shuffled freshly every round
let quizPos = 0;
let quizScore = 0;
let quizAnswers = []; // what the student answered, for the end review

const QUIZ_TYPE_HINTS = {
  mc: 'Choose the best answer',
  tf: 'True or false?',
  fill: 'Type the missing word',
  match: 'Match each pair — you need all of them for the point'
};

function shuffleList(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function startQuiz() {
  if (QUIZ.length === 0) {
    document.getElementById('quiz-question').textContent = 'No quiz questions were generated.';
    document.getElementById('quiz-stage').style.display = 'none';
    return;
  }
  quizOrder = shuffleList([...QUIZ.keys()]);
  quizPos = 0;
  quizScore = 0;
  quizAnswers = [];
  document.getElementById('quiz-final').style.display = 'none';
  document.getElementById('quiz-stage').style.display = 'block';
  renderQuizQuestion();
}

function renderQuizQuestion() {
  if (quizPos >= quizOrder.length) return endQuiz();
  const q = QUIZ[quizOrder[quizPos]];
  document.getElementById('quiz-progress').textContent = (quizPos + 1) + ' / ' + quizOrder.length;
  document.getElementById('quiz-bar-fill').style.width = (quizPos / quizOrder.length * 100) + '%';
  document.getElementById('quiz-question').textContent = q.question;
  document.getElementById('quiz-type-hint').textContent = QUIZ_TYPE_HINTS[q.qtype] || QUIZ_TYPE_HINTS.mc;
  document.getElementById('quiz-feedback').style.display = 'none';
  const area = document.getElementById('quiz-answer-area');
  area.innerHTML = '';

  if (q.qtype === 'tf') renderTF(q, area);
  else if (q.qtype === 'fill') renderFill(q, area);
  else if (q.qtype === 'match') renderMatch(q, area);
  else renderMC(q, area);   // 'mc' + anything unexpected falls back to multiple choice
}

function finishQuestion(q, info) {
  if (info.ok) quizScore++;
  quizAnswers.push({
    question: q.question,
    ok: info.ok,
    given: info.given,
    correct: info.correct,
    explanation: q.explanation || ''
  });
  const result = document.getElementById('quiz-result');
  result.textContent = info.ok
    ? '✅ Correct!'
    : (info.note || ('❌ Not quite — the correct answer is: ' + info.correct));
  result.className = 'quiz-result ' + (info.ok ? 'ok' : 'bad');
  const explain = document.getElementById('quiz-explain');
  if (q.explanation) {
    explain.textContent = '💡 ' + q.explanation;
    explain.style.display = 'block';
  } else {
    explain.style.display = 'none';
  }
  document.getElementById('quiz-next').textContent =
    quizPos + 1 >= quizOrder.length ? 'See your results →' : 'Next question →';
  document.getElementById('quiz-feedback').style.display = 'block';
  document.getElementById('quiz-next').focus();
}

// --- multiple choice ---
function renderMC(q, area) {
  shuffleList(q.options.map((text, i) => ({ text, i }))).forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'quiz-option';
    btn.textContent = opt.text;
    btn.dataset.orig = opt.i;
    btn.onclick = () => {
      const ok = opt.i === q.correct_index;
      area.querySelectorAll('.quiz-option').forEach(b => {
        b.disabled = true;
        if (Number(b.dataset.orig) === q.correct_index) b.classList.add('correct');
      });
      if (!ok) btn.classList.add('wrong');
      finishQuestion(q, { ok, given: q.options[opt.i], correct: q.options[q.correct_index] });
    };
    area.appendChild(btn);
  });
}

// --- true / false ---
function renderTF(q, area) {
  const wrap = document.createElement('div');
  wrap.className = 'tf-buttons';
  [['✅ True', 0, 'True'], ['❌ False', 1, 'False']].forEach(([label, idx, name]) => {
    const btn = document.createElement('button');
    btn.className = 'tf-btn';
    btn.textContent = label;
    btn.onclick = () => {
      const ok = idx === q.correct_index;
      wrap.querySelectorAll('.tf-btn').forEach(b => b.disabled = true);
      if (ok) {
        btn.classList.add('correct');
      } else {
        btn.classList.add('wrong');
        wrap.children[q.correct_index].classList.add('correct');
      }
      finishQuestion(q, { ok, given: name, correct: q.correct_index === 0 ? 'True' : 'False' });
    };
    wrap.appendChild(btn);
  });
  area.appendChild(wrap);
}

// --- fill in the blank ---
function normaliseAnswer(text) {
  return String(text).toLowerCase().trim()
    .replace(/[.,!?;:]+$/g, '')
    .replace(/\s+/g, ' ');
}

function oneTypoApart(a, b) {
  // true when two answers differ by at most one small typo
  if (Math.abs(a.length - b.length) > 1) return false;
  let i = 0, j = 0, edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++edits > 1) return false;
    if (a.length > b.length) i++;
    else if (b.length > a.length) j++;
    else { i++; j++; }
  }
  return edits + (a.length - i) + (b.length - j) <= 1;
}

function renderFill(q, area) {
  const row = document.createElement('div');
  row.className = 'fill-row';
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'fill-input';
  input.placeholder = 'Type your answer…';
  input.autocomplete = 'off';
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-primary';
  btn.textContent = 'Check answer';
  const check = () => {
    if (btn.disabled) return;
    const given = input.value.trim();
    if (!given) {
      input.classList.add('shake');
      setTimeout(() => input.classList.remove('shake'), 400);
      input.focus();
      return;
    }
    btn.disabled = true;
    input.disabled = true;
    const typed = normaliseAnswer(given);
    const accepted = (q.accepted || []).map(normaliseAnswer);
    const ok = accepted.some(a => a === typed || (a.length >= 5 && oneTypoApart(a, typed)));
    input.classList.add(ok ? 'fill-correct' : 'fill-wrong');
    finishQuestion(q, { ok, given, correct: (q.accepted || ['—'])[0] });
  };
  btn.onclick = check;
  input.addEventListener('keydown', e => { if (e.key === 'Enter') check(); });
  row.appendChild(input);
  row.appendChild(btn);
  area.appendChild(row);
  input.focus({ preventScroll: true });
}

// --- matching ---
function renderMatch(q, area) {
  const pairs = q.pairs || [];
  const rights = shuffleList(pairs.map(p => p.right));
  const grid = document.createElement('div');
  grid.className = 'match-grid';
  const selects = [];
  pairs.forEach(pair => {
    const row = document.createElement('div');
    row.className = 'match-row';
    const left = document.createElement('div');
    left.className = 'match-left';
    left.textContent = pair.left;
    const sel = document.createElement('select');
    sel.className = 'match-select';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— choose —';
    sel.appendChild(placeholder);
    rights.forEach(r => {
      const o = document.createElement('option');
      o.value = r;
      o.textContent = r;
      sel.appendChild(o);
    });
    selects.push({ sel, right: pair.right });
    row.appendChild(left);
    row.appendChild(sel);
    grid.appendChild(row);
  });
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-primary';
  btn.textContent = 'Check answers';
  btn.onclick = () => {
    if (btn.disabled) return;
    if (selects.some(s => !s.sel.value)) {
      btn.classList.add('shake');
      setTimeout(() => btn.classList.remove('shake'), 400);
      return;
    }
    btn.disabled = true;
    let rightCount = 0;
    selects.forEach(s => {
      const ok = s.sel.value === s.right;
      if (ok) rightCount++;
      s.sel.disabled = true;
      s.sel.classList.add(ok ? 'match-correct' : 'match-wrong');
    });
    const allOk = rightCount === pairs.length;
    finishQuestion(q, {
      ok: allOk,
      given: pairs.map((p, i) => p.left + ' → ' + selects[i].sel.value),
      correct: pairs.map(p => p.left + ' → ' + p.right),
      note: '❌ ' + rightCount + ' of ' + pairs.length + ' pairs matched — you need all of them for the point.'
    });
  };
  area.appendChild(grid);
  area.appendChild(btn);
}

// --- end of quiz ---
async function endQuiz() {
  document.getElementById('quiz-stage').style.display = 'none';
  document.getElementById('quiz-bar-fill').style.width = '100%';
  document.getElementById('quiz-progress').textContent = quizOrder.length + ' / ' + quizOrder.length;
  const share = quizScore / quizOrder.length;
  const mood = share >= 0.9 ? '🎉' : share >= 0.6 ? '👍' : '💪';
  document.getElementById('quiz-score').textContent =
    mood + ' You scored ' + quizScore + ' out of ' + quizOrder.length + '!';

  // answer review
  const review = document.getElementById('quiz-review');
  review.innerHTML = '';
  quizAnswers.forEach(a => {
    const item = document.createElement('div');
    item.className = 'review-item';
    let html = '<div class="review-head"><span>' + (a.ok ? '✅' : '❌') + '</span>' +
               '<span class="review-q">' + esc(a.question) + '</span></div>';
    if (Array.isArray(a.given)) {
      html += '<div class="review-pairs">';
      a.given.forEach((g, k) => {
        const good = g === a.correct[k];
        html += '<div class="review-pair ' + (good ? 'ok' : 'bad') + '">' + esc(g) +
                (good ? '' : ' <span class="review-fix">→ ' + esc(a.correct[k]) + '</span>') + '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="review-answer">Your answer: <b class="' + (a.ok ? 'ok-text' : 'bad-text') + '">' +
              esc(a.given) + '</b>' +
              (a.ok ? '' : ' · correct: <b class="ok-text">' + esc(a.correct) + '</b>') + '</div>';
    }
    if (a.explanation) {
      html += '<div class="review-explain">💡 ' + esc(a.explanation) + '</div>';
    }
    item.innerHTML = html;
    review.appendChild(item);
  });
  document.getElementById('quiz-final').style.display = 'block';

  // save the best score — if saving fails the quiz still works fine
  const note = document.getElementById('quiz-best-note');
  note.textContent = '';
  try {
    const res = await fetch('/deck/' + DECK_ID + '/quiz-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score: quizScore })
    });
    const data = await res.json();
    if (res.ok) {
      note.textContent = data.new_best
        ? '🏆 New best score!'
        : 'Your best so far: ' + data.best + ' / ' + data.total;
      showBestBadge(data.best, data.total);
    }
  } catch (err) { /* offline — no problem */ }
}

function showBestBadge(best, total) {
  const badge = document.getElementById('quiz-best');
  if (!badge) return;
  badge.textContent = '🏆 Best: ' + best + ' / ' + total;
  badge.style.display = 'inline-block';
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

// physical keyboard support (ignores typing inside quiz answer fields)
document.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  const tag = ((e.target && e.target.tagName) || '').toLowerCase();
  if (tag === 'input' || tag === 'select' || tag === 'textarea') return;
  const key = e.key.toUpperCase();
  if (!/^[A-Z]$/.test(key)) return;
  const btn = [...document.querySelectorAll('.hm-key')].find(b => b.textContent === key);
  if (btn && !btn.disabled) guessLetter(key, btn);
});

// ---------- init ----------
renderGuide();
renderChat();
renderCard();
startQuiz();
newHangman();

const quizNextBtn = document.getElementById('quiz-next');
if (quizNextBtn) {
  quizNextBtn.addEventListener('click', () => { quizPos++; renderQuizQuestion(); });
}
if (typeof QUIZ_BEST !== 'undefined' && QUIZ_BEST) {
  showBestBadge(QUIZ_BEST.best_score, QUIZ_BEST.total);
}

const chatInput = document.getElementById('chat-input');
if (chatInput) {
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });
  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();   // Enter sends, Shift+Enter makes a new line
      sendChat();
    }
  });
}
const chatSendBtn = document.getElementById('chat-send');
if (chatSendBtn) chatSendBtn.addEventListener('click', () => sendChat());
const chatClearBtn = document.getElementById('chat-clear');
if (chatClearBtn) chatClearBtn.addEventListener('click', clearChat);