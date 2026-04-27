// background.js — service worker for DeepBrief extension

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.set({
    apiUrl: 'http://localhost:8090',
    customQuestion: '',
  });
});

// Optional: context menu for right-click DeepBrief
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'deepbrief-selection',
    title: 'DeepBrief this selection',
    contexts: ['selection'],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'deepbrief-selection') {
    chrome.storage.sync.get(['apiUrl'], async (data) => {
      const apiUrl = (data.apiUrl || 'http://localhost:8090').replace(/\/$/, '');
      try {
        const resp = await fetch(`${apiUrl}/brief-page`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: tab.url,
            title: tab.title,
            text: info.selectionText,
            query: `Explain and expand on this: "${info.selectionText.substring(0, 200)}"`,
          }),
        });
        const result = await resp.json();
        // Store result and open popup
        chrome.storage.local.set({ lastResult: result }, () => {
          chrome.action.openPopup();
        });
      } catch (err) {
        console.error('DeepBrief error:', err);
      }
    });
  }
});
