import json
import random
import time
from datetime import datetime
from flask import Flask, request
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, Updater

# ====== تنظیمات اولیه ======
TOKEN = '7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc'  # توکن بات رو اینجا بزن
ADMIN_ID = 5095867558  # آیدی تلگرام ادمین رو اینجا بزن

DEPOSIT_WALLET = "UQAG_02lalmnQiisR-fbZLLSr861phEtyIrnWEUc7OwfxX5Y"

bot = telegram.Bot(token=TOKEN)
app = Flask(__name__)
users_file = 'users.json'

# ====== بارگذاری و ذخیره اطلاعات کاربران ======
def load_users():
    try:
        with open(users_file, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(users_file, 'w') as f:
        json.dump(users, f)

users = load_users()

# ====== اضافه کردن کاربر جدید به دیتابیس ======
def ensure_user(user_id, username, referrer_id=None):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            'balance': 0.0,
            'referrals': [],
            'start_date': str(datetime.utcnow()),
            'withdrawals': [],
            'deposits': [],
            'username': username or "",
            'last_bonus': 0,
            'referred_by': None,
        }
        # اگر رفرال وجود داشت و معتبر بود
        if referrer_id and str(referrer_id) in users and str(referrer_id) != uid:
            users[uid]['referred_by'] = str(referrer_id)
            # افزودن این یوزر به لیست رفرال‌های دعوت‌کننده
            users[str(referrer_id)]['referrals'].append(uid)
            # اضافه کردن 0.05 TON به موجودی دعوت‌کننده
            users[str(referrer_id)]['balance'] += 0.05
            save_users(users)
            # ارسال پیام به دعوت‌کننده
            try:
                bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"🎉 The [{username or uid}](tg://user?id={uid}) joined Plsuh NFT through your invitation link and 0.05 TON was added to your balance.",
                    parse_mode=telegram.ParseMode.MARKDOWN
                )
            except Exception as e:
                print("Error sending referral msg:", e)
        save_users(users)

# ====== منوی اصلی ======
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Balance💰", callback_data="balance")],
        [InlineKeyboardButton("Daily Bonus🎁", callback_data="daily_bonus")],
        [InlineKeyboardButton("Betting🎲", callback_data="betting")],
        [InlineKeyboardButton("Deposit➕", callback_data="deposit")],
        [InlineKeyboardButton("Withdrawal📤", callback_data="withdrawal")],
        [InlineKeyboardButton("Profile👤", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])

# ====== هندلر دستور استارت ======
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    # اگر پارامتر رفرال داشت
    ref_id = None
    args = context.args
    if args:
        ref_id = args[0]
    ensure_user(user.id, user.username, ref_id)
    update.message.reply_text("👋 Welcome to the bot!", reply_markup=get_main_menu())

# ====== هندلر دکمه‌ها ======
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    uid = str(user.id)
    ensure_user(user.id, user.username)
    user_data = users[uid]
    data = query.data

    if data == "balance":
        query.edit_message_text(f"💰 Your balance: {user_data['balance']:.2f} TON", reply_markup=get_back_button())

    elif data == "daily_bonus":
        now = time.time()
        last = user_data.get("last_bonus", 0)
        if now - last >= 86400:
            user_data["balance"] += 0.08
            user_data["last_bonus"] = now
            save_users(users)
            query.edit_message_text("🎁 You received your daily bonus of 0.08 TON!", reply_markup=get_back_button())
        else:
            remaining = 86400 - (now - last)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            query.edit_message_text(f"⌛ You can claim your next bonus in {hours}h {minutes}m", reply_markup=get_back_button())

    elif data == "back":
        query.edit_message_text("Main Menu:", reply_markup=get_main_menu())

    elif data == "betting":
        keyboard = [
            [InlineKeyboardButton("1-3-5", callback_data="bet_135"),
             InlineKeyboardButton("2-4-6", callback_data="bet_246")],
            [InlineKeyboardButton("1-1", callback_data="pair_1"),
             InlineKeyboardButton("2-2", callback_data="pair_2"),
             InlineKeyboardButton("3-3", callback_data="pair_3")],
            [InlineKeyboardButton("4-4", callback_data="pair_4"),
             InlineKeyboardButton("5-5", callback_data="pair_5"),
             InlineKeyboardButton("6-6", callback_data="pair_6")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        query.edit_message_text("🎲 Choose a betting option:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("bet_") or data.startswith("pair_"):
        context.user_data["bet_type"] = data
        query.edit_message_text("💵 Enter amount to bet (min 0.1 TON):")
        context.user_data["awaiting_bet"] = True

    elif data == "deposit":
        # نمایش آدرس ولت به صورت مونو اسپیس و قابل کپی
        wallet_text = f"💰 Deposit Wallet Address:\n\n<code>{DEPOSIT_WALLET}</code>\n\nClick to copy the address."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(wallet_text, parse_mode=telegram.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "withdrawal":
        keyboard = [
            [InlineKeyboardButton("0.5 TON", callback_data="w_0.5"),
             InlineKeyboardButton("1 TON", callback_data="w_1")],
            [InlineKeyboardButton("2 TON", callback_data="w_2"),
             InlineKeyboardButton("5 TON", callback_data="w_5")],
            [InlineKeyboardButton("10 TON", callback_data="w_10"),
             InlineKeyboardButton("15 TON", callback_data="w_15")],
            [InlineKeyboardButton("20 TON", callback_data="w_20")],
            [InlineKeyboardButton("NFT Withdrawal📤", callback_data="withdraw_nft")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
        query.edit_message_text("💸 Select TON amount to withdraw:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("w_"):
        amount = float(data.split("_")[1])
        if user_data["balance"] >= amount:
            context.user_data["pending_withdraw"] = amount
            query.edit_message_text("✍️ Please enter your TON wallet address:")
            context.user_data["awaiting_wallet"] = True
        else:
            query.edit_message_text("❌ Insufficient balance!", reply_markup=get_back_button())

    elif data == "withdraw_nft":
            text = "🎨 *Available NFTs:*\n"
            text += "• Desk Calendar #104863 = 1.3 TON\n"
            text += "• Lol Pop #24488 = 1.3 TON\n"
            text += "• B-day Candle #98618 = 1.5 TON\n"
            text += "• Snake Box #48486 = 1.5 TON\n"
            text += "• Candy Cane #19264 = 1.6 TON\n"
            text += "• Snoop Dogg #299426 = 2 TON\n"
            text += "• Ginger Cookie #89374 = 18.5 TON\n"
            text += "• Jester Hat #91301 = 50 TON"

    keyboard = [
        [InlineKeyboardButton("Desk Calendar", callback_data="nft_desk_calendar")],
        [InlineKeyboardButton("Lol Pop", callback_data="nft_lol_pop")],
        [InlineKeyboardButton("B-day Candle", callback_data="nft_bday_candle")],
        [InlineKeyboardButton("Snake Box", callback_data="nft_snake_box")],
        [InlineKeyboardButton("Candy Cane", callback_data="nft_candy_cane")],
        [InlineKeyboardButton("Snoop Dogg", callback_data="nft_snoop_dogg")],
        [InlineKeyboardButton("Ginger Cookie", callback_data="nft_ginger_cookie")],
        [InlineKeyboardButton("Jester Hat", callback_data="nft_jester_hat")],
        [InlineKeyboardButton("🔙 Back", callback_data="withdrawal")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    elif data.startswith("nft_"):
    nft_prices = {
        "nft_desk_calendar": (1.3, "Desk Calendar #104863"),
        "nft_lol_pop": (1.3, "Lol Pop #24488"),
        "nft_bday_candle": (1.5, "B-day Candle #98618"),
        "nft_snake_box": (1.5, "Snake Box #48486"),
        "nft_candy_cane": (1.6, "Candy Cane #19264"),
        "nft_snoop_dogg": (2, "Snoop Dogg #299426"),
        "nft_ginger_cookie": (18.5, "Ginger Cookie #89374"),
        "nft_jester_hat": (50, "Jester Hat #91301"),
    }

    if data in nft_prices:
        price, nft_name = nft_prices[data]
        if user_data[str(user_id)]["balance"] >= price:
            context.user_data["nft_price"] = price
            context.user_data["nft_name"] = nft_name
            context.user_data["awaiting_nft_username"] = True
            query.edit_message_text(
                f"✅ You selected: *{nft_name}*\n\nPlease enter your Telegram username (@username):",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            query.edit_message_text("❌ You don’t have enough TON for this NFT.\nPlease top up your balance or choose a cheaper NFT.")

def handle_text(update: Update, context: CallbackContext):
    user = update.effective_user
    uid = str(user.id)
    text = update.message.text
    ensure_user(user.id, user.username)
    
    if context.user_data.get("awaiting_wallet"):
        wallet = text
        amount = context.user_data.get("pending_withdraw", 0)
        users[uid]["balance"] -= amount
        save_users(users)
        update.message.reply_text(f"✅ Withdrawal of {amount:.2f} TON requested to:\n`{wallet}`\n\nWill be processed within 24h.", parse_mode=telegram.ParseMode.MARKDOWN)
        context.user_data["awaiting_wallet"] = False
        return

    if context.user_data.get("awaiting_nft_username"):
        username = text
        nft_name = context.user_data.get("nft_name", "NFT")
        price = context.user_data.get("nft_price", 0)

        users[uid]["balance"] -= price
        save_users(users)

        update.message.reply_text(
            f"✅ Request to withdraw *{nft_name}* for @{username} received.\nYour NFT will be sent within 24 hours.",
            parse_mode=telegram.ParseMode.MARKDOWN
        )
        context.user_data["awaiting_nft_username"] = False

def admin_commands(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return  # فقط ادمین اجازه داره

    text = update.message.text.strip()

    # /broadcast پیام همگانی
    if text.startswith("/broadcast "):
        msg = text[len("/broadcast "):]
        count = 0
        for uid in users.keys():
            try:
                bot.send_message(chat_id=int(uid), text=msg)
                count += 1
            except:
                continue
        update.message.reply_text(f"📢 Message sent to {count} users.")

    # /addtoall اضافه‌کردن به همه
    elif text.startswith("/addtoall "):
        try:
            amount = float(text.split()[1])
            for u in users.values():
                u['balance'] += amount
            save_users(users)
            update.message.reply_text(f"✅ Added {amount} TON to all users.")
        except:
            update.message.reply_text("❌ Invalid format. Use: /addtoall 0.1")

    # /add <user_id> <amount>
    elif text.startswith("/add "):
        try:
            _, uid, amount = text.split()
            uid = str(int(uid))
            amount = float(amount)
            if uid in users:
                users[uid]['balance'] += amount
                save_users(users)
                update.message.reply_text(f"✅ Added {amount} TON to user {uid}")
            else:
                update.message.reply_text("❌ User not found.")
        except:
            update.message.reply_text("❌ Invalid format. Use: /add <user_id> <amount>")
            
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))  # 👈 اضافه کن اینو

from flask import Flask
from threading import Thread
import nest_asyncio
import asyncio

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

async def run_bot():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

def run_flask():
    app_flask.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    nest_asyncio.apply()
    Thread(target=run_flask).start()
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    loop.run_forever()
    
