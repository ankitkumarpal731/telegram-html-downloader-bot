# bot_downloads.py
import os
import re
import io
import zipfile
import asyncio
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# TOKEN must be provided via environment variable BOT_TOKEN (safer than hardcoding)
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Error: set your bot token in the BOT_TOKEN environment variable and restart.")

TEMP_DIR = Path("tmp_bot_files")
TEMP_DIR.mkdir(exist_ok=True)

def extract_links(html_content: str):
    """Return (pdf_links, video_links) found inside the provided HTML text."""
    soup = BeautifulSoup(html_content, "html.parser")
    pdf_links = [a["href"] for a in soup.find_all("a") if a.get("href", "").lower().endswith(".pdf")]
    # crude m3u8 regex — adjust as needed
    video_links = re.findall(r"https?://[^\s\"']+\.m3u8", html_content, flags=re.IGNORECASE)
    return pdf_links, video_links

async def download_file_to_path(url: str, out_path: Path, timeout: int = 30):
    """Download a URL in a thread to avoid blocking the event loop."""
    def _download():
        r = requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    await asyncio.to_thread(_download)

async def run_yt_dlp(url: str, output_path: str):
    """Run yt-dlp in executor (blocking) and return True on success."""
    def _run():
        # ensure yt-dlp is in PATH
        res = subprocess.run(["yt-dlp", "-o", output_path, url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    return await asyncio.to_thread(_run)

def safe_name_from_url(url: str, default_prefix="file"):
    name = Path(url.split("?")[0]).name
    # sanitize
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    if not name:
        name = f"{default_prefix}.dat"
    return name

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for incoming document files (expects .html file)."""
    doc = update.message.document
    if not doc:
        await update.message.reply_text("Please send an HTML file as a document (file extension .html).")
        return

    if not doc.file_name.lower().endswith(".html"):
        await update.message.reply_text("This handler only accepts .html files. Please send the HTML exported page.")
        return

    await update.message.chat.send_action("typing")

    # download the uploaded html file from Telegram
    tgfile = await doc.get_file()
    raw = await tgfile.download_as_bytearray()
    try:
        html_content = raw.decode("utf-8", errors="ignore")
    except Exception:
        await update.message.reply_text("Couldn't decode the HTML file.")
        return

    pdf_links, video_links = extract_links(html_content)

    # --- Download PDFs ---
    pdf_folder = TEMP_DIR / "pdfs"
    pdf_folder.mkdir(parents=True, exist_ok=True)
    downloaded_pdfs = []

    for i, link in enumerate(pdf_links, start=1):
        try:
            fname = safe_name_from_url(link, default_prefix=f"file_{i}") 
            out_path = pdf_folder / fname
            await update.message.chat.send_action("upload_document")
            await download_file_to_path(link, out_path)
            downloaded_pdfs.append(out_path)
        except Exception as e:
            # skip problematic links, continue
            print(f"Failed to download PDF {link}: {e}")

    # Create zip in-memory (so we don't need to store zip on disk)
    if downloaded_pdfs:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for p in downloaded_pdfs:
                z.write(p, arcname=p.name)
        zip_buffer.seek(0)
        await update.message.reply_document(document=zip_buffer, filename="downloaded_pdfs.zip")
    else:
        await update.message.reply_text("No PDF links found in the uploaded HTML.")

    # --- Download videos via yt-dlp (limit to first 2 to be safe) ---
    if video_links:
        for idx, vlink in enumerate(video_links[:2], start=1):
            out_file_template = str(TEMP_DIR / f"video_{idx}.%(ext)s")
            await update.message.chat.send_action("upload_video")
            success = await run_yt_dlp(vlink, out_file_template)
            if success:
                # get produced file (pick the largest matching file)
                candidates = list(TEMP_DIR.glob(f"video_{idx}.*"))
                if candidates:
                    # pick the biggest file (most likely the actual video)
                    best = max(candidates, key=lambda p: p.stat().st_size)
                    try:
                        with open(best, "rb") as vf:
                            await update.message.reply_video(video=vf)
                    except Exception as e:
                        print(f"Failed to send video {best}: {e}")
                else:
                    await update.message.reply_text(f"yt-dlp reported success but no output file found for link:\n{vlink}")
            else:
                await update.message.reply_text(f"Failed to download video: {vlink}")
    else:
        await update.message.reply_text("No m3u8 (video) links found in the HTML.")

    # Optional: cleanup downloaded files (uncomment if you want automatic cleanup)
    # for p in TEMP_DIR.glob("*"):
    #     try:
    #         if p.is_file():
    #             p.unlink()
    #         elif p.is_dir():
    #             for sub in p.iterdir():
    #                 if sub.is_file(): sub.unlink()
    #             p.rmdir()
    #     except Exception:
    #         pass

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("Bot is starting... Press Ctrl+C to stop.")
    app.run_polling()
