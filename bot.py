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

TOKEN = "YOUR_BOT_TOKEN"
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

    if not user:
        await query.edit_message_text("User not found. Please /start again.")
        return

    if query.data == "balance":
        await query.edit_message_text(f"💰 Your balance: {user['balance']:.2f} TON", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "profile":
        referrals = len(user.get("referrals", []))
        await query.edit_message_text(f"👤 Username: @{user['username']}\n🆔 ID: {user_id}\n📅 Joined: {user['start_date']}\n👥 Referrals: {referrals}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "referral":
        await query.edit_message_text(f"🔗 Your referral link:\nhttps://t.me/PlushNFTbot?start={user_id}\n💰 Get {REFERRAL_REWARD} TON for each invite!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "daily_bonus":
        now = datetime.now(pytz.utc)
        last_claim = datetime.fromisoformat(user["last_bonus"])
        if now - last_claim >= timedelta(hours=24):
            user["balance"] += DAILY_BONUS_AMOUNT
            user["last_bonus"] = now.isoformat()
            save_users(users)
            await query.edit_message_text(f"🎉 You claimed {DAILY_BONUS_AMOUNT} TON bonus!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            remaining = timedelta(hours=24) - (now - last_claim)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            await query.edit_message_text(f"⏳ Bonus available in {hours}h {minutes}m.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "deposit":
        text = f"📥 Send TON to this wallet:\n`{DEPOSIT_WALLET_ADDRESS}`\n\n(Make sure to send only TON!)"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "withdrawal":
        buttons = [[InlineKeyboardButton(f"{amt} TON", callback_data=f"ton_withdraw_{amt}")] for amt in [0.5, 1, 2, 3, 5, 10, 15, 20]]
        buttons.append([InlineKeyboardButton("🎨 NFT Withdrawal", callback_data="nft_withdrawal")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text("📤 Choose withdrawal option:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("ton_withdraw_"):
        amount = float(query.data.split("_")[-1])
        if user["balance"] >= amount:
            user["balance"] -= amount
            save_users(users)
            await query.edit_message_text(f"✅ {amount} TON will be sent to you within 24h.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            await query.edit_message_text("❌ Not enough balance.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "nft_withdrawal":
        nft_text = "🎨 Available NFTs:\n" + "\n".join([f"• {n[0]} {n[1]} — {n[2]} TON" for n in NFT_LIST]) + "\n\nChoose one:"
        buttons = [[InlineKeyboardButton(f"{n[0]} {n[1]}", callback_data=f"nft_{i}")] for i, n in enumerate(NFT_LIST)]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text(nft_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("nft_"):
        idx = int(query.data.split("_")[1])
        nft_name, nft_tag, price = NFT_LIST[idx]
        if user["balance"] >= price:
            user["balance"] -= price
            save_users(users)
            await query.edit_message_text(f"✅ NFT '{nft_name} {nft_tag}' will be sent within 24h.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            await query.edit_message_text("❌ Not enough balance for this NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "back":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

# Admin commands
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text.replace("/broadcast ", "")
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
        except: pass

async def add_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        amt = float(context.args[0])
    except:
        await update.message.reply_text("Usage: /addtoall 0.1")
        return
    for user in users.values():
        user["balance"] += amt
    save_users(users)
    await update.message.reply_text(f"✅ Added {amt} TON to all users.")

# Flask server for Render
app = Flask(__name__)
@app.route('/')
def home(): return 'Bot is running.'

def run_flask(): app.run(host="0.0.0.0", port=8080)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    app_telegram = Application.builder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("broadcast", broadcast))
    app_telegram.add_handler(CommandHandler("addtoall", add_to_all))
    app_telegram.add_handler(CallbackQueryHandler(handle_callback))
    app_telegram.run_polling()
    
