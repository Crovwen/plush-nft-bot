import json
import random
import os
import pytz
import asyncio
from datetime import datetime, timedelta
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from threading import Thread

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"
ADMIN_ID = 5095867558
DEPOSIT_WALLET_ADDRESS = "UQAG_02lalmnQiisR-fbZLLSr861phEtyIrnWEUc7OwfxX5Y"
DAILY_BONUS_AMOUNT = 0.08
REFERRAL_REWARD = 0.05
USERS_FILE = "users.json"
MIN_BET = 0.1

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

users = {}

def load_users():
    global users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        users = {}

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

load_users()

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
        save_users()
    await update.message.reply_text("Choose an option 👇", reply_markup=get_main_menu())

# ============= CALLBACK HANDLER ============
withdraw_amounts = [0.5, 1, 2, 3, 5, 10, 15, 20]
awaiting_withdraw_address = {}
awaiting_bet_amount = {}
current_bet_type = {}

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
            save_users()
            await query.edit_message_text(f"🎉 You claimed {DAILY_BONUS_AMOUNT} TON bonus!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            remaining = timedelta(hours=24) - (now - last_claim)
            h, r = divmod(int(remaining.total_seconds()), 3600)
            m = r // 60
            await query.edit_message_text(f"⏳ Bonus available in {h}h {m}m.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "deposit":
        text = f"📥 Send TON to this wallet:\n`{DEPOSIT_WALLET_ADDRESS}`\n\n(Make sure to send only TON!)"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "withdrawal":
        buttons = [[InlineKeyboardButton(f"{amt} TON", callback_data=f"ton_withdraw_{amt}")] for amt in withdraw_amounts]
        buttons.append([InlineKeyboardButton("🎨 NFT Withdrawal", callback_data="nft_withdrawal")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text("📤 Choose withdrawal option:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("ton_withdraw_"):
        amt = float(query.data.split("_")[-1])
        if user["balance"] >= amt:
            awaiting_withdraw_address[user_id] = amt
            await query.edit_message_text("📤 Please send your TON wallet address:")
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
            save_users()
            await query.edit_message_text(f"✅ NFT '{nft_name} {nft_tag}' will be sent within 24h.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        else:
            await query.edit_message_text("❌ Not enough balance for this NFT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif query.data == "back":
        await query.edit_message_text("Choose an option 👇", reply_markup=get_main_menu())

# ادامه در بخش دوم ...

# ====== شرط‌بندی ======
    elif query.data == "betting":
        await query.edit_message_text(
            "🎲 Choose a bet type:\n\n"
            "• Odd (1-3-5) or Even (2-4-6): 1.5x\n"
            "• Pairs (1-1 to 6-6): 3x",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Odd ⚫", callback_data="bet_odd"),
                 InlineKeyboardButton("Even ⚪", callback_data="bet_even")],
                [InlineKeyboardButton("1-1", callback_data="bet_pair_1_1"),
                 InlineKeyboardButton("2-2", callback_data="bet_pair_2_2"),
                 InlineKeyboardButton("3-3", callback_data="bet_pair_3_3")],
                [InlineKeyboardButton("4-4", callback_data="bet_pair_4_4"),
                 InlineKeyboardButton("5-5", callback_data="bet_pair_5_5"),
                 InlineKeyboardButton("6-6", callback_data="bet_pair_6_6")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back")]
            ])
        )

    elif query.data.startswith("bet_"):
        current_bet_type[user_id] = query.data
        awaiting_bet_amount[user_id] = True
        await query.edit_message_text("💸 Enter bet amount (min 0.1 TON):")

# ====== پیام متنی ها ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id in awaiting_withdraw_address:
        address = text.strip()
        amt = awaiting_withdraw_address.pop(user_id)
        users[user_id]["balance"] -= amt
        save_users()
        await update.message.reply_text(f"✅ {amt} TON will be sent to {address} within 24h.")
        return

    if awaiting_bet_amount.get(user_id):
        try:
            amount = float(text)
            if amount < MIN_BET:
                await update.message.reply_text(f"❌ Minimum bet is {MIN_BET} TON.")
                return
            if users[user_id]["balance"] < amount:
                await update.message.reply_text("❌ Not enough balance.")
                return

            bet_type = current_bet_type[user_id]
            users[user_id]["balance"] -= amount

            if bet_type in ["bet_odd", "bet_even"]:
                roll = random.randint(1, 6)
                await update.message.reply_dice(emoji="🎲")
                await asyncio.sleep(3)
                result_type = "bet_odd" if roll % 2 != 0 else "bet_even"
                if result_type == bet_type:
                    win = round(amount * 1.5, 2)
                    users[user_id]["balance"] += win
                    await update.message.reply_text(f"🎲 Rolled: {roll}\n✅ You won {win} TON!")
                else:
                    await update.message.reply_text(f"🎲 Rolled: {roll}\n❌ You lost.")
            elif bet_type.startswith("bet_pair_"):
                roll1 = random.randint(1, 6)
                roll2 = random.randint(1, 6)
                await update.message.reply_dice(emoji="🎲")
                await update.message.reply_dice(emoji="🎲")
                await asyncio.sleep(3)
                _, _, x, y = bet_type.split("_")
                if str(roll1) == x and str(roll2) == y:
                    win = round(amount * 3, 2)
                    users[user_id]["balance"] += win
                    await update.message.reply_text(f"🎲 Rolled: {roll1}-{roll2}\n✅ You won {win} TON!")
                else:
                    await update.message.reply_text(f"🎲 Rolled: {roll1}-{roll2}\n❌ You lost.")
            else:
                await update.message.reply_text("❌ Invalid bet type.")
        except:
            await update.message.reply_text("❌ Invalid amount.")
        awaiting_bet_amount.pop(user_id, None)
        current_bet_type.pop(user_id, None)
        save_users()

# ====== ادمین ======
async def admin_add_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        amt = float(context.args[0])
        for user in users.values():
            user["balance"] += amt
        save_users()
        await update.message.reply_text(f"✅ {amt} TON added to all users.")
    except:
        await update.message.reply_text("❌ Usage: /addtoall 0.1")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"👥 Total users: {len(users)}")

async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target_id = context.args[0]
        amt = float(context.args[1])
        if target_id in users:
            users[target_id]["balance"] += amt
            save_users()
            await update.message.reply_text(f"✅ Added {amt} TON to {target_id}.")
        else:
            await update.message.reply_text("❌ User not found.")
    except:
        await update.message.reply_text("❌ Usage: /adduser 123456789 0.5")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    success = 0
    for uid in users.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
            success += 1
        except:
            continue
    await update.message.reply_text(f"✅ Message sent to {success} users.")

# ========== RUN ==========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Admin Commands
    app.add_handler(CommandHandler("addtoall", admin_add_all))
    app.add_handler(CommandHandler("users", admin_list_users))
    app.add_handler(CommandHandler("adduser", admin_add_user))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))

    Thread(target=run_flask).start()
    app.run_polling()

# ========== FLASK for Render ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot is running."

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    main()

