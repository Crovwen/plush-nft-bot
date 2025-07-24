import logging import json import os from datetime import datetime, timedelta from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

-------------------- ذخیره اطلاعات کاربران --------------------

USER_DATA_FILE = "users.json"

if os.path.exists(USER_DATA_FILE): with open(USER_DATA_FILE, "r") as f: users_data = json.load(f) else: users_data = {}

def save_users_data(): with open(USER_DATA_FILE, "w") as f: json.dump(users_data, f, indent=4)

-------------------- تنظیمات اولیه --------------------

logging.basicConfig(level=logging.INFO) TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc" BONUS_AMOUNT = 0.5 NFT_OPTIONS = [ ("Golden Pepe (15 TON)", 15), ("Silver Pepe (22 TON)", 22), ("Diamond Pepe (35 TON)", 35), ("Platinum Pepe (50 TON)", 50), ("King Pepe (100 TON)", 100), ]

-------------------- دکمه های منو --------------------

def get_main_keyboard(): keyboard = [ [InlineKeyboardButton("Balance💰", callback_data="balance")], [InlineKeyboardButton("My Profile👤", callback_data="profile")], [InlineKeyboardButton("Referral Link👥", callback_data="referral")], [InlineKeyboardButton("NFT Withdrawal📤", callback_data="withdrawal")], [InlineKeyboardButton("Deposit📥", callback_data="deposit")], [InlineKeyboardButton("Daily bonus🎁", callback_data="bonus")], ] return InlineKeyboardMarkup(keyboard)

-------------------- شروع ربات --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user user_id = str(user.id) if user_id not in users_data: users_data[user_id] = { "balance": 0.0, "referrals": [], "start_date": datetime.now().strftime("%Y-%m-%d %H:%M"), "name": user.username or user.first_name, "withdrawals": 0, "deposits": 0, "last_bonus": "" } save_users_data() text = "Welcome to @PlushNFTbot\n\nPlease choose one of the options below." await update.message.reply_text(text, reply_markup=get_main_keyboard())

-------------------- مدیریت کلید ها --------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = str(query.from_user.id) user_data = users_data.get(user_id, {})

def back_button():
    return [[InlineKeyboardButton("🔙 Back to menu", callback_data="back")]]

if query.data == "back":
    await query.edit_message_text(
        text="Welcome to @PlushNFTbot\n\nPlease choose one of the options below.",
        reply_markup=get_main_keyboard()
    )
    return

if query.data == "balance":
    text = f"Your balance: {user_data.get('balance', 0)} TON"
    markup = InlineKeyboardMarkup(back_button())

elif query.data == "profile":
    text = (
        f"Your ID: {query.from_user.id}\n"
        f"Username: @{query.from_user.username or query.from_user.first_name}\n"
        f"Start date: {user_data.get('start_date', '-') }\n"
        f"Referrals: {len(user_data.get('referrals', []))}\n"
        f"Withdrawals: {user_data.get('withdrawals', 0)}\n"
        f"Deposits: {user_data.get('deposits', 0)}"
    )
    markup = InlineKeyboardMarkup(back_button())

elif query.data == "referral":
    ref_link = f"https://t.me/PlushNFTbot?start={user_id}"
    text = f"Your referral link:\n{ref_link}"
    markup = InlineKeyboardMarkup(back_button())

elif query.data == "withdrawal":
    referrals = user_data.get("referrals", [])
    if len(referrals) < 10:
        text = "You need to invite at least 10 users to withdraw an NFT."
        markup = InlineKeyboardMarkup(back_button())
    else:
        buttons = [
            [InlineKeyboardButton(f"{name}", callback_data=f"nft_{price}")]
            for name, price in NFT_OPTIONS
            if user_data.get("balance", 0) >= price
        ]
        buttons.append([InlineKeyboardButton("🔙 Back to menu", callback_data="back")])
        if buttons:
            text = "Choose an NFT to withdraw:"
        else:
            text = "You don't have enough balance for any NFT."
        markup = InlineKeyboardMarkup(buttons)

elif query.data.startswith("nft_"):
    price = float(query.data.split("_")[1])
    if user_data.get("balance", 0) >= price:
        user_data["balance"] -= price
        user_data["withdrawals"] += 1
        save_users_data()
        text = "✅ Withdrawal successful! Your NFT will be gifted to your Telegram account within 24 working hours."
    else:
        text = "❌ Not enough balance."
    markup = InlineKeyboardMarkup(back_button())

elif query.data == "deposit":
    text = "🚧 Deposit feature coming soon..."
    markup = InlineKeyboardMarkup(back_button())

elif query.data == "bonus":
    now = datetime.now()
    last_bonus = user_data.get("last_bonus")
    if not last_bonus or now - datetime.strptime(last_bonus, "%Y-%m-%d %H:%M:%S") > timedelta(hours=24):
        user_data["balance"] += BONUS_AMOUNT
        user_data["last_bonus"] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_users_data()
        text = f"🎁 You received your daily bonus of {BONUS_AMOUNT} TON!"
    else:
        text = "⏳ You can only claim your daily bonus once every 24 hours."
    markup = InlineKeyboardMarkup(back_button())

else:
    text = "Unknown command."
    markup = get_main_keyboard()

await query.edit_message_text(text=text, reply_markup=markup)

-------------------- هندل کردن لینک دعوت --------------------

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user args = context.args user_id = str(user.id)

if user_id not in users_data:
    referrer_id = args[0] if args else None
    users_data[user_id] = {
        "balance": 0.0,
        "referrals": [],
        "start_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "name": user.username or user.first_name,
        "withdrawals": 0,
        "deposits": 0,
        "last_bonus": ""
    }
    if referrer_id and referrer_id in users_data and user_id not in users_data[referrer_id]["referrals"]:
        users_data[referrer_id]["referrals"].append(user_id)
        users_data[referrer_id]["balance"] += 0.5
    save_users_data()

text = "Welcome to @PlushNFTbot\n\nPlease choose one of the options below."
await update.message.reply_text(text, reply_markup=get_main_keyboard())

-------------------- اجرای ربات --------------------

app = ApplicationBuilder().token(TOKEN).build() app.add_handler(CommandHandler("start", handle_referral)) app.add_handler(CallbackQueryHandler(handle_callback))

app.run_polling()

