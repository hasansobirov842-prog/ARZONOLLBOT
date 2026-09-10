import os
import sqlite3
import logging
from datetime import datetime, date

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# KARTA
PAYMENT_CARD = os.getenv(
    "PAYMENT_CARD",
    "9860080390168864"
)

PAYMENT_OWNER = "R.O"

DB = "arzonol.db"

MIN_TOPUP = 10000

REFERRAL_BONUS = 100
DAILY_BONUS = 50

STARS_PRICE = 205

FOLLOWER_100_PRICE = 2000
MAX_FOLLOWERS = 100000

REACTION_PRICE = 100
MIN_REACTIONS = 10
MAX_REACTIONS = 1000


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =========================================================
# RAQAMLAR
# =========================================================

NUMBERS = [
    ("Bangladesh", "🇧🇩", "8999"),
    ("Colombia", "🇨🇴", "7890"),
    ("India", "🇮🇳", "7999"),
    ("Niger", "🇳🇪", "9676"),
    ("United States", "🇺🇸", "9476"),
    ("Ethiopia", "🇪🇹", "8999"),
    ("Myanmar", "🇲🇲", "7999"),
    ("Canada", "🇨🇦", "7999"),
    ("Philippines", "🇵🇭", "10000"),
    ("Afghanistan", "🇦🇫", "9999"),
]


# =========================================================
# DATABASE
# =========================================================

def connect():
    return sqlite3.connect(DB)


def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            balance INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            daily_date TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT,
            target TEXT DEFAULT '',
            quantity INTEGER DEFAULT 0,
            amount INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    con.commit()
    con.close()


def ensure_user(user_id, username="", referred_by=0):
    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    exists = cur.fetchone()

    if not exists:

        if referred_by == user_id:
            referred_by = 0

        cur.execute("""
            INSERT INTO users
            (user_id, username, balance, referrals, referred_by, daily_date)
            VALUES (?, ?, 0, 0, ?, '')
        """, (
            user_id,
            username or "",
            referred_by
        ))

        if referred_by:
            cur.execute("""
                UPDATE users
                SET balance = balance + ?,
                    referrals = referrals + 1
                WHERE user_id=?
            """, (
                REFERRAL_BONUS,
                referred_by
            ))

    else:
        cur.execute(
            "UPDATE users SET username=? WHERE user_id=?",
            (username or "", user_id)
        )

    con.commit()
    con.close()


def get_balance(user_id):
    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()

    con.close()

    return row[0] if row else 0


def add_balance(user_id, amount):
    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
    """, (
        amount,
        user_id
    ))

    con.commit()
    con.close()


def remove_balance(user_id, amount):
    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance = balance - ?
        WHERE user_id=? AND balance >= ?
    """, (
        amount,
        user_id,
        amount
    ))

    changed = cur.rowcount

    con.commit()
    con.close()

    return changed == 1


# =========================================================
# ASOSIY MENYU
# =========================================================

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📱 Nomer olish", "⭐ Stars olish"],
            ["📈 Nakrutka", "💳 Balans"],
            ["➕ Pul to'ldirish", "🎁 Kunlik bonus"],
            ["👥 Referal", "📦 Buyurtmalar"],
            ["ℹ️ Yordam"],
        ],
        resize_keyboard=True
    )


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="home"
            )
        ]
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    referral_id = 0

    if context.args:
        try:
            referral_id = int(context.args[0])
        except ValueError:
            referral_id = 0

    ensure_user(
        user.id,
        user.username,
        referral_id
    )

    context.user_data.clear()

    await update.message.reply_text(
        "🚀 ARZON OL BOT\n\n"
        "📱 Arzon raqamlar\n"
        "⭐ Telegram Stars\n"
        "📈 Telegram xizmatlari\n"
        "💳 Balans to'ldirish\n"
        "🎁 Kunlik bonus\n"
        "👥 Referal bonus\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=main_menu()
    )


# =========================================================
# BALANS
# =========================================================

async def balance_page(update, context):
    uid = update.effective_user.id

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT balance, referrals
        FROM users
        WHERE user_id=?
    """, (uid,))

    row = cur.fetchone()

    con.close()

    bal = row[0] if row else 0
    refs = row[1] if row else 0

    await update.message.reply_text(
        "💳 BALANS\n\n"
        f"💰 Balans: {bal:,} so'm\n"
        f"👥 Referallar: {refs} ta\n\n"
        f"⭐ 1 Stars = {STARS_PRICE:,} so'm\n"
        f"➕ Minimal to'lov = {MIN_TOPUP:,} so'm",
        reply_markup=main_menu()
    )


# =========================================================
# STARS
# =========================================================

async def stars_page(update, context):
    context.user_data["state"] = "stars"

    await update.message.reply_text(
        "⭐ STARS SOTIB OLISH\n\n"
        f"💰 1 Stars = {STARS_PRICE:,} so'm\n\n"
        "Qancha Stars kerakligini yozing.\n\n"
        "Masalan:\n"
        "50",
        reply_markup=back_keyboard()
    )


# =========================================================
# RAQAMLAR
# =========================================================

async def numbers_page(update, context):
    buttons = []

    for country, flag, price in NUMBERS:
        buttons.append([
            InlineKeyboardButton(
                f"{flag} {country} — {int(price):,} so'm",
                callback_data=f"country|{country}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Orqaga",
            callback_data="home"
        )
    ])

    await update.message.reply_text(
        "📱 ARZON RAQAMLAR\n\n"
        "Kerakli davlatni tanlang 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def country_page(update, context):
    query = update.callback_query
    await query.answer()

    country = query.data.split("|", 1)[1]

    selected = None

    for item in NUMBERS:
        if item[0] == country:
            selected = item
            break

    if not selected:
        await query.edit_message_text(
            "❌ Davlat topilmadi."
        )
        return

    country, flag, price = selected

    await query.edit_message_text(
        f"{flag} {country}\n\n"
        f"💰 Narxi: {int(price):,} so'm\n\n"
        "📦 Raqam mavjud.\n"
        "Raqamni sotib olish uchun tasdiqlang.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Sotib olish",
                    callback_data=f"buy_number|{country}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="numbers"
                )
            ]
        ])
    )


async def buy_number(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id

    country = query.data.split("|", 1)[1]

    selected = None

    for item in NUMBERS:
        if item[0] == country:
            selected = item
            break

    if not selected:
        await query.edit_message_text(
            "❌ Davlat topilmadi."
        )
        return

    country, flag, price = selected
    price = int(price)

    balance = get_balance(uid)

    if balance < price:
        await query.edit_message_text(
            f"❌ Balansingiz yetarli emas.\n\n"
            f"💰 Kerak: {price:,} so'm\n"
            f"💳 Balans: {balance:,} so'm\n\n"
            f"➕ Minimal to'lov: {MIN_TOPUP:,} so'm",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "➕ Pul to'ldirish",
                        callback_data="topup"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Orqaga",
                        callback_data="numbers"
                    )
                ]
            ])
        )
        return

    if not remove_balance(uid, price):
        await query.edit_message_text(
            "❌ Balansdan pul yechishda xatolik."
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO orders
        (user_id, service, target, quantity, amount, status, created_at)
        VALUES (?, ?, '', 1, ?, 'paid', ?)
    """, (
        uid,
        f"📱 {country} raqam",
        price,
        datetime.now().isoformat()
    ))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    await query.edit_message_text(
        "✅ BUYURTMA QABUL QILINDI!\n\n"
        f"🌍 Davlat: {flag} {country}\n"
        f"💰 To'lov: {price:,} so'm\n"
        f"🆔 Buyurtma: #{order_id}\n\n"
        "📞 Raqam admin tomonidan beriladi.\n"
        "⏳ Iltimos, kuting."
    )

    await context.bot.send_message(
        ADMIN_ID,
        "📱 YANGI RAQAM BUYURTMASI\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"👤 User ID: {uid}\n"
        f"🌍 Davlat: {flag} {country}\n"
        f"💰 Summa: {price:,} so'm\n\n"
        "📌 Raqamni foydalanuvchiga o'zingiz yuboring."
    )


# =========================================================
# PUL TO'LDIRISH
# =========================================================

async def topup_page(update, context):
    context.user_data["state"] = "topup_amount"

    await update.message.reply_text(
        "💳 HISOB TO'LDIRISH\n\n"
        f"💰 Minimal summa: {MIN_TOPUP:,} so'm\n\n"
        f"💳 Karta:\n"
        f"{PAYMENT_CARD}\n\n"
        f"👤 Karta egasi:\n"
        f"{PAYMENT_OWNER}\n\n"
        "Avval qancha to'lov qilmoqchi ekaningizni yozing.\n\n"
        "Masalan: 10000",
        reply_markup=back_keyboard()
    )


async def process_topup_amount(update, context):
    text = update.message.text.strip()

    try:
        amount = int(
            text.replace(" ", "")
                .replace(",", "")
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Summani faqat raqam bilan yozing.\n\n"
            "Masalan: 10000"
        )
        return

    if amount < MIN_TOPUP:
        await update.message.reply_text(
            f"❌ Minimal to'lov {MIN_TOPUP:,} so'm."
        )
        return

    context.user_data["payment_amount"] = amount
    context.user_data["state"] = "payment_done"

    await update.message.reply_text(
        "💳 TO'LOV QILISH\n\n"
        f"💰 Summa: {amount:,} so'm\n\n"
        f"💳 Karta:\n"
        f"{PAYMENT_CARD}\n\n"
        f"👤 Karta egasi:\n"
        f"{PAYMENT_OWNER}\n\n"
        "1️⃣ Yuqoridagi kartaga to'lov qiling.\n"
        "2️⃣ To'lov qilganingizdan keyin tugmani bosing.\n"
        "3️⃣ Keyin chek yoki skrinshot yuboring.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💸 PAGA TO'LOV QILDIM",
                    callback_data="payment_done"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# PAGA TO'LOV QILDIM
# =========================================================

async def payment_done_button(update, context):
    query = update.callback_query
    await query.answer()

    amount = context.user_data.get("payment_amount")

    if not amount:
        await query.message.reply_text(
            "❌ Avval 💳 Pul to'ldirish bo'limidan "
            "summani kiriting."
        )
        return

    context.user_data["state"] = "receipt"

    await query.message.reply_text(
        "📸 CHEK / SKRINSHOT YUBORISH\n\n"
        "To'lovni amalga oshirganingizni tasdiqlovchi "
        "chek yoki skrinshotni shu chatga yuboring.\n\n"
        f"💰 To'lov summasi: {amount:,} so'm\n\n"
        "📌 Chek admin'ga avtomatik yuboriladi."
    )


# =========================================================
# CHEK RASMI
# =========================================================

async def receive_receipt(update, context):
    uid = update.effective_user.id

    amount = context.user_data.get("payment_amount")

    if not amount:
        await update.message.reply_text(
            "❌ Avval 💳 Pul to'ldirish bo'limiga kiring "
            "va summani kiriting."
        )
        return

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Iltimos, chek yoki skrinshotni "
            "RASM ko'rinishida yuboring."
        )
        return

    file_id = update.message.photo[-1].file_id

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO payments
        (user_id, amount, receipt_file_id, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
    """, (
        uid,
        amount,
        file_id,
        datetime.now().isoformat()
    ))

    payment_id = cur.lastrowid

    con.commit()
    con.close()

    username = update.effective_user.username

    if username:
        username_text = f"@{username}"
    else:
        username_text = "username yo'q"

    context.user_data.pop("payment_amount", None)
    context.user_data.pop("state", None)

    await update.message.reply_text(
        "✅ CHEK QABUL QILINDI!\n\n"
        f"💰 Summa: {amount:,} so'm\n"
        f"🧾 To'lov: #{payment_id}\n\n"
        "⏳ Admin chekni tekshiradi.\n"
        "Tasdiqlangandan keyin balansingizga pul tushadi.",
        reply_markup=main_menu()
    )

    # ADMIN'GA RASM + MA'LUMOT
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=(
            "💳 YANGI TO'LOV CHEKI\n\n"
            f"🧾 To'lov: #{payment_id}\n"
            f"👤 User ID: {uid}\n"
            f"🔗 Username: {username_text}\n"
            f"💰 Summa: {amount:,} so'm\n\n"
            "👇 Tekshiring:"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ TASDIQLASH",
                    callback_data=f"approve|{payment_id}"
                ),
                InlineKeyboardButton(
                    "❌ RAD ETISH",
                    callback_data=f"reject|{payment_id}"
                )
            ]
        ])
    )


# =========================================================
# ADMIN TO'LOV TASDIQLASH
# =========================================================

async def approve_payment(update, context):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Siz admin emassiz.",
            show_alert=True
        )
        return

    await query.answer()

    try:
        payment_id = int(
            query.data.split("|", 1)[1]
        )
    except (ValueError, IndexError):
        await query.answer(
            "❌ To'lov ID xato.",
            show_alert=True
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM payments
        WHERE id=?
    """, (payment_id,))

    row = cur.fetchone()

    if not row:
        con.close()

        try:
            await query.edit_message_caption(
                caption="❌ To'lov topilmadi."
            )
        except Exception:
            pass

        return

    uid, amount, status = row

    if status != "pending":
        con.close()

        await query.answer(
            "⚠️ Bu to'lov allaqachon ko'rilgan.",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE payments
        SET status='approved'
        WHERE id=?
    """, (payment_id,))

    cur.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
    """, (
        amount,
        uid
    ))

    con.commit()
    con.close()

    try:
        await query.edit_message_caption(
            caption=(
                "✅ TO'LOV TASDIQLANDI\n\n"
                f"🧾 #{payment_id}\n"
                f"👤 User: {uid}\n"
                f"💰 +{amount:,} so'm"
            )
        )
    except Exception:
        pass

    await context.bot.send_message(
        uid,
        "✅ TO'LOV TASDIQLANDI!\n\n"
        f"💰 +{amount:,} so'm balansingizga tushdi.\n"
        f"💳 Yangi balans: {get_balance(uid):,} so'm",
        reply_markup=main_menu()
    )


# =========================================================
# ADMIN TO'LOV RAD ETISH
# =========================================================

async def reject_payment(update, context):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Siz admin emassiz.",
            show_alert=True
        )
        return

    await query.answer()

    try:
        payment_id = int(
            query.data.split("|", 1)[1]
        )
    except (ValueError, IndexError):
        await query.answer(
            "❌ To'lov ID xato.",
            show_alert=True
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM payments
        WHERE id=?
    """, (payment_id,))

    row = cur.fetchone()

    if not row:
        con.close()

        try:
            await query.edit_message_caption(
                caption="❌ To'lov topilmadi."
            )
        except Exception:
            pass

        return

    uid, amount, status = row

    if status != "pending":
        con.close()

        await query.answer(
            "⚠️ Bu to'lov allaqachon ko'rilgan.",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE payments
        SET status='rejected'
        WHERE id=?
    """, (payment_id,))

    con.commit()
    con.close()

    try:
        await query.edit_message_caption(
            caption=(
                "❌ TO'LOV RAD ETILDI\n\n"
                f"🧾 #{payment_id}\n"
                f"👤 User: {uid}\n"
                f"💰 Summa: {amount:,} so'm"
            )
        )
    except Exception:
        pass

    await context.bot.send_message(
        uid,
        "❌ TO'LOVINGIZ RAD ETILDI.\n\n"
        f"🧾 To'lov: #{payment_id}\n"
        f"💰 Summa: {amount:,} so'm\n\n"
        "Agar xatolik bo'lsa, admin bilan bog'laning.",
        reply_markup=main_menu()
    )


# =========================================================
# KUNLIK BONUS
# =========================================================

async def daily_bonus(update, context):
    uid = update.effective_user.id

    today = str(date.today())

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT daily_date
        FROM users
        WHERE user_id=?
    """, (uid,))

    row = cur.fetchone()

    if row and row[0] == today:
        con.close()

        await update.message.reply_text(
            "🎁 Bugungi bonusni allaqachon olgansiz.\n\n"
            "⏳ Ertaga yana olishingiz mumkin."
        )
        return

    cur.execute("""
        UPDATE users
        SET balance = balance + ?,
            daily_date = ?
        WHERE user_id=?
    """, (
        DAILY_BONUS,
        today,
        uid
    ))

    con.commit()
    con.close()

    await update.message.reply_text(
        "🎁 KUNLIK BONUS\n\n"
        f"✅ +{DAILY_BONUS:,} so'm balansingizga tushdi!\n\n"
        f"💳 Balans: {get_balance(uid):,} so'm",
        reply_markup=main_menu()
    )


# =========================================================
# REFERAL
# =========================================================

async def referral_page(update, context):
    uid = update.effective_user.id

    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={uid}"

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT referrals FROM users WHERE user_id=?",
        (uid,)
    )

    row = cur.fetchone()

    con.close()

    refs = row[0] if row else 0

    await update.message.reply_text(
        "👥 REFERAL\n\n"
        f"👤 Referallar: {refs} ta\n"
        f"💰 Har bir referal: +{REFERRAL_BONUS:,} so'm\n\n"
        "🔗 Sizning referal havolangiz:\n"
        f"{link}",
        reply_markup=main_menu()
    )


# =========================================================
# NAKRUTKA
# =========================================================

async def nakrutka_page(update, context):
    await update.message.reply_text(
        "📈 TELEGRAM XIZMATLARI\n\n"
        "👇 Xizmatni tanlang:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "👥 Obunachi",
                    callback_data="followers"
                )
            ],
            [
                InlineKeyboardButton(
                    "❤️ Reaksiya",
                    callback_data="reactions"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="home"
                )
            ]
        ])
    )


async def followers_page(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "followers"

    await query.edit_message_text(
        "👥 TELEGRAM OBUNACHI\n\n"
        "💰 100 ta = 2,000 so'm\n"
        "📦 Maksimum = 100,000 ta\n\n"
        "Link va miqdorni yuboring.\n\n"
        "Masalan:\n"
        "https://t.me/kanal 100"
    )


async def reactions_page(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "reactions"

    await query.edit_message_text(
        "❤️ TELEGRAM REAKSIYA\n\n"
        "💰 1 ta = 100 so'm\n"
        "🔢 Minimum = 10 ta\n"
        "📦 Maksimum = 1,000 ta\n\n"
        "Post linki va miqdorni yuboring.\n\n"
        "Masalan:\n"
        "https://t.me/kanal/123 10"
    )


async def create_service_order(update, context):
    uid = update.effective_user.id
    state = context.user_data.get("state")

    parts = update.message.text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ Format noto'g'ri.\n\n"
            "Masalan:\n"
            "https://t.me/kanal 100"
        )
        return

    target = parts[0]

    try:
        quantity = int(parts[1])
    except ValueError:
        await update.message.reply_text(
            "❌ Miqdor raqam bo'lishi kerak."
        )
        return

    if state == "followers":

        if quantity < 1 or quantity > MAX_FOLLOWERS:
            await update.message.reply_text(
                f"❌ Maksimum {MAX_FOLLOWERS:,} ta."
            )
            return

        amount = quantity * FOLLOWER_100_PRICE // 100
        service = "👥 Telegram obunachi"

    elif state == "reactions":

        if quantity < MIN_REACTIONS:
            await update.message.reply_text(
                f"❌ Minimum {MIN_REACTIONS} ta."
            )
            return

        if quantity > MAX_REACTIONS:
            await update.message.reply_text(
                f"❌ Maksimum {MAX_REACTIONS:,} ta."
            )
            return

        amount = quantity * REACTION_PRICE
        service = "❤️ Telegram reaksiya"

    else:
        return

    balance = get_balance(uid)

    if balance < amount:
        await update.message.reply_text(
            "❌ Balansingiz yetarli emas.\n\n"
            f"💰 Buyurtma: {amount:,} so'm\n"
            f"💳 Balans: {balance:,} so'm\n\n"
            "Avval hisobingizni to'ldiring.",
            reply_markup=main_menu()
        )
        return

    if not remove_balance(uid, amount):
        await update.message.reply_text(
            "❌ Balansdan pul yechishda xatolik."
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO orders
        (user_id, service, target, quantity, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'paid', ?)
    """, (
        uid,
        service,
        target,
        quantity,
        amount,
        datetime.now().isoformat()
    ))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ BUYURTMA QABUL QILINDI!\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"📌 Xizmat: {service}\n"
        f"🔢 Miqdor: {quantity:,}\n"
        f"💰 Narx: {amount:,} so'm\n"
        f"🔗 Link: {target}\n\n"
        "⏳ Buyurtma tekshirilmoqda.",
        reply_markup=main_menu()
    )

    await context.bot.send_message(
        ADMIN_ID,
        "📈 YANGI NAKRUTKA BUYURTMASI\n\n"
        f"🆔 #{order_id}\n"
        f"👤 User ID: {uid}\n"
        f"📌 {service}\n"
        f"🔢 {quantity:,}\n"
        f"💰 {amount:,} so'm\n"
        f"🔗 {target}"
    )


# =========================================================
# BUYURTMALAR
# =========================================================

async def orders_page(update, context):
    uid = update.effective_user.id

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT id, service, quantity, amount, status
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (uid,))

    rows = cur.fetchall()

    con.close()

    if not rows:
        await update.message.reply_text(
            "📦 Sizda hali buyurtmalar yo'q.",
            reply_markup=main_menu()
        )
        return

    text = "📦 BUYURTMALARIM\n\n"

    for oid, service, quantity, amount, status in rows:
        text += (
            f"🆔 #{oid}\n"
            f"📌 {service}\n"
            f"🔢 {quantity:,}\n"
            f"💰 {amount:,} so'm\n"
            f"📍 {status}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    con = connect()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM payments WHERE status='pending'"
    )
    pending = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM orders WHERE status='paid'"
    )
    orders = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(balance),0) FROM users"
    )
    total_balance = cur.fetchone()[0]

    con.close()

    await update.message.reply_text(
        "👑 ADMIN PANEL\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"💳 Kutilayotgan to'lovlar: {pending}\n"
        f"📦 Buyurtmalar: {orders}\n"
        f"💰 Umumiy balans: {total_balance:,} so'm\n\n"
        "📊 Batafsil:\n"
        "/stats\n\n"
        "📢 Broadcast:\n"
        "/broadcast xabar"
    )


# =========================================================
# STATISTIKA
# =========================================================

async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    con = connect()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(balance),0)
        FROM users
    """)
    balances = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM payments
        WHERE status='approved'
    """)
    payments = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
    """)
    order_count = cur.fetchone()[0]

    con.close()

    await update.message.reply_text(
        "📊 STATISTIKA\n\n"
        f"👥 Users: {users}\n"
        f"💰 Balanslar jami: {balances:,} so'm\n"
        f"💳 Tasdiqlangan to'lovlar: {payments:,} so'm\n"
        f"📦 Buyurtmalar: {order_count}"
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "Format:\n"
            "/broadcast Salom hammaga!"
        )
        return

    message = " ".join(context.args)

    con = connect()
    cur = con.cursor()

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    con.close()

    sent = 0

    for row in users:
        uid = row[0]

        try:
            await context.bot.send_message(
                uid,
                message
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(
        "📢 Broadcast tugadi.\n\n"
        f"✅ Yuborildi: {sent} ta"
    )


# =========================================================
# YORDAM
# =========================================================

async def help_page(update, context):
    await update.message.reply_text(
        "ℹ️ YORDAM\n\n"
        "📱 Nomer olish — davlat tanlab buyurtma berish.\n"
        "⭐ Stars olish — Stars miqdorini kiritish.\n"
        "📈 Nakrutka — obunachi va reaksiya buyurtmalari.\n"
        "➕ Pul to'ldirish — karta orqali balans to'ldirish.\n"
        "🎁 Kunlik bonus — har kuni bonus.\n"
        "👥 Referal — do'st taklif qilib bonus olish.\n"
        "📦 Buyurtmalar — buyurtmalar tarixini ko'rish.",
        reply_markup=main_menu()
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update, context):
    text = update.message.text
    uid = update.effective_user.id

    ensure_user(
        uid,
        update.effective_user.username
    )

    state = context.user_data.get("state")

    # ASOSIY MENU
    if text == "📱 Nomer olish":
        context.user_data.clear()
        await numbers_page(update, context)
        return

    if text == "⭐ Stars olish":
        context.user_data.clear()
        await stars_page(update, context)
        return

    if text == "📈 Nakrutka":
        context.user_data.clear()
        await nakrutka_page(update, context)
        return

    if text == "💳 Balans":
        context.user_data.clear()
        await balance_page(update, context)
        return

    if text == "➕ Pul to'ldirish":
        context.user_data.clear()
        await topup_page(update, context)
        return

    if text == "🎁 Kunlik bonus":
        context.user_data.clear()
        await daily_bonus(update, context)
        return

    if text == "👥 Referal":
        context.user_data.clear()
        await referral_page(update, context)
        return

    if text == "📦 Buyurtmalar":
        context.user_data.clear()
        await orders_page(update, context)
        return

    if text == "ℹ️ Yordam":
        context.user_data.clear()
        await help_page(update, context)
        return

    # TOPUP SUMMA
    if state == "topup_amount":
        await process_topup_amount(update, context)
        return

    # CHEK KUTILAYAPTI
    if state == "receipt":
        await update.message.reply_text(
            "📸 Iltimos, to'lov chekini/skrinshotini "
            "RASM qilib yuboring."
        )
        return

    # PAYMENT DONE HOLATI
    if state == "payment_done":
        await update.message.reply_text(
            "👇 Avval to'lovni amalga oshiring, "
            "keyin \"💸 PAGA TO'LOV QILDIM\" tugmasini bosing."
        )
        return

    # STARS
    if state == "stars":

        try:
            quantity = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Stars miqdorini raqam bilan yozing."
            )
            return

        if quantity <= 0:
            await update.message.reply_text(
                "❌ Miqdor noto'g'ri."
            )
            return

        amount = quantity * STARS_PRICE
        balance = get_balance(uid)

        if balance < amount:
            await update.message.reply_text(
                "❌ Balansingiz yetarli emas.\n\n"
                f"⭐ Stars: {quantity:,}\n"
                f"💰 Narx: {amount:,} so'm\n"
                f"💳 Balans: {balance:,} so'm",
                reply_markup=main_menu()
            )
            return

        if not remove_balance(uid, amount):
            await update.message.reply_text(
                "❌ Balansdan pul yechishda xatolik."
            )
            return

        con = connect()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO orders
            (user_id, service, target, quantity, amount, status, created_at)
            VALUES (?, '⭐ Telegram Stars', '', ?, ?, 'paid', ?)
        """, (
            uid,
            quantity,
            amount,
            datetime.now().isoformat()
        ))

        order_id = cur.lastrowid

        con.commit()
        con.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ STARS BUYURTMASI QABUL QILINDI!\n\n"
            f"🆔 #{order_id}\n"
            f"⭐ Stars: {quantity:,}\n"
            f"💰 To'lov: {amount:,} so'm\n\n"
            "⏳ Buyurtma admin tomonidan bajariladi.",
            reply_markup=main_menu()
        )

        await context.bot.send_message(
            ADMIN_ID,
            "⭐ YANGI STARS BUYURTMASI\n\n"
            f"🆔 #{order_id}\n"
            f"👤 User ID: {uid}\n"
            f"⭐ Miqdor: {quantity:,}\n"
            f"💰 Summa: {amount:,} so'm"
        )

        return

    # NAKRUTKA
    if state in ("followers", "reactions"):
        await create_service_order(update, context)
        return


# =========================================================
# CALLBACK
# =========================================================

async def callback_handler(update, context):
    query = update.callback_query
    data = query.data

    # HOME
    if data == "home":
        await query.answer()

        context.user_data.clear()

        await query.message.reply_text(
            "🏠 Asosiy menyu",
            reply_markup=main_menu()
        )
        return

    # NUMBERS
    if data == "numbers":
        await query.answer()

        buttons = []

        for country, flag, price in NUMBERS:
            buttons.append([
                InlineKeyboardButton(
                    f"{flag} {country} — {int(price):,} so'm",
                    callback_data=f"country|{country}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="home"
            )
        ])

        await query.edit_message_text(
            "📱 ARZON RAQAMLAR\n\n"
            "Davlatni tanlang:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # COUNTRY
    if data.startswith("country|"):
        await country_page(update, context)
        return

    # BUY NUMBER
    if data.startswith("buy_number|"):
        await buy_number(update, context)
        return

    # TOPUP
    if data == "topup":
        await query.answer()

        context.user_data["state"] = "topup_amount"

        await query.message.reply_text(
            "💳 HISOB TO'LDIRISH\n\n"
            f"💰 Minimal summa: {MIN_TOPUP:,} so'm\n\n"
            f"💳 Karta:\n{PAYMENT_CARD}\n\n"
            f"👤 Karta egasi:\n{PAYMENT_OWNER}\n\n"
            "Summani yozing.\n\n"
            "Masalan: 10000",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Orqaga",
                        callback_data="home"
                    )
                ]
            ])
        )
        return

    # PAGA TO'LOV QILDIM
    if data == "payment_done":
        await payment_done_button(update, context)
        return

    # ESKI CHEK CALLBACK
    if data == "send_receipt":
        await payment_done_button(update, context)
        return

    # FOLLOWERS
    if data == "followers":
        await followers_page(update, context)
        return

    # REACTIONS
    if data == "reactions":
        await reactions_page(update, context)
        return

    # APPROVE
    if data.startswith("approve|"):
        await approve_payment(update, context)
        return

    # REJECT
    if data.startswith("reject|"):
        await reject_payment(update, context)
        return

    await query.answer()


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN GitHub Secretsda mavjud emas."
        )

    if not ADMIN_ID:
        raise RuntimeError(
            "ADMIN_ID GitHub Secretsda mavjud emas."
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # START
    app.add_handler(
        CommandHandler("start", start)
    )

    # ADMIN
    app.add_handler(
        CommandHandler("admin", admin_panel)
    )

    app.add_handler(
        CommandHandler("stats", stats)
    )

    app.add_handler(
        CommandHandler("broadcast", broadcast)
    )

    # CALLBACK
    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # =====================================================
    # CHEK RASMLARI
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_receipt
        )
    )

    # =====================================================
    # TEXT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("========================================")
    print("🚀 ARZON OL BOT ISHLAYAPTI")
    print("💳 PAYMENT SYSTEM: ACTIVE")
    print("📸 RECEIPT SYSTEM: ACTIVE")
    print("👑 ADMIN SYSTEM: ACTIVE")
    print("========================================")

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    main()
