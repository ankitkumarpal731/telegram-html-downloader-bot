
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import re, requests, subprocess, zipfile

BOT_TOKEN = os.getenv("7919866373:AAEPWDSj85GJHH7bAVUKhVTLYU2JIaEc_80")  # Get from environment (for Railway)

def extract_links(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    pdf_links = [a['href'] for a in soup.find_all('a') if a.get('href', '').endswith('.pdf')]
    video_links = re.findall(r'https://[^\s"\']+\.m3u8', html_content)
    return pdf_links, video_links

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if file.file_name.endswith('.html'):
        telegram_file = await file.get_file()
        html_content = (await telegram_file.download_as_bytearray()).decode("utf-8")

        pdf_links, video_links = extract_links(html_content)

        # 📄 PDF DOWNLOAD
        os.makedirs("pdfs", exist_ok=True)
        for i, link in enumerate(pdf_links, 1):
            try:
                r = requests.get(link)
                with open(f"pdfs/file_{i}.pdf", "wb") as f:
                    f.write(r.content)
            except:
                continue

        zip_path = "pdfs.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in os.listdir("pdfs"):
                zipf.write(os.path.join("pdfs", file), file)

        await update.message.reply_document(open(zip_path, "rb"))

        # 🎥 VIDEO DOWNLOAD (first 2 for safety)
        for i, link in enumerate(video_links[:2], 1):
            out_file = f"video_{i}.mp4"
            try:
                subprocess.run(["yt-dlp", "-o", out_file, link])
                if os.path.exists(out_file):
                    await update.message.reply_video(open(out_file, "rb"))
            except:
                continue

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.run_polling()
