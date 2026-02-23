# bots/telegram_bot.py
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

REMINDERS_FILE = "../reminders/reminders.txt"
LOG_FILE = "../logs/telegram_logs.txt"

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I am your Reminder Bot.\n"
        "I will send scheduled reminders automatically.\n"
        "Use /help to see commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/help - Show commands"
    )

# --- Helper Functions ---

def load_reminders():
    reminders = []
    if not os.path.exists(REMINDERS_FILE):
        return reminders
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

async def send_reminder(application: Application, message, user_id):
    await application.bot.send_message(chat_id=user_id, text=message)
    # Log sent message
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | Telegram | {user_id} | {message}\n")
    print(f"✅ Sent to {user_id}: {message}")

async def reminder_scheduler(application: Application):
    print("⏰ Reminder scheduler started...")
    while True:
        now = datetime.now().strftime("%H:%M")
        reminders = load_reminders()
        for reminder in reminders:
            if reminder["time"] == now:
                await send_reminder(application, reminder["message"], reminder["user_id"])
        await asyncio.sleep(60)  # Check every minute

# --- Main Function ---

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Start the bot
    await application.start()
    await application.updater.start_polling()
    print("🤖 Telegram bot is running...")

    # Start reminder scheduler
    await reminder_scheduler(application)

    await application.updater.stop()
    await application.stop()
    await application.shutdown()

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())