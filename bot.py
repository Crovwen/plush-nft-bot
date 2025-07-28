import json
import random
import os
import pytz
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ---------------- CONFIG ------------------

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 5095867558
DEPOSIT_WALLET_ADDRESS = "UQAG_02lalmnQiisR-fbZLLSr861phEtyIrnWEUc7OwfxX5Y"
DAILY_BONUS_AMOUNT = 0.06
REFERRAL_REWARD = 0.05
ADD_TO_ALL_AMOUNT = 0.1

# ---------------- USERS DATA ------------------

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

# ---------------- NFT LIST ------------------

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

# ---------------- UI ------------------

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")],
        [InlineKeyboardButton("📤 Withdrawal", callback_data="withdrawal")],
        [InlineKeyboardButton("📥 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("🎲 Betting", callback_data="betting")]
    ])

# ---------------- COMMANDS ------------------

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

# ---------------- CALLBACK ------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if user_id not in users:
        await query.edit_message_text("Use /start to register.")
        return

    data = query.data
    user = users[user_id]

    if data == "balance":
        await query.edit_message_text(f"💰 Balance: {user['balance']:.2f} TON", reply_markup=get_main_menu())

    elif data == "profile":
        await query.edit_message_text(f"👤 Username: @{query.from_user.username}\n🔗 Referrals: {len(user['referrals'])}", reply_markup=get_main_menu())

    elif data == "referral":
        await query.edit_message_text(
            f"🔗 Invite link:\nhttps://t.me/{context.bot.username}?start={user_id}\n💰 Get {REFERRAL_REWARD} TON per invite!",
            reply_markup=get_main_menu()
        )

    elif data == "deposit":
        await query.edit_message_text(
            f"📥 Send TON to this wallet:\n<code>{DEPOSIT_WALLET_ADDRESS}</code>", parse_mode="HTML",
            reply_markup=get_main_menu()
        )

    elif data == "daily_bonus":
        now = datetime.now(pytz.utc)
        last = datetime.fromisoformat(user["last_bonus"])
        if now - last >= timedelta(hours=24):
            user["balance"] += DAILY_BONUS_AMOUNT
            user["last_bonus"] = now.isoformat()
            save_users(users)
            await query.edit_message_text(f"🎁 You got {DAILY_BONUS_AMOUNT} TON bonus!", reply_markup=get_main_menu())
        else:
            remaining = timedelta(hours=24) - (now - last)
            await query.edit_message_text(f"⏳ Try again in {str(remaining).split('.')[0]}", reply_markup=get_main_menu())

    elif data == "withdrawal":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("TON Withdrawal 📤", callback_data="withdraw_ton")],
            [InlineKeyboardButton("NFT Withdrawal 📤", callback_data="withdraw_nft")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
        ])
        await query.edit_message_text("Choose withdrawal type:", reply_markup=markup)

    elif data == "withdraw_ton":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.5 TON", callback_data="ton_0.5"), InlineKeyboardButton("1 TON", callback_data="ton_1")],
            [InlineKeyboardButton("2 TON", callback_data="ton_2"), InlineKeyboardButton("5 TON", callback_data="ton_5")],
            [InlineKeyboardButton("10 TON", callback_data="ton_10"), InlineKeyboardButton("20 TON", callback_data="ton_20")],
            [InlineKeyboardButton("⬅️ Back", callback_data="withdrawal")]
        ])
        await query.edit_message_text("💸 Choose TON amount:", reply_markup=markup)

    elif data.startswith("ton_"):
        amount = float(data.split("_")[1])
        if user["balance"] < amount:
            await query.edit_message_text("❌ Insufficient balance.", reply_markup=get_main_menu())
        else:
            user["pending_withdrawal"] = amount
            save_users(users)
            await query.edit_message_text(f"💳 Send your TON wallet address to withdraw {amount} TON.")

    elif data == "withdraw_nft":
        nft_text = "📦 NFT Options:\n" + "\n".join([f"{name} {code} = {price} TON\n💎" for name, code, price in NFT_LIST])
        buttons = [[InlineKeyboardButton(name, callback_data=f"nft_{name}")] for name, _, _ in NFT_LIST]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="withdrawal")])
        await query.edit_message_text(nft_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("nft_"):
        nft_name = data[4:]
        await query.edit_message_text(f"Send your Telegram username to receive {nft_name}. Processed in 24h.", reply_markup=get_main_menu())

    elif data == "betting":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Even (2-4-6)", callback_data="bet_even"), InlineKeyboardButton("Odd (1-3-5)", callback_data="bet_odd")],
            [InlineKeyboardButton("Double (1-1 to 6-6)", callback_data="bet_double")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
        ])
        await query.edit_message_text("🎲 Choose your bet:", reply_markup=markup)

    elif data == "bet_even":
        result = random.choice([2, 4, 6])
        await query.edit_message_text(f"🎲 Dice rolled: {result}\n✅ You win x1.5!", reply_markup=get_main_menu())

    elif data == "bet_odd":
        result = random.choice([1, 3, 5])
        await query.edit_message_text(f"🎲 Dice rolled: {result}\n✅ You win x1.5!", reply_markup=get_main_menu())

    elif data == "bet_double":
        d1 = random.randint(1, 6)
        d2 = d1
        await query.edit_message_text(f"🎲 Dice: {d1} - {d2}\n✅ You win x3!", reply_markup=get_main_menu())

    elif data == "menu":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

# ---------------- ADMIN ------------------

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
    if update.effective_user.id != 5095867558:
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
# ---------------- MAIN ------------------

app_flask = Flask(__name__)

@app_flask.route("/ping")
def ping():
    return "Bot is alive"

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtoall", add_to_all))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
    app.add_handler(CommandHandler("addcustom", add_custom))

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(main))
    app_flask.run(host="0.0.0.0", port=10000)
