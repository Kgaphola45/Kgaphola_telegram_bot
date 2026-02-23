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
    from telegram import ReplyKeyboardMarkup
    
    reply_keyboard = [
        ["➕ Add Reminder", "📋 My Reminders"],
        ["❓ Help"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "👋 Hello! I am your Reminder Bot.\n"
        "I will send scheduled reminders automatically.\n"
        "Choose an option below:",
        reply_markup=markup
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

    from telegram.ext import MessageHandler, filters
    import re
    
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text == "➕ Add Reminder":
            await update.message.reply_text("To add a reminder, please reply with the format: `Reminder | HH:MM`\n(e.g., `Drink water | 14:30`)", parse_mode="Markdown")
        elif text == "📋 My Reminders":
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == update.message.chat_id]
            if not user_reminders:
                await update.message.reply_text("You have no reminders set.")
            else:
                msg = "Your Reminders:\n" + "\n".join([f"• {r['time']} - {r['message']}" for r in user_reminders])
                await update.message.reply_text(msg)
        elif text == "❓ Help":
            await help_command(update, context)
        elif "|" in text and re.match(r".*\|\s*\d{2}:\d{2}\s*", text):
            # Parse and save new reminder
            parts = [p.strip() for p in text.split("|")]
            msg, time_str = parts[0], parts[1]
            try:
                datetime.strptime(time_str, "%H:%M") # Validate time format
                with open(REMINDERS_FILE, "a") as f:
                    f.write(f"\n{msg} | {time_str} | {update.message.chat_id}")
                await update.message.reply_text(f"✅ Reminder set for {time_str}: {msg}")
            except ValueError:
                await update.message.reply_text("❌ Invalid time format. Please use HH:MM (24-hour).")
        else:
            await update.message.reply_text("I didn't understand that. Please choose an option or send a valid reminder format.")
            
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize and start the application
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        # Run our custom scheduler which runs indefinitely
        await reminder_scheduler(application)
    except asyncio.CancelledError:
        pass
    finally:
        # Graceful shutdown
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())