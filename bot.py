import json
import random
import os
import pytz
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from threading import Thread

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"
ADMIN_ID = 5095867558
DEPOSIT_WALLET_ADDRESS = "UQAG_02lalmnQiisR-fbZLLSr861phEtyIrnWEUc7OwfxX5Y"
DAILY_BONUS_AMOUNT = 0.06
REFERRAL_REWARD = 0.05
ADD_TO_ALL_AMOUNT = 0.1

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

NFT_LIST = [
    ("Desk Calendar", "#104863", 1.3),
    ("Lol Pop", "#24488", 1.3),
    ("B-day Candle", "#98618", 1.5),
    ("Snake Box", "#48486", 1.5),
    ("Candy Cane", "#19264", 1.6),
    ("Snoop Dogg", "#299426", 2),
    ("Ginger Cookie", "#89374", 18.5),
    ("Jester Hat", "#91301", 50)
]

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")],
        [InlineKeyboardButton("📤 Withdrawal", callback_data="withdrawal")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🏱 Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🎲 Betting", callback_data="betting")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": "1970-01-01T00:00:00",
            "username": update.effective_user.username or "N/A"
        }
    if context.args:
        ref_id = context.args[0]
        if ref_id != user_id and ref_id in users:
            users[ref_id]["balance"] += REFERRAL_REWARD
            users[ref_id]["referrals"].append(user_id)
            await context.bot.send_message(chat_id=int(ref_id), text=f"🎉 @{update.effective_user.username} joined via your link!\n💰 You got {REFERRAL_REWARD} TON.")
    save_users(users)
    await update.message.reply_text("Choose an option 👇", reply_markup=get_main_menu())

async def add_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    for user in users.values():
        user["balance"] += ADD_TO_ALL_AMOUNT
    save_users(users)
    await update.message.reply_text("✅ Added balance to all.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
        except:
            continue
    await update.message.reply_text("✅ Broadcast sent.")

async def add_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("❗ Usage: /addcustom amount")
        return
    try:
        amount = float(context.args[0])
        for user in users.values():
            user["balance"] += amount
        save_users(users)
        for uid in users:
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"🎁 Admin sent you {amount} TON.")
            except:
                continue
        await update.message.reply_text(f"✅ {amount} TON added to all users.")
    except ValueError:
        await update.message.reply_text("❗ Invalid amount. Example: /addcustom 0.5")

# ---- Flask Setup ----
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is Alive ✅"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def run_bot():
    application = Application.builder().token("7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addtoall", add_to_all))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addcustom", add_custom))
    application.add_handler(CallbackQueryHandler(handle_callback))
    await application.run_polling()

if __name__ == '__main__':
    Thread(target=run_flask).start()
    asyncio.run(run_bot())
