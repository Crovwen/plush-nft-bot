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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = users.get(user_id)

    if query.data == "balance":
        await query.edit_message_text(f"💰 Balance: {user['balance']} TON", reply_markup=get_main_menu())

    elif query.data == "profile":
        await query.edit_message_text(f"👤 Username: @{user['username']}\n🔗 Referrals: {len(user['referrals'])}", reply_markup=get_main_menu())

    elif query.data == "referral":
        link = f"https://t.me/PlushNFTbot?start={user_id}"
        await query.edit_message_text(f"🔗 Your referral link:\n{link}\n\n💵 You earn {REFERRAL_REWARD} TON per referral.", reply_markup=get_main_menu())

    elif query.data == "deposit":
        await query.edit_message_text(f"📥 Send TON to this address:\n\n{DEPOSIT_WALLET_ADDRESS}\n\n🔄 Balance updates manually after confirmation.", reply_markup=get_main_menu())

    elif query.data == "daily_bonus":
        now = datetime.now(pytz.utc)
        last_bonus_time = datetime.fromisoformat(user["last_bonus"])
        if now - last_bonus_time >= timedelta(hours=24):
            user["balance"] += DAILY_BONUS_AMOUNT
            user["last_bonus"] = now.isoformat()
            save_users(users)
            await query.edit_message_text(f"🎁 You received {DAILY_BONUS_AMOUNT} TON bonus!", reply_markup=get_main_menu())
        else:
            remaining = timedelta(hours=24) - (now - last_bonus_time)
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await query.edit_message_text(f"⏳ Come back in {hours}h {minutes}m for next bonus.", reply_markup=get_main_menu())

    elif query.data == "withdrawal":
        buttons = [
            [InlineKeyboardButton("TON Withdrawal📤", callback_data="withdraw_ton")],
            [InlineKeyboardButton("NFT Withdrawal📤", callback_data="withdraw_nft")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await query.edit_message_text("Select withdrawal type:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == "withdraw_ton":
        options = [0.5, 1, 2, 5, 10, 20]
        buttons = [[InlineKeyboardButton(f"{amt} TON", callback_data=f"ton_{amt}")] for amt in options]
        await query.edit_message_text("Choose amount to withdraw:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("ton_"):
        amount = float(query.data.split("_")[1])
        if user["balance"] >= amount:
            user["balance"] -= amount
            save_users(users)
            await context.bot.send_message(chat_id=user_id, text=f"💸 Enter your TON wallet address to withdraw {amount} TON:")
            context.user_data["pending_withdraw"] = amount
        else:
            await query.edit_message_text("❌ Not enough balance.", reply_markup=get_main_menu())

    elif query.data == "withdraw_nft":
        buttons = [
            [InlineKeyboardButton(f"{name} ({price} TON)", callback_data=f"nft_{idx}")]
            for idx, (name, _, price) in enumerate(NFT_LIST)
        ]
        await query.edit_message_text("Select NFT to withdraw:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("nft_"):
        idx = int(query.data.split("_")[1])
        name, _, price = NFT_LIST[idx]
        if user["balance"] >= price:
            user["balance"] -= price
            save_users(users)
            await context.bot.send_message(chat_id=user_id, text=f"🎁 Enter your Telegram username to receive **{name}**:")
            context.user_data["pending_nft"] = name
        else:
            await query.edit_message_text("❌ Not enough balance.", reply_markup=get_main_menu())

    elif query.data == "betting":
        buttons = [
            [InlineKeyboardButton("🎯 Even (2,4,6) — 1.5x", callback_data="even"),
             InlineKeyboardButton("🎲 Odd (1,3,5) — 1.5x", callback_data="odd")],
            [InlineKeyboardButton("🎯 Pairs (1-1 to 6-6) — 3x", callback_data="pair")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await query.edit_message_text("Choose your bet type:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data in ["even", "odd", "pair"]:
        context.user_data["bet_type"] = query.data
        await context.bot.send_message(chat_id=user_id, text="💸 Enter your bet amount:")

    elif query.data == "back":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = users.get(user_id)

    if "pending_withdraw" in context.user_data:
        amount = context.user_data.pop("pending_withdraw")
        await update.message.reply_text(f"✅ Withdrawal of {amount} TON requested.\n💬 You’ll receive it in 24 hours.")
        return

    if "pending_nft" in context.user_data:
        nft = context.user_data.pop("pending_nft")
        await update.message.reply_text(f"✅ Your NFT **{nft}** will be sent in 24 hours!")
        return

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
            elif bet_type == "pair":
                win = random.choice([True, False])  # 50% for simplification
            if win:
                reward = amount * multiplier
                user["balance"] += reward
                result = f"🎲 Dice: {dice}\n🎉 You won {reward} TON!"
            else:
                user["balance"] -= amount
                result = f"🎲 Dice: {dice}\n❌ You lost {amount} TON."
            save_users(users)
            await update.message.reply_text(result)
        except:
            await update.message.reply_text("❗ Please enter a valid number.")

# Admin commands
async def add_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    for user in users.values():
        user["balance"] += ADD_TO_ALL_AMOUNT
    save_users(users)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"🎁 Admin added {ADD_TO_ALL_AMOUNT} TON to your balance.")
        except: continue
    await update.message.reply_text("✅ Added balance to all.")

async def add_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return await update.message.reply_text("Usage: /addcustom 1.5")
    try:
        amount = float(context.args[0])
        for user in users.values():
            user["balance"] += amount
        save_users(users)
        for uid in users:
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"🎁 Admin added {amount} TON to your balance.")
            except: continue
        await update.message.reply_text(f"✅ Added {amount} TON to all users.")
    except:
        await update.message.reply_text("❗ Invalid amount.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
        except: continue
    await update.message.reply_text("✅ Broadcast sent.")

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
    application.add_handler(CommandHandler("addtoall", add_to_all))
    application.add_handler(CommandHandler("addcustom", add_custom))
    application.add_handler(CommandHandler("broadcast", broadcast))
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
