import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# دیتا موقت
user_data = {}

# توکن ربات
TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"

# منوی اصلی
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Balance💰", callback_data='balance')],
        [InlineKeyboardButton("My Profile👤", callback_data='profile')],
        [InlineKeyboardButton("Referral Link👥", callback_data='referral')],
        [InlineKeyboardButton("NFT Withdrawal📤", callback_data='withdraw')],
        [InlineKeyboardButton("Deposit📥", callback_data='deposit')],
        [InlineKeyboardButton("Daily bonus🎁", callback_data='bonus')]
    ]
    return InlineKeyboardMarkup(keyboard)

# دکمه برگشت
def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to menu", callback_data='menu')]])

# پیام شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if uid not in user_data:
        user_data[uid] = {
            "name": user.full_name,
            "start_date": datetime.now(),
            "referrals": 0,
            "withdrawals": 0,
            "deposits": 0,
            "balance": 0.0,
            "last_bonus": None
        }

    await update.message.reply_text(
        "Welcome to @PlushNFTbot\n\nPlease choose one of the options below:",
        reply_markup=get_main_menu()
    )

# هندلر دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in user_data:
        await query.edit_message_text("Please use /start first.")
        return

    data = query.data

    if data == 'menu':
        await query.edit_message_text(
            "Welcome to @PlushNFTbot\n\nPlease choose one of the options below:",
            reply_markup=get_main_menu()
        )
    elif data == 'balance':
        balance = user_data[uid]["balance"]
        await query.edit_message_text(
            f"💰 Your current balance: {balance:.2f} TON",
            reply_markup=get_back_button()
        )
    elif data == 'profile':
        u = user_data[uid]
        await query.edit_message_text(
            f"👤 Profile Info:\n"
            f"🆔 User ID: {uid}\n"
            f"👤 Name: {u['name']}\n"
            f"📅 Started: {u['start_date'].strftime('%Y-%m-%d %H:%M')}\n"
            f"👥 Referrals: {u['referrals']}\n"
            f"📤 Withdrawals: {u['withdrawals']}\n"
            f"📥 Deposits: {u['deposits']}",
            reply_markup=get_back_button()
        )
    elif data == 'referral':
        link = f"https://t.me/PlushNFTbot?start={uid}"
        await query.edit_message_text(
            f"👥 Your referral link:\n{link}",
            reply_markup=get_back_button()
        )
    elif data == 'withdraw':
        if user_data[uid]["referrals"] < 10:
            await query.edit_message_text(
                "❌ You need to invite at least 10 users to make a withdrawal.",
                reply_markup=get_back_button()
            )
        else:
            await query.edit_message_text(
                "Choose an NFT to withdraw:\n\n"
                "1️⃣ NFT Bronze - 15 TON\n"
                "2️⃣ NFT Silver - 22 TON\n"
                "3️⃣ NFT Gold - 35 TON\n"
                "4️⃣ NFT Diamond - 100 TON\n\n"
                "🚀 Feature coming soon...",
                reply_markup=get_back_button()
            )
    elif data == 'deposit':
        await query.edit_message_text(
            "🚧 Deposit feature coming soon...",
            reply_markup=get_back_button()
        )
    elif data == 'bonus':
        now = datetime.now()
        last = user_data[uid]["last_bonus"]
        if not last or (now - last) > timedelta(hours=24):
            user_data[uid]["balance"] += 0.5
            user_data[uid]["last_bonus"] = now
            await query.edit_message_text(
                "🎁 Daily bonus received! 0.5 TON added to your balance.",
                reply_markup=get_back_button()
            )
        else:
            remaining = timedelta(hours=24) - (now - last)
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await query.edit_message_text(
                f"⏳ You have already claimed your daily bonus.\n"
                f"Please wait {hours}h {minutes}m.",
                reply_markup=get_back_button()
            )

# اجرای ربات
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
