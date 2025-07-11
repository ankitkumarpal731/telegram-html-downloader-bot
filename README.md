
# Telegram HTML Video+PDF Downloader Bot

This bot extracts `.pdf` and `.m3u8` video links from HTML files sent via Telegram, downloads them, and sends them back to the user.

## ✅ Features
- Extracts and downloads all PDFs
- Extracts and downloads the first 2 `.m3u8` video links
- Sends back ZIP of PDFs and MP4 videos
- Designed for Railway hosting (uses environment variable for bot token)

## ⚙️ Setup

1. Replace BOT_TOKEN in environment variables (or in code for local test).
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run bot locally:
   ```
   python bot.py
   ```

## 🚀 Hosting on Railway
- Push this project to GitHub
- Connect to [https://railway.app](https://railway.app)
- Add environment variable:
   - `BOT_TOKEN` = `<your Telegram bot token>`

Done! Send `.html` files to your bot on Telegram and it will reply with PDFs and videos.
