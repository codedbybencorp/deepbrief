# DeepBrief Chrome Extension

One-click research summaries for any webpage.

## Features

- **DeepBrief This Page** — Summarize and analyze the current page
- **Right-click selection** — Highlight text and "DeepBrief this selection"
- **Custom questions** — Ask specific questions about the page
- **Dark theme** — Matches the DeepBrief web UI

## Install (Developer Mode)

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (toggle top right)
3. Click **Load unpacked**
4. Select the `extension/` folder

## Configure

Click the ⚙️ gear icon in the popup and set your DeepBrief API URL:
- Default: `http://localhost:8090`
- Or your deployed URL: `https://deepbrief.yourdomain.com`

## Usage

1. Navigate to any webpage
2. Click the DeepBrief icon in your toolbar
3. Click **"DeepBrief This Page"**
4. Get a cited summary in seconds

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension config (Manifest V3) |
| `popup.html/js` | Extension popup UI |
| `content.js` | Extracts readable text from pages |
| `background.js` | Service worker for context menu |
| `icons/` | Extension icons |
