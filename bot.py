import os
import logging
import subprocess

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler

# t.me/w3bankbot
load_dotenv()
INPUT_DIR = os.getenv("INPUT_DIR")
TG_MY_TOKEN = os.getenv("TG_TOKEN")
CALLER = os.getenv("CALLER")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_dir = os.path.join(INPUT_DIR, f"{update.effective_chat.id}")
    if not os.path.isdir(input_dir):
        os.makedirs(input_dir)
    
    if len(os.listdir(input_dir)) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Hi, {update.effective_chat.username}\n\nNo data! Please upload your files.\nPath: {input_dir}")
        return

    result = subprocess.Popen([CALLER, input_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Started process: ", result)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = subprocess.Popen(["taskkill", "/F", "/IM", CALLER], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Killed process: ", result)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Unknown message: {update.message.text}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TG_MY_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    application.run_polling()