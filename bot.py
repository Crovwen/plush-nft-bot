import logging
import json
import os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from flask import Flask
import threading

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"
DATA_FILE = "users.json"
PENDING_WITHDRAWALS = {}
ADMIN_IDS = ["5095867558"]

# 🌐 Flask برای روشن ماندن ربات
web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Bot is alive!"
threading.Thread(target=lambda: web_app.run(host="0.0.0.0", port=8080)).start()

# 📁 بارگذاری/ذخیره اطلاعات
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

users = load_users()
logging.basicConfig(level=logging.INFO)

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Balance💰", callback_data="balance")],
        [InlineKeyboardButton("My Profile👤", callback_data="profile")],
        [InlineKeyboardButton("Referral Link👥", callback_data="referral")],
        [InlineKeyboardButton("NFT Withdrawal📤", callback_data="withdraw_menu")],
        [InlineKeyboardButton("Deposit📥", callback_data="deposit")],
        [InlineKeyboardButton("Daily bonus🎁", callback_data="bonus")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "start_date": datetime.utcnow().isoformat(),
            "name": user.full_name,
            "withdrawals": 0,
            "deposits": 0,
            "last_bonus": None
        }
        save_users()

        if context.args:
            referrer_id = context.args[0]
            if referrer_id != user_id and referrer_id in users:
                if user_id not in users[referrer_id]["referrals"]:
                    users[referrer_id]["referrals"].append(user_id)
                    users[referrer_id]["balance"] += 0.5
                    save_users()
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"🎉 Your friend ({user_id}) joined the bot via your referral link!\n💸 You earned 0.5 TON!"
                    )

    await update.message.reply_text(
        "Welcome to @PlushNFTbot\n\nPlease choose one of the options below 👇",
        reply_markup=get_main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = users.get(user_id, {})

    if query.data == "menu":
        await query.edit_message_text("Please choose one of the options below 👇", reply_markup=get_main_menu())

    elif query.data == "balance":
        await query.edit_message_text(f"💰 Your balance: {user_data.get('balance', 0):.2f} TON", reply_markup=back_button())

    elif query.data == "profile":
        profile_text = (
            f"👤 Name: {user_data.get('name', '')}\n"
            f"🆔 ID: {user_id}\n"
            f"📆 Started: {user_data.get('start_date', '')[:10]}\n"
            f"👥 Referrals: {len(user_data.get('referrals', []))}\n"
            f"📤 Withdrawals: {user_data.get('withdrawals', 0)}\n"
            f"📥 Deposits: {user_data.get('deposits', 0)}"
        )
        await query.edit_message_text(profile_text, reply_markup=back_button())

    elif query.data == "referral":
        referral_link = f"https://t.me/PlushNFTbot?start={user_id}"
        message = (
            "👥 Invite your friends and earn 0.5 TON for each one!\n"
            f"🔗 Your referral link:\n{referral_link}"
        )
        await query.edit_message_text(message, reply_markup=back_button())

    elif query.data == "bonus":
        last_bonus = user_data.get("last_bonus")
        now = datetime.utcnow()
        if last_bonus and now - datetime.fromisoformat(last_bonus) < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - datetime.fromisoformat(last_bonus))
            await query.edit_message_text(
                f"⏳ You already claimed your daily bonus.\nTry again in {str(remaining).split('.')[0]}.",
                reply_markup=back_button()
            )
        else:
            user_data["balance"] += 0.06
            user_data["last_bonus"] = now.isoformat()
            users[user_id] = user_data
            save_users()
            await query.edit_message_text("🎉 You received 0.06 TON as daily bonus!", reply_markup=back_button())

    elif query.data == "withdraw_menu":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("TON Withdrawal📤", callback_data="ton_withdraw")],
            [InlineKeyboardButton("NFT Withdrawal📤", callback_data="nft_withdraw")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
        ])
        await query.edit_message_text("Select withdrawal type:", reply_markup=markup)

    elif query.data == "ton_withdraw":
        options = [
            [InlineKeyboardButton(f"{amt} TON💎", callback_data=f"withdraw_{amt}")]
            for amt in [0.5, 1, 2, 3, 4, 5, 10, 20]
        ]
        options.append([InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")])
        await query.edit_message_text("Choose amount to withdraw:", reply_markup=InlineKeyboardMarkup(options))

    elif query.data.startswith("withdraw_"):
        amount = float(query.data.split("_")[1])
        if user_data.get("balance", 0) < amount:
            await query.edit_message_text("❌ Insufficient balance for this withdrawal.", reply_markup=back_button())
        else:
            PENDING_WITHDRAWALS[user_id] = {"type": "ton", "amount": amount}
            await query.edit_message_text("📥 Please send your TON wallet address:")

    elif query.data == "nft_withdraw":
        nft_list = (
            "📦 NFT Options:\n"
            "Desk Calendar = 1.3 TON\n💎"
            "Lol Pop = 1.3 TON\n💎"
            "B-day Candle = 1.5 TON\n💎"
            "Snake Box = 1.5 TON\n💎"
            "Candy Cane = 1.6 TON\n💎"
            "Snoop Dogg = 2 TON\n💎"
            "Ginger Cookie = 18.5 TON\n💎"
            "Jester Hat = 50 TON\n💎"
        )
        buttons = [
            [InlineKeyboardButton(name, callback_data=f"nft_{name}")]
            for name in ["Desk Calendar", "Lol Pop", "B-day Candle", "Snake Box", "Candy Cane", "Snoop Dogg", "Ginger Cookie", "Jester Hat"]
        ]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")])
        await query.edit_message_text(nft_list, reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("nft_"):
        nft_name = query.data[4:]
        PENDING_WITHDRAWALS[user_id] = {"type": "nft", "nft": nft_name}
        await query.edit_message_text("👤 Please send your Telegram username:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id in PENDING_WITHDRAWALS:
        info = PENDING_WITHDRAWALS.pop(user_id)
        if info["type"] == "ton":
            amount = info["amount"]
            users[user_id]["balance"] -= amount
            users[user_id]["withdrawals"] += 1
            save_users()
            await update.message.reply_text(
                f"✅ Withdrawal successful!\n- {amount} TON deducted from your balance.\nIt will be sent within 24 hours."
            )
        elif info["type"] == "nft":
            nft = info["nft"]
            await update.message.reply_text(
                f"✅ NFT withdrawal successful!\nYou requested {nft}.\nIt will be gifted to your Telegram account (@{text}) within 24 hours."
            )

async def addtoall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    for uid in users:
        users[uid]["balance"] += 1
        try:
            await context.bot.send_message(chat_id=int(uid), text="🎁 1 TON has been credited to your account by Admin.")
        except: pass
    save_users()
    await update.message.reply_text("✅ 1 TON sent to all users.")

async def sendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /sendall your message here")
        return

    msg = " ".join(context.args)
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
        except: pass
    await update.message.reply_text("✅ Message sent to all users.")

async def giveall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /giveall <amount>")
        return

    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("Invalid amount.")
        return

    for uid in users:
        users[uid]["balance"] += amount
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"🎁 {amount} TON has been credited to your account by Admin.")
        except: pass
    save_users()
    await update.message.reply_text(f"✅ {amount} TON added to all users.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtoall", addtoall))
    app.add_handler(CommandHandler("sendall", sendall))
    app.add_handler(CommandHandler("giveall", giveall))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main() 
