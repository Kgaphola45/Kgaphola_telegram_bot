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
        ["❌ Delete Reminder", "❓ Help"]
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
            if len(parts) >= 3:
                reminders.append({
                    "message": parts[0].strip(),
                    "time": parts[1].strip(),
                    "user_id": int(parts[2].strip()),
                    "frequency": parts[3].strip() if len(parts) > 3 else "Daily"
                })
    return reminders

def delete_reminder_from_file(reminder):
    try:
        with open(REMINDERS_FILE, "r") as f:
            lines = f.readlines()
        with open(REMINDERS_FILE, "w") as f:
            deleted = False
            for line in lines:
                if line.strip() == "":
                    continue
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    r_msg, r_time = parts[0].strip(), parts[1].strip()
                    r_id = int(parts[2].strip())
                    r_freq = parts[3].strip() if len(parts) > 3 else "Daily"
                    if not deleted and r_msg == reminder['message'] and r_time == reminder['time'] and r_id == reminder['user_id'] and r_freq == reminder.get('frequency', 'Daily'):
                        deleted = True
                        continue
                f.write(line)
        return True
    except Exception as e:
        print(f"Error deleting: {e}")
        return False

async def send_reminder(application: Application, message, user_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Mark as Done", callback_data=f"done_|{message}"),
            InlineKeyboardButton("💤 Snooze (10m)", callback_data=f"snooze_|{message}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await application.bot.send_message(chat_id=user_id, text=f"🔔 *Reminder:*\n\n{message}", reply_markup=reply_markup)
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
                if reminder.get("frequency", "Daily") == "Once":
                    delete_reminder_from_file(reminder)
        await asyncio.sleep(60)  # Check every minute

# --- Main Function ---

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    from telegram.ext import MessageHandler, filters, CallbackQueryHandler
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    import re
    
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text == "➕ Add Reminder":
            await update.message.reply_text("To add a reminder, reply with the format: `Reminder | HH:MM | Frequency`\nFrequency can be `Once` or `Daily` (default is Daily).\n(e.g., `Drink water | 14:30 | Daily` or `Meeting | 15:00 | Once`)", parse_mode="Markdown")
        elif text == "📋 My Reminders":
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == update.message.chat_id]
            if not user_reminders:
                await update.message.reply_text("You have no reminders set.")
            else:
                msg = "Your Reminders:\n" + "\n".join([f"• {r['time']} - {r['message']} ({r.get('frequency', 'Daily')})" for r in user_reminders])
                await update.message.reply_text(msg)
        elif text == "❌ Delete Reminder":
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == update.message.chat_id]
            if not user_reminders:
                await update.message.reply_text("You have no reminders set to delete.")
            else:
                keyboard = []
                for i, r in enumerate(user_reminders):
                    keyboard.append([InlineKeyboardButton(f"🗑️ {r['time']} - {r['message']} ({r.get('frequency', 'Daily')})", callback_data=f"del_{i}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Tap a reminder below to delete it:", reply_markup=reply_markup)
        elif text == "❓ Help":
            await help_command(update, context)
        elif "|" in text and re.match(r".*\|\s*\d{2}:\d{2}.*", text):
            # Parse and save new reminder
            parts = [p.strip() for p in text.split("|")]
            msg, time_str = parts[0], parts[1]
            freq = parts[2] if len(parts) > 2 else "Daily"
            if freq not in ["Once", "Daily"]:
                freq = "Daily"
            
            try:
                datetime.strptime(time_str, "%H:%M") # Validate time format
                with open(REMINDERS_FILE, "a") as f:
                    f.write(f"\n{msg} | {time_str} | {update.message.chat_id} | {freq}")
                await update.message.reply_text(f"✅ Reminder set for {time_str}: {msg} ({freq})")
            except ValueError:
                await update.message.reply_text("❌ Invalid time format. Please use HH:MM (24-hour).")
        else:
            await update.message.reply_text("I didn't understand that. Please choose an option or send a valid reminder format.")
            
    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("del_"):
            idx = int(query.data.split("_")[1])
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == query.message.chat_id]
            
            if idx < len(user_reminders):
                reminder_to_delete = user_reminders[idx]
                if delete_reminder_from_file(reminder_to_delete):
                    await query.edit_message_text(text=f"🗑️ Deleted reminder: {reminder_to_delete['message']} at {reminder_to_delete['time']}")
                else:
                    await query.edit_message_text(text="❌ Failed to delete reminder.")
        elif query.data.startswith("done_|"):
            # Mark the sent reminder as done by editing the message to remove buttons
            msg = query.data.split("|")[1]
            await query.edit_message_text(text=f"✅ *Done:*\n\n~{msg}~", parse_mode="MarkdownV2")
        elif query.data.startswith("snooze_|"):
            msg = query.data.split("|")[1]
            # Calculate time + 10 mins
            from datetime import timedelta
            now = datetime.now()
            snooze_time = (now + timedelta(minutes=10)).strftime("%H:%M")
            
            # Save as temporary "Once" reminder
            with open(REMINDERS_FILE, "a") as f:
                f.write(f"\n{msg} (Snoozed) | {snooze_time} | {query.message.chat_id} | Once")
            
            await query.edit_message_text(text=f"💤 Snoozed for 10 minutes.\nI will remind you again at {snooze_time}.")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

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