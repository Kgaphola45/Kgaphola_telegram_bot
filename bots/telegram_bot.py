# bots/telegram_bot.py
import os
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
from dotenv import load_dotenv
from datetime import datetime
import time

# Load bot token
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Paths
REMINDERS_FILE = "../reminders/reminders.txt"
LOG_FILE = "../logs/telegram_logs.txt"

# Function to load reminders
def load_reminders():
    reminders = []
    with open(REMINDERS_FILE, "r") as file:
        for line in file:
            if line.strip() == "":
                continue
            parts = line.strip().split("|")
            if len(parts) == 3:
                reminders.append({
                    "message": parts[0].strip(),
                    "time": parts[1].strip(),
                    "user_id": int(parts[2].strip())
                })
    return reminders


# Send reminder to a user
def send_reminder(bot, message, user_id):
    bot.send_message(chat_id=user_id, text=message)
    # Log message
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | Telegram | {user_id} | {message}\n")
    print(f"✅ Sent to {user_id}: {message}")

# /start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hello! I am your Reminder Bot.\n"
        "I will send you scheduled reminders automatically.\n"
        "Use /help to see commands."
    )
    

# /help command
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show commands"
    )

# Main function to send reminders
def run_reminders(updater):
    bot = updater.bot
    reminders = load_reminders()
    print("⏰ Reminder scheduler started...")
    while True:
        now = datetime.now().strftime("%H:%M")
        for reminder in reminders:
            if reminder["time"] == now:
                send_reminder(bot, reminder["message"], reminder["user_id"])
        time.sleep(60)