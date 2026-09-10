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
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB = "arzonol.db"

CARD_NUMBER = "9860080390168864"
CARD_NAME = "RAKHMONVA O"

STAR_PRICE = 205

REFERRAL_BONUS = 100
DAILY_BONUS = 50

# =========================================================
# NOMER DAVLATLARI
# =========================================================

COUNTRIES = {
    "bangladesh": {
        "name": "🇧🇩 Bangladesh",
        "price": 8999,
        "stock": 234,
    },
    "colombia": {
        "name": "🇨🇴 Colombia",
        "price": 7890,
        "stock": 5,
    },
    "india": {
        "name": "🇮🇳 India",
        "price": 7999,
        "stock": 625,
    },
    "niger": {
        "name": "🇳🇪 Niger",
        "price": 9676,
        "stock": 3,
    },
    "usa": {
        "name": "🇺🇸 United States",
        "price": 9476,
        "stock": 2,
    },
    "ethiopia": {
        "name": "🇪🇹 Ethiopia",
        "price": 8999,
        "stock": 124,
    },
    "myanmar": {
        "name": "🇲🇲 Myanmar",
        "price": 7999,
        "stock": 669,
    },
    "canada": {
        "name": "🇨🇦 Canada",
        "price": 7999,
        "stock": 129,
    },
    "philippines": {
        "name": "🇵🇭 Philippines",
        "price": 10000,
        "stock": 477,
    },
    "afghanistan": {
        "name": "🇦🇫 Afghanistan",
        "price": 9999,
        "stock": 117,
    },
}

# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            daily_date TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            sold INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            country TEXT,
            phone TEXT,
            price INTEGER,
            status TEXT DEFAULT 'pending',
            created TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stars_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stars INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created TEXT
        )
    """)

    con.commit()
    con.close()


# =========================================================
# USER
# =========================================================

def add_user(user_id, username, first_name, ref_id=0):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    exists = cur.fetchone()

    if not exists:
        cur.execute("""
            INSERT INTO users
            (user_id, username, first_name, balance, referrals, referred_by, daily_date)
            VALUES (?, ?, ?, 0, 0, ?, '')
        """, (
            user_id,
            username or "",
            first_name or "",
            ref_id if ref_id != user_id else 0,
        ))

        if ref_id and ref_id != user_id:
            cur.execute("""
                UPDATE users
                SET balance = balance + ?,
                    referrals = referrals + 1
                WHERE user_id=?
            """, (REFERRAL_BONUS, ref_id))

    else:
        cur.execute("""
            UPDATE users
            SET username=?, first_name=?
            WHERE user_id=?
        """, (
            username or "",
            first_name or "",
            user_id,
        ))

    con.commit()
    con.close()


def get_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, username, first_name, balance, referrals, referred_by, daily_date
        FROM users
        WHERE user_id=?
    """, (user_id,))

    row = cur.fetchone()

    con.close()
    return row


def change_balance(user_id, amount):
    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
    """, (amount, user_id))

    con.commit()
    con.close()


# =========================================================
# MENYU
# =========================================================

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📱 Nomer olish", "⭐ Stars sotib olish"],
            ["🛒 Buyurtmalarim", "💳 Hisobim"],
            ["💳 Hisob to‘ldirish", "💸 Pul ishlash"],
            ["📖 Qo‘llanma", "☎️ Qo‘llab-quvvatlash"],
        ],
        resize_keyboard=True,
    )


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back")]
    ])


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    ref_id = 0

    if context.args:
        try:
            ref_id = int(context.args[0])
        except:
            ref_id = 0

    add_user(
        user.id,
        user.username,
        user.first_name,
        ref_id,
    )

    text = (
        "🚀 <b>ARZON OL BOT</b>\n\n"
        "📱 Arzon raqamlar\n"
        "⭐ Telegram Stars\n"
        "💳 Tezkor balans to‘ldirish\n"
        "💸 Referral orqali bonus\n\n"
        "👇 Kerakli bo‘limni tanlang."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# NOMERLAR
# =========================================================

async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = []

    for key, data in COUNTRIES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{data['name']} — {data['price']:,} so‘m | 📦 {data['stock']}",
                callback_data=f"country:{key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Orqaga", callback_data="back")
    ])

    await update.message.reply_text(
        "🌍 <b>Mavjud davlatlar:</b>\n\n"
        "Kerakli davlatni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]

    if key not in COUNTRIES:
        return

    data = COUNTRIES[key]

    # Haqiqiy bazadagi mavjud raqamlarni hisoblash
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM numbers
        WHERE country=? AND sold=0
    """, (key,))

    real_stock = cur.fetchone()[0]
    con.close()

    # Agar admin hali raqamlarni kiritmagan bo‘lsa,
    # oldindan berilgan son ko‘rsatiladi.
    stock = real_stock if real_stock > 0 else data["stock"]

    text = (
        f"{data['name']}\n\n"
        f"💰 <b>Narxi:</b> {data['price']:,} so‘m\n"
        f"📦 <b>Mavjud:</b> {stock} dona\n\n"
        f"👇 Nomer olish uchun tugmani bosing."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "📱 Nomer olish",
                callback_data=f"buy_number:{key}"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="countries"
            )
        ],
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# NOMER SOTIB OLISH
# =========================================================

async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]

    if key not in COUNTRIES:
        return

    data = COUNTRIES[key]

    user = get_user(query.from_user.id)

    if not user:
        await query.message.reply_text("❌ Avval /start bosing.")
        return

    balance = user[3]

    # Avval real raqam bor-yo‘qligini tekshiramiz
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, phone
        FROM numbers
        WHERE country=? AND sold=0
        ORDER BY id ASC
        LIMIT 1
    """, (key,))

    number = cur.fetchone()

    con.close()

    if not number:
        await query.edit_message_text(
            f"{data['name']}\n\n"
            f"💰 Narxi: <b>{data['price']:,} so‘m</b>\n"
            f"📦 Hozircha raqam bazaga kiritilmagan yoki tugagan.\n\n"
            "☎️ Admin bilan bog‘laning.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="countries")]
            ]),
        )
        return

    if balance < data["price"]:
        await query.edit_message_text(
            f"❌ <b>Balansingiz yetarli emas.</b>\n\n"
            f"💰 Nomer narxi: {data['price']:,} so‘m\n"
            f"💳 Balansingiz: {balance:,} so‘m\n"
            f"➖ Yetishmayapti: {data['price'] - balance:,} so‘m\n\n"
            "💳 Avval hisobingizni to‘ldiring.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 Hisob to‘ldirish",
                        callback_data="deposit"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Orqaga",
                        callback_data="countries"
                    )
                ]
            ]),
        )
        return

    context.user_data["pending_number_country"] = key

    await query.edit_message_text(
        f"📱 <b>{data['name']}</b>\n\n"
        f"💰 Narxi: <b>{data['price']:,} so‘m</b>\n"
        f"💳 Balansingiz: <b>{balance:,} so‘m</b>\n\n"
        "⚠️ Xaridni tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Tasdiqlash",
                    callback_data=f"confirm_number:{key}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Bekor qilish",
                    callback_data="countries"
                )
            ]
        ]),
    )


async def confirm_number(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]

    if key not in COUNTRIES:
        return

    data = COUNTRIES[key]
    user_id = query.from_user.id

    con = db()
    cur = con.cursor()

    # Raqamni band qilamiz
    cur.execute("""
        SELECT id, phone
        FROM numbers
        WHERE country=? AND sold=0
        ORDER BY id ASC
        LIMIT 1
    """, (key,))

    number = cur.fetchone()

    if not number:
        con.close()

        await query.edit_message_text(
            "❌ Bu davlatdagi raqamlar tugagan.",
            reply_markup=back_button(),
        )
        return

    number_id, phone = number

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cur.fetchone()

    if not row or row[0] < data["price"]:
        con.close()

        await query.edit_message_text(
            "❌ Balansingiz yetarli emas.",
            reply_markup=back_button(),
        )
        return

    # Pul yechiladi
    cur.execute("""
        UPDATE users
        SET balance = balance - ?
        WHERE user_id=?
    """, (data["price"], user_id))

    # Raqam sotildi
    cur.execute("""
        UPDATE numbers
        SET sold=1
        WHERE id=?
    """, (number_id,))

    cur.execute("""
        INSERT INTO orders
        (user_id, country, phone, price, status, created)
        VALUES (?, ?, ?, ?, 'completed', ?)
    """, (
        user_id,
        key,
        phone,
        data["price"],
        datetime.now().isoformat(),
    ))

    con.commit()
    con.close()

    new_balance = row[0] - data["price"]

    await query.edit_message_text(
        f"✅ <b>Nomer muvaffaqiyatli olindi!</b>\n\n"
        f"🌍 Davlat: {data['name']}\n"
        f"📱 Nomer: <code>{phone}</code>\n"
        f"💰 To‘lov: {data['price']:,} so‘m\n"
        f"💳 Qolgan balans: {new_balance:,} so‘m",
        parse_mode="HTML",
        reply_markup=back_button(),
    )

    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"📱 <b>NOMER SOTILDI</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"🌍 {data['name']}\n"
            f"📱 <code>{phone}</code>\n"
            f"💰 {data['price']:,} so‘m",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(e)


# =========================================================
# STARS
# =========================================================

async def stars_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"⭐ <b>Stars sotib olish</b>\n\n"
        f"⭐ 1 Stars = <b>{STAR_PRICE} so‘m</b>\n\n"
        "👇 Nechta Stars kerakligini yozing.\n"
        "Masalan: <code>50</code>",
        parse_mode="HTML",
        reply_markup=back_button(),
    )

    context.user_data["waiting_stars"] = True


async def process_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_stars"):
        return

    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ Faqat raqam yozing.\n\nMasalan: 50"
        )
        return

    stars = int(text)

    if stars <= 0:
        await update.message.reply_text("❌ Miqdor noto‘g‘ri.")
        return

    amount = stars * STAR_PRICE

    user = get_user(update.effective_user.id)

    if not user or user[3] < amount:
        balance = user[3] if user else 0

        await update.message.reply_text(
            f"❌ Balansingiz yetarli emas.\n\n"
            f"⭐ Stars: {stars}\n"
            f"💰 Kerak: {amount:,} so‘m\n"
            f"💳 Balans: {balance:,} so‘m"
        )

        context.user_data["waiting_stars"] = False
        return

    context.user_data["waiting_stars"] = False
    context.user_data["pending_stars"] = stars
    context.user_data["pending_stars_amount"] = amount

    await update.message.reply_text(
        f"⭐ <b>Buyurtmani tasdiqlash</b>\n\n"
        f"⭐ Stars: <b>{stars}</b>\n"
        f"💰 Narxi: <b>{amount:,} so‘m</b>\n"
        f"💳 Balansingiz: <b>{user[3]:,} so‘m</b>\n\n"
        "Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Tasdiqlash",
                    callback_data="confirm_stars"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Bekor qilish",
                    callback_data="back"
                )
            ]
        ]),
    )


async def confirm_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    stars = context.user_data.get("pending_stars")
    amount = context.user_data.get("pending_stars_amount")

    if not stars or not amount:
        await query.edit_message_text(
            "❌ Buyurtma topilmadi.",
            reply_markup=back_button(),
        )
        return

    user = get_user(user_id)

    if not user or user[3] < amount:
        await query.edit_message_text(
            "❌ Balansingiz yetarli emas.",
            reply_markup=back_button(),
        )
        return

    change_balance(user_id, -amount)

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO stars_orders
        (user_id, stars, amount, status, created)
        VALUES (?, ?, ?, 'pending', ?)
    """, (
        user_id,
        stars,
        amount,
        datetime.now().isoformat(),
    ))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.pop("pending_stars", None)
    context.user_data.pop("pending_stars_amount", None)

    new_balance = user[3] - amount

    await query.edit_message_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🧾 Buyurtma: #{order_id}\n"
        f"⭐ Stars: {stars}\n"
        f"💰 To‘lov: {amount:,} so‘m\n"
        f"💳 Qolgan balans: {new_balance:,} so‘m\n\n"
        "⏳ Admin tasdiqlashini kuting.",
        parse_mode="HTML",
        reply_markup=back_button(),
    )

    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"⭐ <b>YANGI STARS BUYURTMASI</b>\n\n"
            f"🧾 #{order_id}\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"⭐ Stars: {stars}\n"
            f"💰 Summa: {amount:,} so‘m",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(e)


# =========================================================
# HISOB
# =========================================================

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user.id)

    if not user:
        return

    await update.message.reply_text(
        f"💳 <b>Hisobingiz</b>\n\n"
        f"💰 Balans: <b>{user[3]:,} so‘m</b>\n"
        f"👥 Referallar: <b>{user[4]}</b>\n\n"
        f"🔗 Referral havolangiz:\n"
        f"<code>https://t.me/{context.bot.username}?start={user[0]}</code>",
        parse_mode="HTML",
    )


# =========================================================
# HISOB TO‘LDIRISH
# =========================================================

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["waiting_deposit"] = True

    await update.message.reply_text(
        "💳 <b>Hisob to‘ldirish</b>\n\n"
        f"💳 Karta:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 Karta egasi: <b>{CARD_NAME}</b>\n\n"
        "👇 Qancha pul to‘ldirmoqchi ekaningizni yozing.\n"
        "Masalan: <code>50000</code>",
        parse_mode="HTML",
        reply_markup=back_button(),
    )


async def process_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_deposit"):
        return False

    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ Summani raqam bilan yozing.\nMasalan: 50000"
        )
        return True

    amount = int(text)

    if amount < 1000:
        await update.message.reply_text(
            "❌ Minimal to‘ldirish: 1 000 so‘m."
        )
        return True

    context.user_data["waiting_deposit"] = False
    context.user_data["deposit_amount"] = amount

    await update.message.reply_text(
        f"💳 <b>To‘lov ma’lumoti</b>\n\n"
        f"💰 Summa: <b>{amount:,} so‘m</b>\n\n"
        f"💳 Karta:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 {CARD_NAME}\n\n"
        "To‘lovni amalga oshirgandan keyin:\n"
        "📸 <b>Chek rasmini shu botga yuboring.</b>",
        parse_mode="HTML",
    )

    return True


# =========================================================
# CHEK QABUL QILISH
# =========================================================

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):

    amount = context.user_data.get("deposit_amount")

    if not amount:
        return False

    user_id = update.effective_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO deposits
        (user_id, amount, status, created)
        VALUES (?, ?, 'pending', ?)
    """, (
        user_id,
        amount,
        datetime.now().isoformat(),
    ))

    deposit_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.pop("deposit_amount", None)

    await update.message.reply_text(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        f"🧾 To‘lov: #{deposit_id}\n"
        f"💰 Summa: {amount:,} so‘m\n\n"
        "⏳ Admin tekshiruvini kuting.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    caption = (
        "💳 <b>YANGI TO‘LOV</b>\n\n"
        f"🧾 To‘lov: #{deposit_id}\n"
        f"👤 User ID: <code>{user_id}</code>\n"
        f"💰 Summa: <b>{amount:,} so‘m</b>\n\n"
        "Tasdiqlash:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data=f"approve_deposit:{deposit_id}"
            ),
            InlineKeyboardButton(
                "❌ Rad etish",
                callback_data=f"reject_deposit:{deposit_id}"
            )
        ]
    ])

    try:
        if update.message.photo:
            await context.bot.send_photo(
                ADMIN_ID,
                update.message.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        elif update.message.document:
            await context.bot.send_document(
                ADMIN_ID,
                update.message.document.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:
            await context.bot.send_message(
                ADMIN_ID,
                caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(e)

    return True


# =========================================================
# DEPOSIT ADMIN
# =========================================================

async def approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    deposit_id = int(query.data.split(":")[1])

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM deposits
        WHERE id=?
    """, (deposit_id,))

    row = cur.fetchone()

    if not row:
        con.close()
        await query.edit_message_caption("❌ To‘lov topilmadi.")
        return

    user_id, amount, status = row

    if status != "pending":
        con.close()
        await query.edit_message_caption(
            f"ℹ️ Bu to‘lov allaqachon: {status}"
        )
        return

    cur.execute("""
        UPDATE deposits
        SET status='approved'
        WHERE id=?
    """, (deposit_id,))

    cur.execute("""
        UPDATE users
        SET balance=balance+?
        WHERE user_id=?
    """, (amount, user_id))

    con.commit()
    con.close()

    await query.edit_message_caption(
        f"✅ <b>TASDIQLANDI</b>\n\n"
        f"🧾 #{deposit_id}\n"
        f"👤 {user_id}\n"
        f"💰 +{amount:,} so‘m",
        parse_mode="HTML",
    )

    await context.bot.send_message(
        user_id,
        f"✅ <b>To‘lovingiz tasdiqlandi!</b>\n\n"
        f"💰 Balansingizga +{amount:,} so‘m qo‘shildi.",
        parse_mode="HTML",
    )


async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    deposit_id = int(query.data.split(":")[1])

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM deposits
        WHERE id=?
    """, (deposit_id,))

    row = cur.fetchone()

    if not row:
        con.close()
        return

    user_id, amount, status = row

    if status != "pending":
        con.close()
        await query.edit_message_caption(
            f"ℹ️ Bu to‘lov allaqachon: {status}"
        )
        return

    cur.execute("""
        UPDATE deposits
        SET status='rejected'
        WHERE id=?
    """, (deposit_id,))

    con.commit()
    con.close()

    await query.edit_message_caption(
        f"❌ <b>RAD ETILDI</b>\n\n"
        f"🧾 #{deposit_id}\n"
        f"💰 {amount:,} so‘m",
        parse_mode="HTML",
    )

    await context.bot.send_message(
        user_id,
        "❌ To‘lov chekingiz rad etildi.\n"
        "☎️ Muammo bo‘lsa admin bilan bog‘laning.",
    )


# =========================================================
# PUL ISHLASH
# =========================================================

async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        f"💸 <b>Pul ishlash</b>\n\n"
        f"👥 Har bir referral: <b>+{REFERRAL_BONUS} so‘m</b>\n"
        f"🎁 Kunlik bonus: <b>+{DAILY_BONUS} so‘m</b>\n\n"
        f"👥 Sizning referallaringiz: <b>{user[4]}</b>\n\n"
        f"🔗 Referral havolangiz:\n"
        f"<code>https://t.me/{context.bot.username}?start={user[0]}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎁 Kunlik bonus",
                    callback_data="daily"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="back"
                )
            ]
        ]),
    )


async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    user = get_user(user_id)

    if not user:
        return

    today = date.today().isoformat()

    if user[6] == today:
        await query.edit_message_text(
            "⏳ Bugungi bonusni olib bo‘lgansiz.\n"
            "Ertaga yana olishingiz mumkin.",
            reply_markup=back_button(),
        )
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance=balance+?,
            daily_date=?
        WHERE user_id=?
    """, (
        DAILY_BONUS,
        today,
        user_id,
    ))

    con.commit()
    con.close()

    await query.edit_message_text(
        f"🎁 <b>KUNLIK BONUS</b>\n\n"
        f"✅ Balansingizga <b>+{DAILY_BONUS} so‘m</b> qo‘shildi!",
        parse_mode="HTML",
        reply_markup=back_button(),
    )


# =========================================================
# BUYURTMALAR
# =========================================================

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, country, phone, price, status, created
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))

    orders = cur.fetchall()

    cur.execute("""
        SELECT id, stars, amount, status
        FROM stars_orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))

    stars_orders = cur.fetchall()

    con.close()

    if not orders and not stars_orders:
        await update.message.reply_text(
            "🛒 Sizda hali buyurtmalar yo‘q.",
            reply_markup=main_menu(),
        )
        return

    text = "🛒 <b>Buyurtmalarim</b>\n\n"

    for order in orders:
        text += (
            f"📱 #{order[0]} — {order[1]}\n"
            f"💰 {order[3]:,} so‘m\n"
            f"📌 {order[4]}\n\n"
        )

    for order in stars_orders:
        text += (
            f"⭐ #{order[0]} — {order[1]} Stars\n"
            f"💰 {order[2]:,} so‘m\n"
            f"📌 {order[3]}\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# QO‘LLANMA
# =========================================================

async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📖 <b>Qo‘llanma</b>\n\n"
        "📱 <b>Nomer olish</b> — mavjud davlatlardan raqam tanlaysiz.\n\n"
        "⭐ <b>Stars sotib olish</b> — kerakli Stars miqdorini yozasiz.\n\n"
        "💳 <b>Hisob to‘ldirish</b> — kartaga to‘lov qilasiz va chek yuborasiz.\n\n"
        "💸 <b>Pul ishlash</b> — referral va kunlik bonus orqali balans yig‘asiz.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "☎️ <b>Qo‘llab-quvvatlash</b>\n\n"
        "Muammo bo‘lsa admin bilan bog‘laning.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="admin_stats"
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Nomer qo‘shish",
                callback_data="admin_add_number"
            )
        ],
        [
            InlineKeyboardButton(
                "📱 Nomerlar",
                callback_data="admin_numbers"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Balanslar",
                callback_data="admin_balances"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Stars buyurtmalar",
                callback_data="admin_stars"
            )
        ],
        [
            InlineKeyboardButton(
                "🛒 Nomer buyurtmalar",
                callback_data="admin_orders"
            )
        ],
    ]

    await update.message.reply_text(
        "🛠 <b>ADMIN PANEL</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    action = query.data

    if action == "admin_stats":

        con = db()
        cur = con.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM deposits
            WHERE status='pending'
        """)
        pending_deposits = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM stars_orders
            WHERE status='pending'
        """)
        pending_stars = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM orders
            WHERE status='completed'
        """)
        sold_numbers = cur.fetchone()[0]

        con.close()

        await query.edit_message_text(
            f"📊 <b>STATISTIKA</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{users}</b>\n"
            f"💳 Kutilayotgan to‘lovlar: <b>{pending_deposits}</b>\n"
            f"⭐ Kutilayotgan Stars: <b>{pending_stars}</b>\n"
            f"📱 Sotilgan nomerlar: <b>{sold_numbers}</b>",
            parse_mode="HTML",
            reply_markup=back_button(),
        )

    elif action == "admin_add_number":

        context.user_data["admin_add_number"] = True

        await query.edit_message_text(
            "📱 <b>Nomer qo‘shish</b>\n\n"
            "Format:\n"
            "<code>bangladesh 8801712345678</code>\n\n"
            "Davlat kodi emas, botdagi davlat nomidan foydalaning:\n\n"
            "bangladesh\n"
            "colombia\n"
            "india\n"
            "niger\n"
            "usa\n"
            "ethiopia\n"
            "myanmar\n"
            "canada\n"
            "philippines\n"
            "afghanistan",
            parse_mode="HTML",
            reply_markup=back_button(),
        )

    elif action == "admin_numbers":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT country, COUNT(*)
            FROM numbers
            WHERE sold=0
            GROUP BY country
        """)

        rows = cur.fetchall()
        con.close()

        text = "📱 <b>OMBORDAGI NOMERLAR</b>\n\n"

        if not rows:
            text += "Hozircha raqam kiritilmagan."
        else:
            for country, count in rows:
                country_name = COUNTRIES.get(
                    country,
                    {"name": country}
                )["name"]

                text += f"{country_name}: <b>{count}</b> dona\n"

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_button(),
        )

    elif action == "admin_balances":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT user_id, username, balance
            FROM users
            ORDER BY balance DESC
            LIMIT 20
        """)

        rows = cur.fetchall()
        con.close()

        text = "💰 <b>BALANSLAR</b>\n\n"

        for row in rows:
            username = f"@{row[1]}" if row[1] else "username yo‘q"

            text += (
                f"👤 {username}\n"
                f"🆔 <code>{row[0]}</code>\n"
                f"💰 {row[2]:,} so‘m\n\n"
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_button(),
        )

    elif action == "admin_stars":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT id, user_id, stars, amount, status
            FROM stars_orders
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cur.fetchall()
        con.close()

        text = "⭐ <b>STARS BUYURTMALAR</b>\n\n"

        if not rows:
            text += "Buyurtmalar yo‘q."

        for row in rows:
            text += (
                f"#{row[0]} | User: <code>{row[1]}</code>\n"
                f"⭐ {row[2]} Stars\n"
                f"💰 {row[3]:,} so‘m\n"
                f"📌 {row[4]}\n\n"
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_button(),
        )

    elif action == "admin_orders":

        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT id, user_id, country, phone, price, status
            FROM orders
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cur.fetchall()
        con.close()

        text = "🛒 <b>NOMER BUYURTMALAR</b>\n\n"

        if not rows:
            text += "Buyurtmalar yo‘q."

        for row in rows:
            text += (
                f"#{row[0]} | User: <code>{row[1]}</code>\n"
                f"🌍 {row[2]}\n"
                f"📱 {row[3]}\n"
                f"💰 {row[4]:,} so‘m\n"
                f"📌 {row[5]}\n\n"
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_button(),
        )


# =========================================================
# ADMIN NOMER QO‘SHISH
# =========================================================

async def admin_add_number_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return False

    if not context.user_data.get("admin_add_number"):
        return False

    parts = update.message.text.strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ Format noto‘g‘ri.\n\n"
            "Masalan:\n"
            "<code>bangladesh 8801712345678</code>",
            parse_mode="HTML",
        )
        return True

    country = parts[0].lower()
    phone = parts[1]

    if country not in COUNTRIES:
        await update.message.reply_text(
            "❌ Bunday davlat topilmadi."
        )
        return True

    con = db()
    cur = con.cursor()

    try:
        cur.execute("""
            INSERT INTO numbers
            (country, phone, sold)
            VALUES (?, ?, 0)
        """, (country, phone))

        con.commit()

        await update.message.reply_text(
            f"✅ Nomer qo‘shildi!\n\n"
            f"🌍 {COUNTRIES[country]['name']}\n"
            f"📱 <code>{phone}</code>",
            parse_mode="HTML",
        )

    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "❌ Bu nomer bazada allaqachon bor."
        )

    finally:
        con.close()

    context.user_data["admin_add_number"] = False

    return True


# =========================================================
# CALLBACK BACK
# =========================================================

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🚀 <b>ARZON OL BOT</b>\n\n"
        "👇 Kerakli bo‘limni tanlang.",
        parse_mode="HTML",
    )


# =========================================================
# TEXT HANDLER
# =========================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    # ADMIN NOMER QO‘SHISH
    if await admin_add_number_message(update, context):
        return

    # STARS
    if context.user_data.get("waiting_stars"):
        await process_stars(update, context)
        return

    # DEPOSIT AMOUNT
    if context.user_data.get("waiting_deposit"):
        await process_deposit_amount(update, context)
        return

    if text == "📱 Nomer olish":
        await show_countries(update, context)

    elif text == "⭐ Stars sotib olish":
        await stars_menu(update, context)

    elif text == "🛒 Buyurtmalarim":
        await my_orders(update, context)

    elif text == "💳 Hisobim":
        await account(update, context)

    elif text == "💳 Hisob to‘ldirish":
        await deposit(update, context)

    elif text == "💸 Pul ishlash":
        await earn(update, context)

    elif text == "📖 Qo‘llanma":
        await guide(update, context)

    elif text == "☎️ Qo‘llab-quvvatlash":
        await support(update, context)


# =========================================================
# PHOTO / DOCUMENT
# =========================================================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("deposit_amount"):
        await receive_receipt(update, context)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("deposit_amount"):
        await receive_receipt(update, context)


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    data = query.data

    if data == "countries":
        await query.answer()

        keyboard = []

        for key, item in COUNTRIES.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{item['name']} — {item['price']:,} so‘m | 📦 {item['stock']}",
                    callback_data=f"country:{key}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="back"
            )
        ])

        await query.edit_message_text(
            "🌍 <b>Mavjud davlatlar:</b>\n\n"
            "Kerakli davlatni tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("country:"):
        await country_callback(update, context)

    elif data.startswith("buy_number:"):
        await buy_number(update, context)

    elif data.startswith("confirm_number:"):
        await confirm_number(update, context)

    elif data == "confirm_stars":
        await confirm_stars(update, context)

    elif data == "deposit":
        await query.answer()
        context.user_data["waiting_deposit"] = True

        await query.edit_message_text(
            "💳 <b>Hisob to‘ldirish</b>\n\n"
            f"💳 Karta:\n<code>{CARD_NUMBER}</code>\n"
            f"👤 {CARD_NAME}\n\n"
            "Qancha to‘ldirmoqchi ekaningizni yozing.",
            parse_mode="HTML",
        )

    elif data == "daily":
        await daily_bonus(update, context)

    elif data == "back":
        await back_callback(update, context)

    elif data.startswith("approve_deposit:"):
        await approve_deposit(update, context)

    elif data.startswith("reject_deposit:"):
        await reject_deposit(update, context)

    elif data.startswith("admin_"):
        await admin_callback(update, context)


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi!")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(
        CallbackQueryHandler(callback_router)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    logger.info("ARZON OL BOT ishga tushdi.")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
