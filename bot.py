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
DAILY_BONUS_AMOUNT = 0.08
REFERRAL_REWARD = 0.05
USERS_FILE = "users.json"

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

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_users()

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")],
        [InlineKeyboardButton("📤 Withdrawal", callback_data="withdrawal")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🎲 Betting", callback_data="betting")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": "1970-01-01T00:00:00",
            "username": update.effective_user.username or "N/A",
            "start_date": datetime.now(pytz.utc).strftime('%Y-%m-%d')
        }
        if context.args:
            ref_id = context.args[0]
            if ref_id != user_id and ref_id in users:
                users[ref_id]["balance"] += REFERRAL_REWARD
                users[ref_id]["referrals"].append(user_id)
                await context.bot.send_message(chat_id=int(ref_id), text=f"🎉 @{update.effective_user.username} joined via your link!\n💰 You got {REFERRAL_REWARD} TON.")
        save_users(users)
    await update.message.reply_text("Choose an option 👇", reply_markup=get_main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = users.get(user_id)

    if query.data == "balance":
        balance = round(user['balance'], 2)
        await query.edit_message_text(f"💰 Balance: {balance:.2f} TON", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "profile":
        text = (
            f"👤 Name: {query.from_user.first_name or 'N/A'}\n"
            f"🆔 ID: {user_id}\n"
            f"📆 Started: {user.get('start_date', 'N/A')}\n"
            f"👥 Referrals: {len(user['referrals'])}\n"
            f"📤 Withdrawals: N/A\n"
            f"📥 Deposits: N/A"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "referral":
        link = f"https://t.me/PlushNFTbot?start={user_id}"
        await query.edit_message_text(f"🔗 Your referral link:\n{link}\n\n💵 You earn {REFERRAL_REWARD} TON per referral.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "deposit":
        await query.edit_message_text(f"📥 Send TON to this address:\n\n`{DEPOSIT_WALLET_ADDRESS}`\n\n🔄 Balance updates manually after confirmation.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "daily_bonus":
        now = datetime.now(pytz.utc)
        last_bonus_time = datetime.fromisoformat(user["last_bonus"])
        if now - last_bonus_time >= timedelta(hours=24):
            user["balance"] += DAILY_BONUS_AMOUNT
            user["last_bonus"] = now.isoformat()
            save_users(users)
            await query.edit_message_text(f"🎁 You received {DAILY_BONUS_AMOUNT} TON as your daily bonus!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            remaining = timedelta(hours=24) - (now - last_bonus_time)
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await query.edit_message_text(f"⏳ Come back in {hours}h {minutes}m for your next bonus.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            elif query.data == "withdrawal":
        keyboard = [
            [InlineKeyboardButton("0.5 TON", callback_data="withdraw_ton_0.5")],
            [InlineKeyboardButton("1 TON", callback_data="withdraw_ton_1")],
            [InlineKeyboardButton("2 TON", callback_data="withdraw_ton_2")],
            [InlineKeyboardButton("5 TON", callback_data="withdraw_ton_5")],
            [InlineKeyboardButton("10 TON", callback_data="withdraw_ton_10")],
            [InlineKeyboardButton("15 TON", callback_data="withdraw_ton_15")],
            [InlineKeyboardButton("20 TON", callback_data="withdraw_ton_20")],
            [InlineKeyboardButton("NFT Withdrawal 📤", callback_data="nft_withdraw")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await query.edit_message_text("📤 Choose withdrawal option:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("withdraw_ton_"):
        amount = float(query.data.split("_")[-1])
        if user["balance"] >= amount:
            user["balance"] -= amount
            save_users(users)
            await query.edit_message_text(f"✅ {amount} TON withdrawal requested.\n⏳ You'll receive it within 24h.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            await query.edit_message_text("❌ Insufficient balance.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "nft_withdraw":
        text = "🎨 Choose an NFT to withdraw:\n\n"
        for name, tag, price in NFT_LIST:
            text += f"• {name} {tag} - {price} TON\n"
        keyboard = [[InlineKeyboardButton(f"{name} {tag}", callback_data=f"nft_{tag.strip('#')}")] for name, tag, price in NFT_LIST]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("nft_"):
        tag = "#" + query.data.split("_")[1]
        nft = next((n for n in NFT_LIST if n[1] == tag), None)
        if nft:
            name, tag, price = nft
            if user["balance"] >= price:
                user["balance"] -= price
                save_users(users)
                await query.edit_message_text(f"🎉 NFT `{name} {tag}` withdrawal requested.\nPlease reply with your Telegram @username for delivery.", parse_mode=\"Markdown\", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            else:
                await query.edit_message_text("❌ Not enough balance for this NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "back":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please use the buttons below 👇", reply_markup=get_main_menu())

# Admin Commands
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message.text.split(' ', 1)[1] if len(update.message.text.split()) > 1 else ''
    count = 0
    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
            count += 1
        except:
            continue
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def add_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    amount = float(update.message.text.split(' ')[1]) if len(update.message.text.split()) > 1 else ADD_TO_ALL_AMOUNT
    for uid in users:
        users[uid]["balance"] += amount
    save_users(users)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"💸 Admin added {amount} TON to your balance!")
        except:
            continue
    await update.message.reply_text("✅ Added to all users.")

# Flask app for Render hosting
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is running."

# Run bot
async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addtoall", add_to_all))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))).start()
    asyncio.run(main())
