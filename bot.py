import json import random from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove, Dice from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "7593433447:AAGkPgNGsXx5bvJYQiea64HrCOGIiKOn2Pc" ADMIN_ID = 5095867558 DATA_FILE = "users.json"

Load or initialize user data

def load_users(): try: with open(DATA_FILE, "r") as f: return json.load(f) except FileNotFoundError: return {}

def save_users(data): with open(DATA_FILE, "w") as f: json.dump(data, f)

users = load_users()

Start command

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) if user_id not in users: users[user_id] = {"balance": 0.0, "ref": None, "claimed_bonus": False} if context.args: ref_id = context.args[0] if ref_id != user_id and ref_id in users: users[user_id]["ref"] = ref_id users[ref_id]["balance"] += 0.05 await context.bot.send_message(chat_id=ref_id, text=f"🎉 Your friend ({user_id}) joined the bot via your referral link!\n💸 You earned 0.05 TON!") save_users(users) await send_main_menu(update, context)

Send Main Menu

def get_main_keyboard(): keyboard = [ [InlineKeyboardButton("💰 Balance", callback_data="balance")], [InlineKeyboardButton("👤 Profile", callback_data="profile")], [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")], [InlineKeyboardButton("📤 Withdrawal", callback_data="withdraw")], [InlineKeyboardButton("📥 Deposit", callback_data="deposit")], [InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")], [InlineKeyboardButton("🎲 Betting", callback_data="betting")], ] return InlineKeyboardMarkup(keyboard)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE): keyboard = get_main_keyboard() if update.message: await update.message.reply_text("Please choose one of the options below 👇", reply_markup=keyboard) elif update.callback_query: await update.callback_query.edit_message_text("Please choose one of the options below 👇", reply_markup=keyboard)

Callback Handlers

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = str(query.from_user.id)

if user_id not in users:
    users[user_id] = {"balance": 0.0, "ref": None, "claimed_bonus": False}

if query.data == "balance":
    balance = users[user_id]["balance"]
    await query.edit_message_text(f"💰 Your balance: {balance:.2f} TON", reply_markup=get_main_keyboard())

elif query.data == "profile":
    await query.edit_message_text(f"👤 Your ID: {user_id}\n💰 Balance: {users[user_id]['balance']:.2f} TON", reply_markup=get_main_keyboard())

elif query.data == "referral":
    link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"
    await query.edit_message_text(
        f"🔗 Invite your friends and earn 0.05 TON for each referral!\n\nYour referral link:\n{link}",
        reply_markup=get_main_keyboard())

elif query.data == "withdraw":
    await query.edit_message_text("📤 Withdrawal feature is under construction.", reply_markup=get_main_keyboard())

elif query.data == "deposit":
    await query.edit_message_text(
        "📥 To deposit, please send TON to the following wallet address:\n\nUQAG_02lalmnQiisR-fbZLLSr861phEtyIrnWEUc7OwfxX5Y",
        reply_markup=get_main_keyboard())

elif query.data == "bonus":
    if not users[user_id].get("claimed_bonus"):
        users[user_id]["balance"] += 0.06
        users[user_id]["claimed_bonus"] = True
        save_users(users)
        await query.edit_message_text("🎁 You claimed your 0.06 TON daily bonus!", reply_markup=get_main_keyboard())
    else:
        await query.edit_message_text("❗ You have already claimed your bonus today!", reply_markup=get_main_keyboard())

elif query.data == "betting":
    context.user_data['bet_mode'] = True
    await query.edit_message_text("🎲 How much TON do you want to bet?", reply_markup=ReplyKeyboardRemove())

Betting amount input

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) if context.user_data.get('bet_mode'): try: amount = float(update.message.text) if users[user_id]['balance'] < amount: await update.message.reply_text("❌ Insufficient balance.") return context.user_data['bet_amount'] = amount context.user_data['bet_mode'] = False keyboard = [ [InlineKeyboardButton("2 - 4 - 6", callback_data="even"), InlineKeyboardButton("1 - 3 - 5", callback_data="odd")], [InlineKeyboardButton("6-6", callback_data="pair_6"), InlineKeyboardButton("5-5", callback_data="pair_5")], [InlineKeyboardButton("4-4", callback_data="pair_4"), InlineKeyboardButton("3-3", callback_data="pair_3")], [InlineKeyboardButton("2-2", callback_data="pair_2"), InlineKeyboardButton("1-1", callback_data="pair_1")], ] text = "🎲 Choose your bet type:\n2 - 4 - 6 = 1.5x\n1 - 3 - 5 = 1.5x\n6-6 to 1-1 = 3x" await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard)) except ValueError: await update.message.reply_text("❗ Invalid amount. Enter a number.")

Betting result

async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = str(query.from_user.id) amount = context.user_data.get('bet_amount', 0.0) bet_type = query.data result_msg = ""

if bet_type in ["even", "odd"]:
    dice = await query.message.reply_dice(emoji="🎲")
    rolled = dice.dice.value
    if (bet_type == "even" and rolled % 2 == 0) or (bet_type == "odd" and rolled % 2 == 1):
        reward = amount * 1.5
        users[user_id]['balance'] += reward
        result_msg = f"🎉 You rolled {rolled} and won {reward:.2f} TON!"
    else:
        users[user_id]['balance'] -= amount
        result_msg = f"❌ You rolled {rolled} and lost {amount:.2f} TON."

elif bet_type.startswith("pair_"):
    expected = int(bet_type.split("_")[1])
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    await query.message.reply_text(f"🎲 You rolled {d1} and {d2}")
    if d1 == d2 == expected:
        reward = amount * 3
        users[user_id]['balance'] += reward
        result_msg = f"🎉 You got {expected}-{expected} and won {reward:.2f} TON!"
    else:
        users[user_id]['balance'] -= amount
        result_msg = f"❌ You lost {amount:.2f} TON."

save_users(users)
await query.message.reply_text(result_msg)
await send_main_menu(update, context)

Admin command to add TON to all

async def addtoall(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return try: amount = float(context.args[0]) for uid in users: users[uid]['balance'] += amount try: await context.bot.send_message(chat_id=uid, text=f"🎁 You received {amount:.2f} TON from admin!") except: pass save_users(users) await update.message.reply_text(f"✅ Added {amount} TON to all users.") except: await update.message.reply_text("❗ Usage: /addtoall 1.0")

Admin command to send message to all

async def sendall(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return text = update.message.text.replace("/sendall", "", 1).strip() for uid in users: try: await context.bot.send_message(chat_id=uid, text=text) except: pass await update.message.reply_text("✅ Message sent to all users.")

Main function

def main(): app = Application.builder().token(TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("addtoall", addtoall)) app.add_handler(CommandHandler("sendall", sendall)) app.add_handler(CallbackQueryHandler(handle_callback)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)) app.add_handler(CallbackQueryHandler(handle_bet, pattern="^(even|odd|pair_\d)$")) app.run_polling()

if name == "main": main()

