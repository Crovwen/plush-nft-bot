# ... بقیه import ها
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
import json
import random

# فایل ذخیره اطلاعات
DATA_FILE = "users.json"
users = {}
PENDING_WITHDRAWALS = {}
PENDING_BETS = {}

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc"

# لود و سیو دیتا
def load_users():
    global users
    try:
        with open(DATA_FILE, "r") as f:
            users = json.load(f)
    except:
        users = {}

def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

load_users()

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in users:
        users[user_id] = {"balance": 0, "referrals": 0, "withdrawals": 0}
        save_users()

        # رفرال
        if context.args:
            referrer = context.args[0]
            if referrer != user_id and referrer in users:
                users[referrer]["balance"] += 0.05
                users[referrer]["referrals"] += 1
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer),
                        text=f"👤 User {user_id} joined via your referral link.\n💰 You earned 0.05 TON!"
                    )
                except:
                    pass
                save_users()

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")],
        [InlineKeyboardButton("📤 Withdraw", callback_data="withdraw_menu")],
        [InlineKeyboardButton("👥 Referral", callback_data="referral")],
        [InlineKeyboardButton("🎲 Betting", callback_data="betting")]
    ])
    await update.message.reply_text("Welcome to Plush NFT Bot!", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = users.get(user_id, {})

    if query.data == "menu":
        await start(update, context)

    elif query.data == "balance":
        balance = user_data.get("balance", 0)
        await query.edit_message_text(f"💼 Your balance: {balance:.2f} TON", reply_markup=back_button())

    elif query.data == "referral":
        await query.edit_message_text(
            f"🔗 Your referral link:\n"
            f"https://t.me/PlushNFTbot?start={user_id}\n\n"
            f"👥 Referrals: {user_data.get('referrals', 0)}\n"
            f"💰 Earn 0.05 TON per referral!",
            reply_markup=back_button()
        )

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

    elif query.data == "betting":
        PENDING_BETS[user_id] = {}
        await query.edit_message_text("🎲 How much do you want to bet?", reply_markup=back_button())

    elif query.data.startswith("bet_even") or query.data.startswith("bet_odd"):
        bet = PENDING_BETS.get(user_id)
        if not bet or "amount" not in bet:
            await query.edit_message_text("❌ Please enter your bet amount first.", reply_markup=back_button())
            return
        result = await context.bot.send_dice(chat_id=int(user_id))
        dice = result.dice.value
        amount = bet["amount"]
        if query.data == "bet_even" and dice in [2, 4, 6]:
            reward = amount * 1.5
            users[user_id]["balance"] += reward
            await context.bot.send_message(chat_id=int(user_id), text=f"🎉 Dice: {dice}\n✅ You won {reward:.2f} TON!")
        elif query.data == "bet_odd" and dice in [1, 3, 5]:
            reward = amount * 1.5
            users[user_id]["balance"] += reward
            await context.bot.send_message(chat_id=int(user_id), text=f"🎉 Dice: {dice}\n✅ You won {reward:.2f} TON!")
        else:
            users[user_id]["balance"] -= amount
            await context.bot.send_message(chat_id=int(user_id), text=f"🎲 Dice: {dice}\n❌ You lost {amount:.2f} TON.")
        save_users()
        del PENDING_BETS[user_id]

    elif query.data.startswith("pair_"):
        pair_value = int(query.data.split("_")[1])
        bet = PENDING_BETS.get(user_id)
        if not bet or "amount" not in bet:
            await query.edit_message_text("❌ Please enter your bet amount first.", reply_markup=back_button())
            return
        msg1 = await context.bot.send_dice(chat_id=int(user_id))
        msg2 = await context.bot.send_dice(chat_id=int(user_id))
        d1 = msg1.dice.value
        d2 = msg2.dice.value
        amount = bet["amount"]
        if d1 == d2 == pair_value:
            reward = amount * 3
            users[user_id]["balance"] += reward
            await context.bot.send_message(chat_id=int(user_id), text=f"🎉 Dice: {d1}-{d2}\n✅ You won {reward:.2f} TON!")
        else:
            users[user_id]["balance"] -= amount
            await context.bot.send_message(chat_id=int(user_id), text=f"🎲 Dice: {d1}-{d2}\n❌ You lost {amount:.2f} TON.")
        save_users()
        del PENDING_BETS[user_id]

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    if user_id in PENDING_BETS:
        try:
            amount = float(text)
            if users[user_id]["balance"] < amount:
                await update.message.reply_text("❌ Not enough balance.")
                del PENDING_BETS[user_id]
                return
            PENDING_BETS[user_id]["amount"] = amount
            keyboard = [
                [
                    InlineKeyboardButton("2 - 4 - 6", callback_data="bet_even"),
                    InlineKeyboardButton("1 - 3 - 5", callback_data="bet_odd")
                ],
                [
                    InlineKeyboardButton("6-6", callback_data="pair_6"),
                    InlineKeyboardButton("5-5", callback_data="pair_5"),
                    InlineKeyboardButton("4-4", callback_data="pair_4"),
                    InlineKeyboardButton("3-3", callback_data="pair_3"),
                    InlineKeyboardButton("2-2", callback_data="pair_2"),
                    InlineKeyboardButton("1-1", callback_data="pair_1"),
                ]
            ]
            text = "🎲 Choose your bet type:\n\n2 - 4 - 6 = 1.5x\n1 - 3 - 5 = 1.5x\n6-6 to 1-1 = 3x"
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await update.message.reply_text("❌ Invalid amount. Try again.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
