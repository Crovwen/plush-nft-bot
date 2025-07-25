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
)
from flask import Flask
import threading

# 🟢 Flask برای روشن نگه داشتن ربات
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    web_app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_web).start()

# 🔐 توکن ربات
TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"
DATA_FILE = "users.json"

# 📦 بارگذاری اطلاعات کاربران
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# 💾 ذخیره اطلاعات کاربران
def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

# 📊 مقداردهی اولیه
users = load_users()
logging.basicConfig(level=logging.INFO)

# 🔙 منوی اصلی
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Balance💰", callback_data="balance")],
        [InlineKeyboardButton("My Profile👤", callback_data="profile")],
        [InlineKeyboardButton("Referral Link👥", callback_data="referral")],
        [InlineKeyboardButton("NFT Withdrawal📤", callback_data="withdraw")],
        [InlineKeyboardButton("Deposit📥", callback_data="deposit")],
        [InlineKeyboardButton("Daily bonus🎁", callback_data="bonus")]
    ])

# 🔙 دکمه بازگشت
def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
    ])

# 🎬 شروع ربات
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
                        text=f"🎉 Your friend ({user_id}) joined the bot via your referral link!\n💰 You earned 0.5 TON!"
                    )

    await update.message.reply_text(
        "Welcome to @PlushNFTbot\n\nPlease choose one of the options below 👇",
        reply_markup=get_main_menu()
    )

# 📥 مدیریت دکمه‌ها
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
        await query.edit_message_text(
            f"💸 Invite your friends and earn 0.5 TON for each!\n\n🔗 Your referral link:\n{referral_link}",
            reply_markup=back_button()
        )

    elif query.data == "withdraw":
        if len(user_data.get("referrals", [])) < 10:
            await query.edit_message_text("❌ You must invite at least 10 users to withdraw NFT.", reply_markup=back_button())
        else:
            await query.edit_message_text("🎁 Select NFT to withdraw:\n\n" +
                                          "1️⃣ Golden Pepe — 15 TON\n" +
                                          "2️⃣ Diamond Pepe — 22 TON\n" +
                                          "3️⃣ Platinum Pepe — 35 TON\n" +
                                          "4️⃣ Cosmic Pepe — 100 TON\n\n" +
                                          "✅ Your withdrawal will be processed within 24 business hours.",
                                          reply_markup=back_button())

    elif query.data == "deposit":
        await query.edit_message_text("🚧 Deposit system coming soon...", reply_markup=back_button())

    elif query.data == "bonus":
        last_bonus = user_data.get("last_bonus")
        now = datetime.utcnow()
        if last_bonus:
            elapsed = now - datetime.fromisoformat(last_bonus)
            if elapsed < timedelta(hours=24):
                remaining = timedelta(hours=24) - elapsed
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                await query.edit_message_text(
                    f"⏳ You have already claimed your daily bonus.\nPlease try again in {hours}h {minutes}m {seconds}s.",
                    reply_markup=back_button()
                )
                return

        user_data["balance"] = user_data.get("balance", 0) + 0.5
        user_data["last_bonus"] = now.isoformat()
        users[user_id] = user_data
        save_users()
        await query.edit_message_text("🎉 You received 0.5 TON as your daily bonus!", reply_markup=back_button())

# 🚀 دستور اضافه کردن 1 TON به همه کاربران (فقط ادمین)
async def addtoall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    admin_ids = ["5095867558"]  # شناسه خودت رو اینجا بذار

    if user_id not in admin_ids:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    for uid in users:
        users[uid]["balance"] = users[uid].get("balance", 0) + 1

    save_users()
    await update.message.reply_text("✅ 1 TON added to all users' balances!")

# 🚀 اجرای ربات
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtoall", addtoall))  # اضافه شد
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
