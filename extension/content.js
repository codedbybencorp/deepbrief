// content.js — extract readable text from the current page

function extractReadableText() {
  // Clone the body
  const clone = document.body.cloneNode(true);

  // Remove non-content elements
  const selectors = [
    'script', 'style', 'nav', 'footer', 'header', 'aside',
    '[role="banner"]', '[role="navigation"]', '[role="complementary"]',
    '.sidebar', '.comments', '.advertisement', '.ad', '.social-share'
  ];
  selectors.forEach(sel => {
    clone.querySelectorAll(sel).forEach(el => el.remove());
  });

  // Try to find main content area
  let content = clone.querySelector('article') || clone.querySelector('main') || clone.querySelector('[role="main"]');
  if (!content) content = clone;

  const text = content.innerText || content.textContent || '';

  // Clean up
  return text
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\t+/g, ' ')
    .trim()
    .substring(0, 8000); // Limit to 8k chars
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageText') {
    const text = extractReadableText();
    sendResponse({ text });
  }
  return true;
});
