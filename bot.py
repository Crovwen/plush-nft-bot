import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"

# پایگاه داده ساده در حافظه
users = {}

# پیام خوش‌آمدگویی
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    referrer_id = None

    # ثبت کاربر
    if user_id not in users:
        users[user_id] = {
            "username": user.username or "N/A",
            "start_time": datetime.now(),
            "balance": 0.0,
            "referrals": [],
            "referrer": None,
            "withdrawals": 0,
            "deposits": 0,
            "last_bonus": datetime.min
        }

        # بررسی لینک دعوت
        if context.args:
            try:
                referrer_id = int(context.args[0])
                if referrer_id in users and referrer_id != user_id:
                    users[user_id]["referrer"] = referrer_id
                    users[referrer_id]["referrals"].append(user_id)
                    users[referrer_id]["balance"] += 0.5
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 Your friend ({user_id}) joined the bot using your referral link!"
                    )
            except ValueError:
                pass

    keyboard = [
        [InlineKeyboardButton("Balance💰", callback_data='balance')],
        [InlineKeyboardButton("My Profile👤", callback_data='profile')],
        [InlineKeyboardButton("Referral Link👥", callback_data='referral')],
        [InlineKeyboardButton("NFT Withdrawal📤", callback_data='withdraw')],
        [InlineKeyboardButton("Deposit📥", callback_data='deposit')],
        [InlineKeyboardButton("Daily bonus🎁", callback_data='bonus')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome to @PlushNFTbot\n\nPlease select one of the options below:",
        reply_markup=reply_markup
    )

# مدیریت دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = users.get(user_id)

    if not user_data:
        await query.edit_message_text("Please use /start to begin.")
        return

    if query.data == 'balance':
        await query.edit_message_text(f"💰 Your balance: {user_data['balance']:.2f} TON")

    elif query.data == 'profile':
        profile_text = (
            f"👤 Your Profile:\n"
            f"ID: {user_id}\n"
            f"Username: @{user_data['username']}\n"
            f"Start Date: {user_data['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"Referrals: {len(user_data['referrals'])}\n"
            f"Withdrawals: {user_data['withdrawals']}\n"
            f"Deposits: {user_data['deposits']}\n"
            f"Balance: {user_data['balance']:.2f} TON"
        )
        await query.edit_message_text(profile_text)

    elif query.data == 'referral':
        link = f"https://t.me/PlushNFTbot?start={user_id}"
        await query.edit_message_text(f"👥 Your referral link:\n{link}")

    elif query.data == 'withdraw':
        if len(user_data["referrals"]) < 10:
            await query.edit_message_text("❌ You need to invite at least 10 users to withdraw NFTs.")
        else:
            keyboard = [
                [InlineKeyboardButton("NFT 1 - 15 TON", callback_data='nft_15')],
                [InlineKeyboardButton("NFT 2 - 22 TON", callback_data='nft_22')],
                [InlineKeyboardButton("NFT 3 - 35 TON", callback_data='nft_35')],
                [InlineKeyboardButton("NFT 4 - 50 TON", callback_data='nft_50')],
                [InlineKeyboardButton("NFT 5 - 100 TON", callback_data='nft_100')],
            ]
            await query.edit_message_text("💎 Choose an NFT to withdraw:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('nft_'):
        price = float(query.data.split('_')[1])
        if user_data["balance"] >= price:
            user_data["balance"] -= price
            user_data["withdrawals"] += 1
            await query.edit_message_text(
                "✅ Your withdrawal was successful.\nYour NFT will be gifted to your Telegram within 24 business hours."
            )
        else:
            await query.edit_message_text("❌ Insufficient balance for this NFT.")

    elif query.data == 'deposit':
        await query.edit_message_text("💼 Deposit feature is coming soon...")

    elif query.data == 'bonus':
        now = datetime.now()
        if now - user_data["last_bonus"] >= timedelta(hours=24):
            user_data["balance"] += 0.5
            user_data["last_bonus"] = now
            await query.edit_message_text("🎁 Daily bonus claimed! You received 0.5 TON.")
        else:
            remaining = timedelta(hours=24) - (now - user_data["last_bonus"])
            await query.edit_message_text(f"⏳ You can claim your bonus again in {remaining.seconds//3600}h {(remaining.seconds//60)%60}m.")

# اجرای بات
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
