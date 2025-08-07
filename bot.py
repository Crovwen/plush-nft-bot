import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WALLET_ADDRESS = "UQCqEq6fP4BO2Gn1BLgAe8L5gk0vnzpXAr-ZJd8eqA3v0x3o"
NFTS = ["Lol Pop #24488", "Dark Smile #10572", "Skull Beast #38299"]
NFT_COST = 1.0
TON_WITHDRAW_OPTIONS = [0.5, 1, 2, 5, 10, 15, 20]
DAILY_BONUS_AMOUNT = 0.08
MIN_BET = 0.1

USERS_FILE = "users.json"
app = Flask(__name__)

# --- Helper Functions ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user_data(user):
    users = load_users()
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            "name": user.first_name,
            "balance": 0.0,
            "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "referrals": 0,
            "deposits": 0.0,
            "withdrawals": 0.0,
            "last_bonus": "1970-01-01"
        }
        save_users(users)
    return users[user_id]

def update_user_data(user_id, data):
    users = load_users()
    users[str(user_id)].update(data)
    save_users(users)

def add_balance(user_id, amount):
    users = load_users()
    users[str(user_id)]["balance"] += amount
    save_users(users)

def subtract_balance(user_id, amount):
    users = load_users()
    users[str(user_id)]["balance"] -= amount
    save_users(users)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_data(user)
    ref_id = context.args[0] if context.args else None
    if ref_id and ref_id != str(user.id):
        ref_users = load_users()
        if ref_id in ref_users:
            ref_users[ref_id]["balance"] += 0.05
            ref_users[ref_id]["referrals"] += 1
            save_users(ref_users)

    keyboard = [[
        InlineKeyboardButton("💼 Profile", callback_data="profile"),
        InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")
    ], [
        InlineKeyboardButton("💰 Deposit", callback_data="deposit"),
        InlineKeyboardButton("📤 Withdraw", callback_data="withdraw")
    ], [
        InlineKeyboardButton("🎨 NFT Withdraw", callback_data="nft"),
        InlineKeyboardButton("🎲 Betting", callback_data="betting")
    ]]

    await update.message.reply_text(
        "👋 Welcome to the Bot!", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = str(user.id)
    user_data = get_user_data(user)
    data = query.data

    if data == "profile":
        profile_text = (
            f"👤 Name: {user_data['name']}\n"
            f"🆔 ID: {user_id}\n"
            f"📅 Start: {user_data['start_date']}\n"
            f"👥 Referrals: {user_data['referrals']}\n"
            f"💸 Deposits: {user_data['deposits']:.2f} TON\n"
            f"📤 Withdrawals: {user_data['withdrawals']:.2f} TON\n"
            f"💰 Balance: {user_data['balance']:.2f} TON"
        )
        back_btn = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(back_btn))

    elif data == "bonus":
        last = datetime.strptime(user_data["last_bonus"], "%Y-%m-%d")
        if datetime.utcnow() - last >= timedelta(days=1):
            add_balance(user_id, DAILY_BONUS_AMOUNT)
            update_user_data(user_id, {"last_bonus": datetime.utcnow().strftime("%Y-%m-%d")})
            await query.edit_message_text("🎉 Bonus received: 0.08 TON")
        else:
            await query.edit_message_text("⏳ You can claim your bonus every 24 hours.")

    elif data == "deposit":
        await query.edit_message_text(
            f"💰 *Deposit TON to:*\n`{WALLET_ADDRESS}`\n\nSend any amount and your balance will be updated.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
        )

    elif data == "withdraw":
        buttons = [
            [InlineKeyboardButton(f"Withdraw {amt} TON", callback_data=f"withdraw_{amt}")]
            for amt in TON_WITHDRAW_OPTIONS if user_data["balance"] >= amt
        ] or [[InlineKeyboardButton("Insufficient balance", callback_data="back")]]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        await query.edit_message_text("📤 Choose amount to withdraw:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("withdraw_"):
        amount = float(data.split("_")[1])
        context.user_data["withdraw_amount"] = amount
        await query.edit_message_text("📥 Send your TON wallet address:")

    elif data == "nft":
        text = "🎨 *Available NFTs:*"
        buttons = []
        for nft in NFTS:
            text += f"- {nft} ({NFT_COST} TON)\n"
            buttons.append([InlineKeyboardButton(nft, callback_data=f"nft_{nft}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("nft_"):
        nft_name = data.split("nft_")[1]
        if user_data["balance"] >= NFT_COST:
            subtract_balance(user_id, NFT_COST)
            await query.edit_message_text(f"✅ {nft_name} reserved! Send your @Telegram username for confirmation.")
        else:
            await query.edit_message_text("❌ Not enough balance for this NFT.")

    elif data == "betting":
        buttons = [
            [InlineKeyboardButton("Even (2-4-6)", callback_data="even"),
             InlineKeyboardButton("Odd (1-3-5)", callback_data="odd")],
            [InlineKeyboardButton(f"{i}-{i}", callback_data=f"pair_{i}") for i in range(1, 4)],
            [InlineKeyboardButton(f"{i}-{i}", callback_data=f"pair_{i}") for i in range(4, 7)],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        await query.edit_message_text("🎲 Choose your bet:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data in ["even", "odd"] or data.startswith("pair_"):
        context.user_data["bet_type"] = data
        await query.edit_message_text("💸 Enter your bet amount (min 0.1 TON):")

    elif data == "back":
        await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_data = get_user_data(user)
    text = update.message.text

    if "withdraw_amount" in context.user_data:
        amount = context.user_data.pop("withdraw_amount")
        subtract_balance(user_id, amount)
        update_user_data(user_id, {"withdrawals": user_data["withdrawals"] + amount})
        await update.message.reply_text(
            f"✅ Withdraw {amount} TON requested! It will be confirmed within 24h to: {text}"
        )
        return

    if "bet_type" in context.user_data:
        try:
            bet_amount = float(text)
            if bet_amount < MIN_BET or user_data["balance"] < bet_amount:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid or insufficient balance. Try again.")
            return

        bet_type = context.user_data.pop("bet_type")
        subtract_balance(user_id, bet_amount)
        win = False

        if bet_type in ["even", "odd"]:
            roll = random.randint(1, 6)
            win = (roll % 2 == 0 and bet_type == "even") or (roll % 2 == 1 and bet_type == "odd")
            multiplier = 1.5
            result_text = f"🎲 Rolled: {roll}\n"
        elif bet_type.startswith("pair_"):
            roll1, roll2 = random.randint(1, 6), random.randint(1, 6)
            chosen = int(bet_type.split("_")[1])
            win = roll1 == roll2 == chosen
            multiplier = 3
            result_text = f"🎲 Rolled: {roll1}-{roll2}\n"

        if win:
            winnings = bet_amount * multiplier
            add_balance(user_id, winnings)
            result_text += f"🎉 You won {winnings:.2f} TON!"
        else:
            result_text += "😢 You lost. Better luck next time."

        await update.message.reply_text(result_text)

async def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.initialize()
    await application.start()
    await application.run_polling()

@app.route('/')
def index():
    return "Bot is running."

def start_bot():
    try:
        asyncio.run(run_bot())
    except RuntimeError as e:
        if "event loop is running" in str(e).lower():
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
            loop.run_forever()
        else:
            raise

if __name__ == "__main__":
    if os.getenv("RENDER"):
        import threading
        threading.Thread(target=start_bot).start()
    else:
        start_bot()
