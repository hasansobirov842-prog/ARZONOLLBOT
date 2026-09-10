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

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB = "arzonol.db"

# Referal va bonus
REFERRAL_REWARD = 100
DAILY_BONUS = 50

# Stars narxi
# 1 Stars = 206 so'm
STARS_PRICE = 206

# Qo'llab-quvvatlash
SUPPORT_USERNAME = "@bookmeet"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# DATABASE
# =========================

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
            referrer_id INTEGER DEFAULT NULL,
            referrals INTEGER DEFAULT 0,
            last_bonus TEXT DEFAULT NULL,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            price INTEGER NOT NULL,
            sold INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_type TEXT,
            product TEXT,
            amount INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            amount INTEGER DEFAULT 0,
            used_by TEXT DEFAULT ''
        )
    """)

    con.commit()
    con.close()


def add_user(user, referrer_id=None):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,)
    )

    exists = cur.fetchone()

    if not exists:
        now = datetime.now().isoformat()

        valid_ref = None

        if referrer_id and referrer_id != user.id:
            cur.execute(
                "SELECT user_id FROM users WHERE user_id=?",
                (referrer_id,)
            )
            if cur.fetchone():
                valid_ref = referrer_id

        cur.execute("""
            INSERT INTO users
            (user_id, username, first_name, balance,
             referrer_id, referrals, last_bonus, created_at)
            VALUES (?, ?, ?, 0, ?, 0, NULL, ?)
        """, (
            user.id,
            user.username or "",
            user.first_name or "",
            valid_ref,
            now,
        ))

        if valid_ref:
            cur.execute("""
                UPDATE users
                SET balance = balance + ?,
                    referrals = referrals + 1
                WHERE user_id=?
            """, (REFERRAL_REWARD, valid_ref))

    else:
        cur.execute("""
            UPDATE users
            SET username=?, first_name=?
            WHERE user_id=?
        """, (
            user.username or "",
            user.first_name or "",
            user.id,
        ))

    con.commit()
    con.close()


def get_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, username, first_name,
               balance, referrals, last_bonus
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


# =========================
# KEYBOARDS
# =========================

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📞 Nomer olish", "⭐ Stars sotib olish"],
            ["🛒 Buyurtmalarim", "💳 Hisobim"],
            ["📥 Hisob to'ldirish", "💸 Pul ishlash"],
            ["📕 Qo'llanma", "☎️ Qo'llab-quvvatlash"],
        ],
        resize_keyboard=True,
    )


def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back")]
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton("📞 Nomerlar", callback_data="admin_numbers"),
        ],
        [
            InlineKeyboardButton("💳 Balans", callback_data="admin_balance"),
            InlineKeyboardButton("🛒 Buyurtmalar", callback_data="admin_orders"),
        ],
        [
            InlineKeyboardButton("📥 To'lovlar", callback_data="admin_topups"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("➕ Nomer qo'shish", callback_data="add_number"),
            InlineKeyboardButton("➕ Promokod", callback_data="add_promo"),
        ],
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except:
            referrer_id = None

    add_user(user, referrer_id)

    text = (
        "🏠 <b>ARZON OL BOT</b>\n\n"
        "🔥 Xush kelibsiz!\n\n"
        "📞 Arzon nomerlar\n"
        "⭐ Stars xaridi\n"
        "💳 Balans tizimi\n"
        "🎁 Kunlik bonus\n"
        "👥 Referal tizimi\n\n"
        "Kerakli bo'limni tanlang:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================
# NOMER OLISH
# =========================

async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT country, COUNT(*)
        FROM numbers
        WHERE sold=0
        GROUP BY country
        ORDER BY country
    """)

    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text(
            "📞 Hozircha sotuvda nomer mavjud emas.",
            reply_markup=main_menu(),
        )
        return

    buttons = []

    for country, count in rows:
        buttons.append([
            InlineKeyboardButton(
                f"🌍 {country} — {count} dona",
                callback_data=f"country:{country}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("⬅️ Orqaga", callback_data="back")
    ])

    await update.message.reply_text(
        "🌍 <b>Mavjud davlatlar:</b>\n\n"
        "Kerakli davlatni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def country_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country = query.data.split(":", 1)[1]

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, phone, price
        FROM numbers
        WHERE country=? AND sold=0
        ORDER BY id
        LIMIT 50
    """, (country,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        await query.edit_message_text(
            "❌ Bu davlatda hozircha nomer qolmagan.",
            reply_markup=back_button(),
        )
        return

    buttons = []

    for number_id, phone, price in rows:
        buttons.append([
            InlineKeyboardButton(
                f"📞 {phone} — {price:,} so'm",
                callback_data=f"number:{number_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("⬅️ Orqaga", callback_data="numbers_back")
    ])

    await query.edit_message_text(
        f"🌍 <b>{country}</b>\n\n"
        f"📦 Mavjud: {len(rows)} dona\n\n"
        "Kerakli nomerni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def number_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    number_id = int(query.data.split(":")[1])

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT country, phone, price
        FROM numbers
        WHERE id=? AND sold=0
    """, (number_id,))

    row = cur.fetchone()
    con.close()

    if not row:
        await query.edit_message_text(
            "❌ Bu nomer allaqachon sotilgan yoki mavjud emas.",
            reply_markup=back_button(),
        )
        return

    country, phone, price = row

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Sotib olish",
                callback_data=f"buy_number:{number_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data=f"country:{country}"
            )
        ],
    ])

    await query.edit_message_text(
        "📞 <b>Nomer ma'lumotlari</b>\n\n"
        f"🌍 Davlat: <b>{country}</b>\n"
        f"📱 Nomer: <code>{phone}</code>\n"
        f"💰 Narx: <b>{price:,} so'm</b>\n\n"
        "Sotib olishni tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def buy_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    number_id = int(query.data.split(":")[1])
    user_id = query.from_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT country, phone, price
        FROM numbers
        WHERE id=? AND sold=0
    """, (number_id,))

    row = cur.fetchone()

    if not row:
        con.close()
        await query.edit_message_text("❌ Nomer mavjud emas.")
        return

    country, phone, price = row

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cur.fetchone()

    if not user or user[0] < price:
        con.close()

        await query.edit_message_text(
            f"❌ Balansingiz yetarli emas.\n\n"
            f"💰 Narx: {price:,} so'm\n"
            f"💳 Balansingiz: {user[0] if user else 0:,} so'm\n\n"
            "📥 Avval hisobingizni to'ldiring.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📥 Hisob to'ldirish",
                    callback_data="topup"
                )],
                [InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="back"
                )],
            ]),
        )
        return

    cur.execute("""
        UPDATE users
        SET balance=balance-?
        WHERE user_id=?
    """, (price, user_id))

    cur.execute("""
        UPDATE numbers
        SET sold=1
        WHERE id=? AND sold=0
    """, (number_id,))

    cur.execute("""
        INSERT INTO orders
        (user_id, order_type, product, amount, price, status, created_at)
        VALUES (?, 'number', ?, 1, ?, 'completed', ?)
    """, (
        user_id,
        phone,
        price,
        datetime.now().isoformat(),
    ))

    con.commit()
    con.close()

    await query.edit_message_text(
        "✅ <b>Nomer muvaffaqiyatli sotib olindi!</b>\n\n"
        f"🌍 Davlat: {country}\n"
        f"📱 Nomer: <code>{phone}</code>\n"
        f"💰 To'lov: {price:,} so'm\n\n"
        "🛒 Buyurtma Buyurtmalarim bo'limida saqlandi.",
        parse_mode="HTML",
    )


# =========================
# STARS
# =========================

async def stars_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⭐ <b>Stars sotib olish</b>\n\n"
        f"💰 1 Stars = <b>{STARS_PRICE:,} so'm</b>\n\n"
        "👇 Qancha Stars olmoqchi ekaningizni yozing.\n"
        "Masalan: <code>50</code>",
        parse_mode="HTML",
    )

    context.user_data["waiting_stars"] = True


async def process_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_stars"):
        return False

    text = update.message.text.strip()

    try:
        stars = int(text)
    except:
        await update.message.reply_text(
            "❌ Faqat Stars sonini yozing.\nMasalan: 50"
        )
        return True

    if stars <= 0:
        await update.message.reply_text("❌ Stars soni 0 dan katta bo'lishi kerak.")
        return True

    price = stars * STARS_PRICE

    context.user_data["waiting_stars"] = False
    context.user_data["stars_amount"] = stars
    context.user_data["stars_price"] = price

    await update.message.reply_text(
        "⭐ <b>Stars buyurtmasi</b>\n\n"
        f"⭐ Miqdor: <b>{stars} Stars</b>\n"
        f"💰 Narx: <b>{price:,} so'm</b>\n\n"
        "Buyurtmani tasdiqlaysizmi?",
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
                    callback_data="cancel_stars"
                )
            ],
        ]),
    )

    return True


async def confirm_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    stars = context.user_data.get("stars_amount", 0)
    price = context.user_data.get("stars_price", 0)

    if not stars or not price:
        await query.edit_message_text("❌ Buyurtma topilmadi.")
        return

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cur.fetchone()

    if not row or row[0] < price:
        con.close()

        await query.edit_message_text(
            f"❌ Balansingiz yetarli emas.\n\n"
            f"⭐ Stars: {stars}\n"
            f"💰 Narx: {price:,} so'm\n"
            f"💳 Balans: {row[0] if row else 0:,} so'm",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📥 Hisob to'ldirish",
                    callback_data="topup"
                )]
            ]),
        )
        return

    cur.execute("""
        UPDATE users
        SET balance=balance-?
        WHERE user_id=?
    """, (price, user_id))

    cur.execute("""
        INSERT INTO orders
        (user_id, order_type, product, amount, price, status, created_at)
        VALUES (?, 'stars', ?, ?, ?, 'pending', ?)
    """, (
        user_id,
        f"{stars} Stars",
        stars,
        price,
        datetime.now().isoformat(),
    ))

    order_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data.clear()

    await query.edit_message_text(
        "✅ <b>Stars buyurtmangiz qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma: <code>#{order_id}</code>\n"
        f"⭐ Miqdor: <b>{stars} Stars</b>\n"
        f"💰 To'lov: <b>{price:,} so'm</b>\n\n"
        "⏳ Buyurtma admin tomonidan tekshirilmoqda.",
        parse_mode="HTML",
    )


# =========================
# BUYURTMALAR
# =========================

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, order_type, product, price, status
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 20
    """, (user_id,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text(
            "🛒 Sizda hozircha buyurtmalar yo'q.",
            reply_markup=main_menu(),
        )
        return

    text = "🛒 <b>Buyurtmalarim</b>\n\n"

    for oid, typ, product, price, status in rows:
        icon = "📞" if typ == "number" else "⭐"

        text += (
            f"{icon} <b>#{oid}</b>\n"
            f"📦 {product}\n"
            f"💰 {price:,} so'm\n"
            f"📌 {status}\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================
# HISOB
# =========================

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)

    if not row:
        return

    await update.message.reply_text(
        "💳 <b>Hisobim</b>\n\n"
        f"💰 Balans: <b>{row[3]:,} so'm</b>\n"
        f"👥 Referallar: <b>{row[4]}</b>\n\n"
        "💸 Pul ishlash orqali balansingizni oshirishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================
# TOPUP
# =========================

async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 <b>Hisob to'ldirish</b>\n\n"
        "To'ldirmoqchi bo'lgan summani yozing.\n"
        "Masalan: <code>50000</code>",
        parse_mode="HTML",
    )

    context.user_data["waiting_topup"] = True


async def process_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_topup"):
        return False

    try:
        amount = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Summani raqam bilan yozing.")
        return True

    if amount < 1000:
        await update.message.reply_text(
            "❌ Minimal to'lov 1,000 so'm."
        )
        return True

    user_id = update.effective_user.id

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO topups
        (user_id, amount, status, created_at)
        VALUES (?, ?, 'pending', ?)
    """, (
        user_id,
        amount,
        datetime.now().isoformat(),
    ))

    topup_id = cur.lastrowid

    con.commit()
    con.close()

    context.user_data["waiting_topup"] = False

    await update.message.reply_text(
        "📥 <b>To'lov so'rovi yaratildi!</b>\n\n"
        f"🆔 ID: <code>#{topup_id}</code>\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n\n"
        "☎️ To'lov qilish bo'yicha admin bilan bog'laning:\n"
        f"{SUPPORT_USERNAME}",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    return True


# =========================
# PUL ISHLASH
# =========================

async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)

    bot_username = context.bot.username

    ref_link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
        "💸 <b>Pul ishlash</b>\n\n"
        f"👥 Har bir referal: <b>+{REFERRAL_REWARD:,} so'm</b>\n"
        f"🎁 Kunlik bonus: <b>+{DAILY_BONUS:,} so'm</b>\n\n"
        "🔗 <b>Sizning referal havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "Do'stlaringizni taklif qiling va balansingizni oshiring.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎁 Kunlik bonus",
                    callback_data="daily_bonus"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔗 Referal havolam",
                    callback_data="ref_link"
                )
            ],
        ]),
    )


async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    today = str(date.today())

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT last_bonus FROM users WHERE user_id=?",
        (user_id,)
    )
    row = cur.fetchone()

    if row and row[0] == today:
        con.close()

        await query.edit_message_text(
            "🎁 Bugungi bonusni allaqachon olgansiz.\n\n"
            "⏰ Ertaga yana olishingiz mumkin.",
            reply_markup=back_button(),
        )
        return

    cur.execute("""
        UPDATE users
        SET balance=balance+?,
            last_bonus=?
        WHERE user_id=?
    """, (DAILY_BONUS, today, user_id))

    con.commit()
    con.close()

    await query.edit_message_text(
        f"🎁 <b>Kundalik bonus olindi!</b>\n\n"
        f"💰 +{DAILY_BONUS:,} so'm balansingizga qo'shildi.",
        parse_mode="HTML",
        reply_markup=back_button(),
    )


async def ref_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    username = context.bot.username

    link = f"https://t.me/{username}?start={user_id}"

    await query.edit_message_text(
        "🔗 <b>Referal havolangiz:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 Har bir yangi foydalanuvchi uchun "
        f"<b>+{REFERRAL_REWARD:,} so'm</b>.",
        parse_mode="HTML",
        reply_markup=back_button(),
    )


# =========================
# QO'LLANMA / SUPPORT
# =========================

async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📕 <b>Qo'llanma</b>\n\n"
        "📞 <b>Nomer olish</b> — mavjud davlatlardan nomer tanlaysiz.\n\n"
        "⭐ <b>Stars sotib olish</b> — kerakli Stars miqdorini "
        "o'zingiz kiritasiz.\n\n"
        "📥 <b>Hisob to'ldirish</b> — balansga pul qo'shasiz.\n\n"
        "💸 <b>Pul ishlash</b> — referal va kunlik bonus orqali "
        "balans yig'asiz.\n\n"
        "☎️ Muammo bo'lsa support bilan bog'laning.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "☎️ <b>Qo'llab-quvvatlash</b>\n\n"
        f"👨‍💻 Admin: {SUPPORT_USERNAME}\n\n"
        "Savolingiz bo'lsa yozishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# =========================
# ADMIN
# =========================

def is_admin(user_id):
    return user_id == ADMIN_ID


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return

    await update.message.reply_text(
        "👨‍💻 <b>ADMIN PANEL</b>\n\n"
        "Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(balance),0) FROM users")
    balance = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM numbers")
    numbers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM numbers WHERE sold=0")
    available = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders")
    orders_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending = cur.fetchone()[0]

    con.close()

    await query.edit_message_text(
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users:,}</b>\n"
        f"💰 Umumiy balans: <b>{balance:,} so'm</b>\n"
        f"📞 Jami nomerlar: <b>{numbers:,}</b>\n"
        f"🟢 Sotuvdagi nomerlar: <b>{available:,}</b>\n"
        f"🛒 Jami buyurtmalar: <b>{orders_count:,}</b>\n"
        f"⏳ Kutilayotgan buyurtmalar: <b>{pending:,}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Admin panel", callback_data="admin")]
        ]),
    )


async def admin_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT country, COUNT(*)
        FROM numbers
        WHERE sold=0
        GROUP BY country
        ORDER BY country
    """)

    rows = cur.fetchall()
    con.close()

    text = "📞 <b>NOMERLAR OMBORI</b>\n\n"

    if not rows:
        text += "❌ Ombor bo'sh."
    else:
        for country, count in rows:
            text += f"🌍 {country}: <b>{count} dona</b>\n"

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "➕ Nomer qo'shish",
                callback_data="add_number"
            )],
            [InlineKeyboardButton(
                "⬅️ Admin panel",
                callback_data="admin"
            )],
        ]),
    )


async def add_number_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_add_number"] = True
    context.user_data["add_step"] = "country"

    await query.edit_message_text(
        "➕ <b>NOMER QO'SHISH</b>\n\n"
        "1️⃣ Davlat nomini yozing.\n"
        "Masalan: <code>Uzbekistan</code>",
        parse_mode="HTML",
    )


async def admin_add_number_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return False

    if not context.user_data.get("admin_add_number"):
        return False

    text = update.message.text.strip()
    step = context.user_data.get("add_step")

    if step == "country":
        context.user_data["add_country"] = text
        context.user_data["add_step"] = "phone"

        await update.message.reply_text(
            "2️⃣ Telefon nomerini yozing.\n"
            "Masalan: <code>+998901234567</code>",
            parse_mode="HTML",
        )
        return True

    if step == "phone":
        context.user_data["add_phone"] = text
        context.user_data["add_step"] = "price"

        await update.message.reply_text(
            "3️⃣ Nomer narxini yozing.\n"
            "Masalan: <code>9371</code>",
            parse_mode="HTML",
        )
        return True

    if step == "price":
        try:
            price = int(text)
        except:
            await update.message.reply_text(
                "❌ Narx faqat raqam bo'lishi kerak."
            )
            return True

        country = context.user_data["add_country"]
        phone = context.user_data["add_phone"]

        con = db()
        cur = con.cursor()

        try:
            cur.execute("""
                INSERT INTO numbers
                (country, phone, price, sold, created_at)
                VALUES (?, ?, ?, 0, ?)
            """, (
                country,
                phone,
                price,
                datetime.now().isoformat(),
            ))

            con.commit()

            await update.message.reply_text(
                "✅ <b>Nomer omborga qo'shildi!</b>\n\n"
                f"🌍 {country}\n"
                f"📱 {phone}\n"
                f"💰 {price:,} so'm",
                parse_mode="HTML",
                reply_markup=main_menu(),
            )

        except sqlite3.IntegrityError:
            await update.message.reply_text(
                "❌ Bu nomer bazada allaqachon mavjud."
            )

        con.close()

        context.user_data.clear()
        return True

    return True


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, user_id, order_type, product, price, status
        FROM orders
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()
    con.close()

    text = "🛒 <b>OXIRGI BUYURTMALAR</b>\n\n"

    if not rows:
        text += "Buyurtmalar yo'q."
    else:
        for oid, uid, typ, product, price, status in rows:
            text += (
                f"🆔 #{oid}\n"
                f"👤 {uid}\n"
                f"📦 {product}\n"
                f"💰 {price:,} so'm\n"
                f"📌 {status}\n\n"
            )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "⬅️ Admin panel",
                callback_data="admin"
            )]
        ]),
    )


async def admin_topups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, user_id, amount, status
        FROM topups
        ORDER BY id DESC
        LIMIT 15
    """)

    rows = cur.fetchall()
    con.close()

    buttons = []
    text = "📥 <b>TO'LOV SO'ROVLARI</b>\n\n"

    if not rows:
        text += "To'lov so'rovlari yo'q."

    for tid, uid, amount, status in rows:
        text += (
            f"🆔 #{tid} | 👤 {uid}\n"
            f"💰 {amount:,} so'm | 📌 {status}\n\n"
        )

        if status == "pending":
            buttons.append([
                InlineKeyboardButton(
                    f"✅ #{tid} tasdiqlash",
                    callback_data=f"approve_topup:{tid}"
                ),
                InlineKeyboardButton(
                    f"❌ #{tid}",
                    callback_data=f"reject_topup:{tid}"
                ),
            ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Admin panel",
            callback_data="admin"
        )
    ])

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def approve_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tid = int(query.data.split(":")[1])

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, amount, status
        FROM topups
        WHERE id=?
    """, (tid,))

    row = cur.fetchone()

    if not row:
        con.close()
        await query.answer("Topup topilmadi", show_alert=True)
        return

    uid, amount, status = row

    if status != "pending":
        con.close()
        await query.answer("Bu to'lov allaqachon ko'rib chiqilgan.")
        return

    cur.execute("""
        UPDATE topups
        SET status='approved'
        WHERE id=?
    """, (tid,))

    cur.execute("""
        UPDATE users
        SET balance=balance+?
        WHERE user_id=?
    """, (amount, uid))

    con.commit()
    con.close()

    try:
        await context.bot.send_message(
            uid,
            "✅ <b>Hisobingiz to'ldirildi!</b>\n\n"
            f"💰 +{amount:,} so'm balansingizga qo'shildi.",
            parse_mode="HTML",
        )
    except:
        pass

    await query.answer("To'lov tasdiqlandi ✅")
    await admin_topups(update, context)


async def reject_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tid = int(query.data.split(":")[1])

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, status
        FROM topups
        WHERE id=?
    """, (tid,))

    row = cur.fetchone()

    if row and row[1] == "pending":
        cur.execute("""
            UPDATE topups
            SET status='rejected'
            WHERE id=?
        """, (tid,))

        con.commit()

    con.close()

    await query.answer("To'lov rad etildi ❌")
    await admin_topups(update, context)


# =========================
# CALLBACK ROUTER
# =========================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "back":
        await query.answer()
        await query.message.delete()
        await context.bot.send_message(
            query.from_user.id,
            "🏠 Asosiy menyu:",
            reply_markup=main_menu(),
        )
        return

    if data == "numbers_back":
        await query.answer()
        await query.message.delete()
        await context.bot.send_message(
            query.from_user.id,
            "📞 Nomer olish:",
            reply_markup=main_menu(),
        )
        await show_countries(update, context)
        return

    if data.startswith("country:"):
        await country_numbers(update, context)
        return

    if data.startswith("number:"):
        await number_details(update, context)
        return

    if data.startswith("buy_number:"):
        await buy_number(update, context)
        return

    if data == "confirm_stars":
        await confirm_stars(update, context)
        return

    if data == "cancel_stars":
        await query.answer()
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Stars buyurtmasi bekor qilindi.",
            reply_markup=back_button(),
        )
        return

    if data == "daily_bonus":
        await daily_bonus(update, context)
        return

    if data == "ref_link":
        await ref_link(update, context)
        return

    if data == "topup":
        await query.answer()
        await query.edit_message_text(
            "📥 Hisob to'ldirish uchun asosiy menyudagi "
            "📥 <b>Hisob to'ldirish</b> tugmasidan foydalaning.",
            parse_mode="HTML",
            reply_markup=back_button(),
        )
        return

    if data == "admin":
        if not is_admin(query.from_user.id):
            await query.answer("⛔ Ruxsat yo'q", show_alert=True)
            return

        await query.answer()
        await query.edit_message_text(
            "👨‍💻 <b>ADMIN PANEL</b>\n\n"
            "Kerakli bo'limni tanlang:",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )
        return

    if data == "admin_stats":
        await admin_stats(update, context)
        return

    if data == "admin_numbers":
        await admin_numbers(update, context)
        return

    if data == "add_number":
        await add_number_start(update, context)
        return

    if data == "admin_orders":
        await admin_orders(update, context)
        return

    if data == "admin_topups":
        await admin_topups(update, context)
        return

    if data.startswith("approve_topup:"):
        await approve_topup(update, context)
        return

    if data.startswith("reject_topup:"):
        await reject_topup(update, context)
        return

    await query.answer()


# =========================
# MESSAGE ROUTER
# =========================

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    add_user(user)

    # Admin nomer qo'shish
    if await admin_add_number_message(update, context):
        return

    # Stars
    if await process_stars(update, context):
        return

    # Topup
    if await process_topup(update, context):
        return

    text = update.message.text

    if text == "📞 Nomer olish":
        await show_countries(update, context)

    elif text == "⭐ Stars sotib olish":
        await stars_menu(update, context)

    elif text == "🛒 Buyurtmalarim":
        await orders(update, context)

    elif text == "💳 Hisobim":
        await account(update, context)

    elif text == "📥 Hisob to'ldirish":
        await topup(update, context)

    elif text == "💸 Pul ishlash":
        await earn(update, context)

    elif text == "📕 Qo'llanma":
        await guide(update, context)

    elif text == "☎️ Qo'llab-quvvatlash":
        await support(update, context)

    else:
        await update.message.reply_text(
            "🏠 Menyudan kerakli bo'limni tanlang.",
            reply_markup=main_menu(),
        )


# =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi!")

    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID topilmadi!")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(
        CallbackQueryHandler(callbacks)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages
        )
    )

    print("ARZON OL BOT ishga tushdi...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
