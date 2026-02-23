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