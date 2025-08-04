import os
import json
import random
import datetime
from dotenv import load_dotenv
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, filters)

load_dotenv()
BOT_TOKEN = os.getenv("7593433447:AAGXQT4mTAJkKIiDPE7uNr1whDW4dFabbok")

app = Flask(__name__)

users_file = "users.json"

if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        json.dump({}, f)

def load_users():
    with open(users_file, "r") as f:
        return json.load(f)

def save_users(users):
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "start_date": str(datetime.datetime.now()),
            "referrals": [],
            "last_bonus": "1970-01-01",
            "name": update.effective_user.first_name
        }
        save_users(users)
    keyboard = [[InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")]]
    await update.message.reply_text("Welcome to the bot!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)
    users = load_users()

    if user_id not in users:
        return

    if data == "daily_bonus":
        last_bonus = datetime.datetime.fromisoformat(users[user_id]["last_bonus"])
        now = datetime.datetime.now()
        if (now - last_bonus).total_seconds() >= 86400:
            users[user_id]["balance"] += 0.08
            users[user_id]["last_bonus"] = str(now)
            save_users(users)
            await query.edit_message_text("✅ You've received your 0.08 TON daily bonus!")
        else:
            remaining = 86400 - (now - last_bonus).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await query.edit_message_text(f"⏳ Please wait {hours}h {minutes}m for the next bonus.")

    elif data == "bet_even":
        bet_result = random.choice([1, 2, 3, 4, 5, 6])
        if bet_result % 2 == 0:
            users[user_id]["balance"] += 0.1 * 1.5
            await query.edit_message_text(f"🎲 You rolled {bet_result} — You win 0.15 TON!")
        else:
            users[user_id]["balance"] -= 0.1
            await query.edit_message_text(f"🎲 You rolled {bet_result} — You lose 0.1 TON!")
        save_users(users)

    elif data == "bet_odd":
        bet_result = random.choice([1, 2, 3, 4, 5, 6])
        if bet_result % 2 == 1:
            users[user_id]["balance"] += 0.1 * 1.5
            await query.edit_message_text(f"🎲 You rolled {bet_result} — You win 0.15 TON!")
        else:
            users[user_id]["balance"] -= 0.1
            await query.edit_message_text(f"🎲 You rolled {bet_result} — You lose 0.1 TON!")
        save_users(users)

    elif data.startswith("nft_"):
        nft_id = data.split("_")[1]
        await query.edit_message_text(f"✅ NFT #{nft_id} withdrawal requested. It will be processed within 24 hours.")

@app.route("/")
def home():
    return "Bot is running."

async def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started...")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bot())
