import os
import psutil
import logging
import subprocess

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler

# t.me/w3bankbot
load_dotenv()
INPUT_DIR = os.getenv("INPUT_DIR")
TG_MY_TOKEN = os.getenv("TG_TOKEN")
CALLER = os.getenv("CALLER") or 'wallet_info.exe'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_process_list():
    # Get a list of all running processes
    process_list = []
    for proc in psutil.process_iter(['pid', 'cmdline', 'name']):
        try:
            # Append process information to the list
            process_info = proc.info
            if process_info['name'] == CALLER:
                process_list.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # Handle the case where the process has terminated

    return process_list


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_db = os.path.join(INPUT_DIR, f"{update.effective_chat.id}.db")
    if not os.path.isfile(input_db):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Hi, {update.effective_chat.username}\n\nNo db! Please upload your db.\nPath: {input_db}")
        return

    result = subprocess.Popen([CALLER, input_db], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Started process: ", result)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = subprocess.Popen(["taskkill", "/F", "/IM", CALLER], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Killed process: ", result)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=get_process_list())

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Unknown message: {update.message.text}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TG_MY_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    application.run_polling()