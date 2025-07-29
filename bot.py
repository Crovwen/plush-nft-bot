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
ADD_TO_ALL_AMOUNT = 0.1
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
        buttons = [
            [InlineKeyboardButton("TON Withdrawal📤", callback_data="ton_withdrawal")],
            [InlineKeyboardButton("NFT Withdrawal📤", callback_data="nft_withdrawal")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await query.edit_message_text("📤 Choose a withdrawal method:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == "betting":
        explanation = (
            "🎲 Choose a bet type:\n\n"
            "🔹 *Odd (1,3,5)* or *Even (2,4,6)*: 1.5x reward\n"
            "🔹 *Pairs (1-1 to 6-6)*: 3x reward\n"
        )
        buttons = [
            [InlineKeyboardButton("Even (2,4,6)", callback_data="even"), InlineKeyboardButton("Odd (1,3,5)", callback_data="odd")],
            [InlineKeyboardButton("1-1", callback_data="pair_1"), InlineKeyboardButton("2-2", callback_data="pair_2"), InlineKeyboardButton("3-3", callback_data="pair_3")],
            [InlineKeyboardButton("4-4", callback_data="pair_4"), InlineKeyboardButton("5-5", callback_data="pair_5"), InlineKeyboardButton("6-6", callback_data="pair_6")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await query.edit_message_text(explanation, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data in ["even", "odd"] or query.data.startswith("pair_"):
        context.user_data["bet_type"] = query.data
        await context.bot.send_message(chat_id=user_id, text="💸 Enter your bet amount:")

    elif query.data == "back":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = users.get(user_id)

    if "bet_type" in context.user_data:
        try:
            amount = float(update.message.text)
            if amount > user["balance"]:
                await update.message.reply_text("❌ Not enough balance.")
                return
            bet_type = context.user_data.pop("bet_type")
            dice = random.randint(1, 6)
            win = False
            multiplier = 1.5 if bet_type in ["even", "odd"] else 3

            if bet_type == "even" and dice % 2 == 0:
                win = True
            elif bet_type == "odd" and dice % 2 == 1:
                win = True
            elif bet_type.startswith("pair_"):
                pair_num = int(bet_type.split("_")[1])
                if dice == pair_num:
                    win = True

            if win:
                reward = amount * multiplier
                user["balance"] += reward
                result = f"🎲 Dice rolled: {dice}\n🎉 You won {reward:.2f} TON!"
            else:
                user["balance"] -= amount
                result = f"🎲 Dice rolled: {dice}\n❌ You lost {amount:.2f} TON."

            save_users(users)
            await update.message.reply_text(result)
        except:
            await update.message.reply_text("❗ Please enter a valid number.")

# Admin commands
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    message = " ".join(context.args)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
        except:
            pass
    await update.message.reply_text("✅ Broadcast sent.")

async def add_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        amount = float(context.args[0])
        for user in users.values():
            user["balance"] += amount
        save_users(users)
        await update.message.reply_text(f"✅ Added {amount} TON to all users.")
    except:
        await update.message.reply_text("❗ Usage: /addtoall [amount]")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"👥 Total users: {len(users)}")

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = context.args[0]
        user = users.get(uid)
        if user:
            await update.message.reply_text(f"💰 User {uid} balance: {user['balance']:.2f} TON")
        else:
            await update.message.reply_text("❗ User not found.")
    except:
        await update.message.reply_text("❗ Usage: /balance [user_id]")

async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = context.args[0]
        amount = float(context.args[1])
        user = users.get(uid)
        if user:
            user["balance"] = amount
            save_users(users)
            await update.message.reply_text(f"✅ Set balance of {uid} to {amount} TON")
        else:
            await update.message.reply_text("❗ User not found.")
    except:
        await update.message.reply_text("❗ Usage: /setbalance [user_id] [amount]")

# Flask for Render
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is Alive ✅"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addtoall", add_to_all))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("balance", get_balance))
    application.add_handler(CommandHandler("setbalance", set_balance))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()

    async def main():
        await run_bot()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(main())
    loop.run_forever()
