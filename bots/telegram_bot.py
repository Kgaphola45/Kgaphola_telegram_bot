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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMINDERS_FILE = os.path.join(BASE_DIR, "reminders", "reminders.txt")
LOG_FILE = os.path.join(BASE_DIR, "logs", "telegram_logs.txt")
USERS_FILE = os.path.join(BASE_DIR, "reminders", "users.json")

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram import ReplyKeyboardMarkup
    
    reply_keyboard = [
        ["➕ Add Reminder", "📋 My Reminders"],
        ["❌ Delete Reminder", "🗑️ Clear All"],
        ["🌍 Set Timezone", "❓ Help"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
 await update.message.reply_text(
    "👋 Hello! I am the Kgaphola Emmanuel Reminder Bot.\n\n"
    "I help you stay organised by sending scheduled reminders directly on Telegram.\n"
    "You can use me to set reminders for tasks, meetings, important events, or daily activities.\n\n"
    "Choose an option below to get started 👇",
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

import json

def load_user_timezones():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}
        
def save_user_timezone(user_id, offset):
    data = load_user_timezones()
    data[str(user_id)] = offset
    with open(USERS_FILE, "w") as f:
        json.dump(data, f)

async def reminder_scheduler(application: Application):
    print("⏰ Reminder scheduler started...")
    from datetime import timedelta
    while True:
        utc_now = datetime.utcnow()
        reminders = load_reminders()
        timezones = load_user_timezones()
        
        for reminder in reminders:
            user_id = str(reminder["user_id"])
            offset = timezones.get(user_id, 0) # Default to UTC+0 if not set
            
            # Calculate exactly what time it is for that user
            user_now = (utc_now + timedelta(hours=offset)).strftime("%H:%M")
            
            if reminder["time"] == user_now:
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
            await update.message.reply_text("To add a reminder, simply send the time and your message:\n`HH:MM Your Message`\n*(e.g., `14:30 Drink water`)*\n\nYou can optionally add `Once` or `Daily` at the end (default is Daily).", parse_mode="Markdown")
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
        elif text == "🗑️ Clear All":
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == update.message.chat_id]
            if not user_reminders:
                await update.message.reply_text("You have no reminders to clear.")
            else:
                for r in user_reminders:
                    delete_reminder_from_file(r)
                await update.message.reply_text("✅ All your reminders have been cleared!")
        elif text == "🌍 Set Timezone":
            await update.message.reply_text("Please reply with your UTC offset format:\n`UTC [+/-] [Hours]`\n*(e.g., `UTC +2` or `UTC -5`)*", parse_mode="Markdown")
        elif text == "❓ Help":
            await help_command(update, context)
        elif text.upper().startswith("UTC "):
            try:
                offset_str = text[4:].strip().replace(" ", "")
                offset = int(offset_str)
                save_user_timezone(update.message.chat_id, offset)
                await update.message.reply_text(f"🌍 Timezone successfully set to UTC {offset:+d}!")
            except ValueError:
                await update.message.reply_text("❌ Invalid timezone format. Please reply with: `UTC +2` or `UTC -5`", parse_mode="Markdown")
        else:
            # Try to parse text as a new reminder
            match = re.match(r"^(\d{2}:\d{2})\s+(.+)$", text.strip(), re.IGNORECASE)
            if match:
                time_str = match.group(1)
                msg_part = match.group(2).strip()
                
                freq = "Daily"
                if msg_part.lower().endswith(" once"):
                    freq = "Once"
                    msg_part = msg_part[:-5].strip()
                elif msg_part.lower().endswith(" daily"):
                    freq = "Daily"
                    msg_part = msg_part[:-6].strip()
                    
                try:
                    datetime.strptime(time_str, "%H:%M") # Validate time format
                    with open(REMINDERS_FILE, "a", encoding="utf-8") as f:
                        f.write(f"\n{msg_part} | {time_str} | {update.message.chat_id} | {freq}")
                    await update.message.reply_text(f"✅ Reminder set for {time_str}: {msg_part} ({freq})")
                except ValueError:
                    await update.message.reply_text("❌ Invalid time format. Please use a valid 24-hour time like `14:30`.", parse_mode="Markdown")
                except Exception as e:
                    print(f"Error saving reminder: {e}")
                    await update.message.reply_text("❌ An error occurred while saving the reminder.", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ I didn't understand that.\n\nTo add a reminder, use the format:\n`HH:MM Your Message`\n*(e.g., `14:30 Drink water`)*", parse_mode="Markdown")
            
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