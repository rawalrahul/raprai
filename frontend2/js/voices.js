/**
 * Voices for group chats: each AI in a group speaks in its own voice, using the
 * browser's built-in speech (free, works offline on most systems). Turn on
 * "Read group replies aloud" in Settings; pick each AI's voice there too.
 */

const _voiceKey = ai => 'rapr_voice_' + (ai || 'default');

function _availableVoices() {
  return (window.speechSynthesis && speechSynthesis.getVoices()) || [];
}

/** The voice for an AI: the one you picked, else a stable pick from the voices installed. */
function voiceFor(ai) {
  const voices = _availableVoices();
  if (!voices.length) return null;
  let name = '';
  try { name = localStorage.getItem(_voiceKey(ai)) || ''; } catch (_) {}
  const chosen = voices.find(v => v.name === name);
  if (chosen) return chosen;
  let h = 0;
  for (const ch of String(ai || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return voices[h % voices.length];
}

function speakAs(ai, text) {
  if (!window.speechSynthesis || !text) return;
  const u = new SpeechSynthesisUtterance(text.slice(0, 1500));
  const v = voiceFor(ai);
  if (v) { u.voice = v; u.lang = v.lang; }
  u.rate = 1.02;
  speechSynthesis.speak(u);
}

function setVoiceFor(ai, name) {
  try { localStorage.setItem(_voiceKey(ai), name || ''); } catch (_) {}
}

function toggleGroupSpeak(on) {
  window._groupSpeak = !!on;
  try { localStorage.setItem('rapr_group_speak', on ? '1' : '0'); } catch (_) {}
}
try { window._groupSpeak = localStorage.getItem('rapr_group_speak') === '1'; } catch (_) {}

/** Settings panel: one voice choice per AI that has a session. Built from the live list. */
function renderVoiceSettings() {
  const box = document.getElementById('voice-settings');
  if (!box) return;
  box.textContent = '';
  const voices = _availableVoices();
  if (!voices.length) {
    box.textContent = 'No voices found on this device yet. Install a system voice, or try again after the page loads.';
    return;
  }
  const ais = [...new Set(((typeof State !== 'undefined' && State.sessions) || []).map(s => s.ai).filter(Boolean))];
  if (!ais.length) { box.textContent = 'Start an AI session to pick its voice.'; return; }
  ais.forEach(ai => {
    const row = document.createElement('div');
    row.style.cssText = 'display:grid;grid-template-columns:110px 1fr;gap:6px;align-items:center;font-size:12px;padding:2px 0';
    const label = document.createElement('span'); label.textContent = ai;
    const sel = document.createElement('select'); sel.className = 'settings-input';
    const auto = document.createElement('option'); auto.value = ''; auto.textContent = 'Automatic';
    sel.appendChild(auto);
    voices.forEach(v => {
      const o = document.createElement('option'); o.value = v.name; o.textContent = v.name + ' (' + v.lang + ')';
      sel.appendChild(o);
    });
    try { sel.value = localStorage.getItem(_voiceKey(ai)) || ''; } catch (_) {}
    sel.addEventListener('change', () => setVoiceFor(ai, sel.value));
    row.append(label, sel);
    box.appendChild(row);
  });
}
