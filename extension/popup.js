// popup.js
let pageInfo = { url: '', title: '', text: '' };

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  document.getElementById('pageUrl').textContent = tab.url;
  pageInfo.url = tab.url;
  pageInfo.title = tab.title;

  // Request page text from content script
  chrome.tabs.sendMessage(tab.id, { action: 'getPageText' }, (response) => {
    if (response && response.text) {
      pageInfo.text = response.text;
    }
  });
});

// Load settings
chrome.storage.sync.get(['apiUrl', 'customQuestion'], (data) => {
  if (data.apiUrl) document.getElementById('apiUrl').value = data.apiUrl;
  if (data.customQuestion) document.getElementById('customQuestion').value = data.customQuestion;
});

function saveSettings() {
  chrome.storage.sync.set({
    apiUrl: document.getElementById('apiUrl').value,
    customQuestion: document.getElementById('customQuestion').value,
  });
}

function toggleSettings() {
  const panel = document.getElementById('settingsPanel');
  panel.classList.toggle('hidden');
}

async function briefPage() {
  const btn = document.getElementById('briefBtn');
  const status = document.getElementById('status');
  const result = document.getElementById('result');
  const apiUrl = document.getElementById('apiUrl').value.replace(/\/$/, '');
  const customQ = document.getElementById('customQuestion').value.trim();

  if (!pageInfo.text) {
    status.textContent = 'Could not extract page text. Try refreshing.';
    return;
  }

  btn.disabled = true;
  status.innerHTML = '<span class="spinner"></span> Analyzing page...';
  result.classList.add('hidden');

  try {
    const resp = await fetch(`${apiUrl}/brief-page`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: pageInfo.url,
        title: pageInfo.title,
        text: pageInfo.text,
        query: customQ || `Summarize and analyze: ${pageInfo.title}`,
      }),
    });

    const data = await resp.json();
    if (data.error) {
      status.textContent = 'Error: ' + data.error;
    } else {
      status.textContent = 'Done!';
      result.innerHTML = formatMarkdown(data.answer);
      result.classList.remove('hidden');
    }
  } catch (err) {
    status.textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
  }
}

function formatMarkdown(text) {
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/^# (.+)$/gm, '<h3>$1</h3>');
  text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
  text = text.replace(/(<li>.+<\/li>\n?)+/g, '<ul>$&</ul>');
  text = text.replace(/<\/ul>\s*<ul>/g, '');
  text = text.split('\n\n').map(p => {
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<li')) return p;
    return `<p>${p}</p>`;
  }).join('\n');
  return text;
}
