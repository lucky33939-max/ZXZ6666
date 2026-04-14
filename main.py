import os
import asyncio
import logging
import random
import asyncpg

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
router = Router()
dp.include_router(router)

app = FastAPI()
db = None

user_lock = {}

# ================= DB =================
async def init_db():
    global db
    while True:
        try:
            db = await asyncpg.create_pool(DATABASE_URL)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                balance FLOAT DEFAULT 0
            );
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                product TEXT,
                price FLOAT,
                status TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)

            print("✅ DB READY")
            break
        except Exception as e:
            print("❌ DB ERROR:", e)
            await asyncio.sleep(2)

# ================= MENU =================
def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="💎 开通会员"), types.KeyboardButton(text="✨ 购买星星")],
            [types.KeyboardButton(text="👑 靓号市场"), types.KeyboardButton(text="🔥 888靓号")],
            [types.KeyboardButton(text="💰 余额充值"), types.KeyboardButton(text="👤 个人中心")],
            [types.KeyboardButton(text="📦 我的订单"), types.KeyboardButton(text="👨‍💻 客服")]
        ],
        resize_keyboard=True
    )

# ================= USER =================
async def get_user(user_id):
    user = await db.fetchrow("SELECT * FROM users WHERE telegram_id=$1", user_id)
    if not user:
        await db.execute("INSERT INTO users(telegram_id) VALUES($1)", user_id)
        user = await db.fetchrow("SELECT * FROM users WHERE telegram_id=$1", user_id)
    return user

# ================= START =================
@router.message(lambda msg: msg.text == "/start")
async def start(msg: types.Message):
    await get_user(msg.from_user.id)

    await msg.answer("""
<b>🚀 欢迎使用系统</b>

⚡ 自动化交易系统
""", reply_markup=main_menu())

# ================= STARS =================
@router.message(lambda msg: msg.text == "✨ 购买星星")
async def stars(msg: types.Message):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="50⭐ / 1$", callback_data="star_50"),
         types.InlineKeyboardButton(text="100⭐ / 2$", callback_data="star_100")],
        [types.InlineKeyboardButton(text="200⭐ / 3$", callback_data="star_200"),
         types.InlineKeyboardButton(text="500⭐ / 6$", callback_data="star_500")]
    ])
    await msg.answer("✨ <b>请选择套餐</b>", reply_markup=kb)

# ================= CREATE ORDER =================
async def create_order(user_id, product, price):
    row = await db.fetchrow("""
        INSERT INTO orders(user_id, product, price, status)
        VALUES($1,$2,$3,'pending')
        RETURNING id
    """, user_id, product, price)
    return row["id"]

# ================= CALLBACK =================
@router.callback_query(lambda c: c.data.startswith("star"))
async def buy(call: types.CallbackQuery):

    if call.from_user.id in user_lock:
        await call.answer("⚠️ 操作太快", show_alert=True)
        return

    user_lock[call.from_user.id] = True

    await call.answer()

    try:
        amount = int(call.data.split("_")[1])
        price_map = {50:1, 100:2, 200:3, 500:6}
        price = price_map.get(amount, amount)

        user = await get_user(call.from_user.id)

        # ===== BALANCE PAY =====
        if user["balance"] >= price:
            await db.execute("""
            UPDATE users SET balance = balance - $1
            WHERE telegram_id=$2
            """, price, call.from_user.id)

            await call.message.answer("✅ 支付成功（余额）")

            await call.message.answer(f"📦 ⭐ {amount} 已到账")
            return

        # ===== CREATE ORDER =====
        order_id = await create_order(call.from_user.id, f"STAR {amount}", price)

        await call.message.answer(f"""
🧾 <b>订单 #{order_id}</b>

⭐ 数量: {amount}
💰 金额: {price} USDT

━━━━━━━━━━━━━━━
💳 地址(TRC20):

<code>TXXXXXXX</code>

⏳ 状态: 等待支付
""")

        # ===== ADMIN ALERT =====
        if ADMIN_ID:
            await bot.send_message(ADMIN_ID, f"💰 新订单 #{order_id} - {price}U")

    except Exception as e:
        print("❌ ERROR:", e)

    finally:
        del user_lock[call.from_user.id]

# ================= PROFILE =================
@router.message(lambda msg: msg.text == "👤 个人中心")
async def profile(msg: types.Message):
    user = await get_user(msg.from_user.id)

    await msg.answer(f"""
👤 <b>个人中心</b>

🆔 {msg.from_user.id}
💰 余额: {user['balance']} USDT
""")

# ================= ORDERS =================
@router.message(lambda msg: msg.text == "📦 我的订单")
async def orders(msg: types.Message):
    rows = await db.fetch("""
    SELECT * FROM orders WHERE user_id=$1 ORDER BY id DESC LIMIT 5
    """, msg.from_user.id)

    text = "📦 <b>最近订单</b>\n\n"

    for r in rows:
        text += f"#{r['id']} - {r['status']} - {r['price']}U\n"

    await msg.answer(text)

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return {"ok": False}

    data = await request.json()
    logging.info(f"🔥 UPDATE")

    update = types.Update(**data)

    asyncio.create_task(dp.feed_update(bot, update))

    return {"ok": True}

# ================= ROOT =================
@app.get("/")
async def root():
    return {"status": "ok"}

# ================= STARTUP =================
@app.on_event("startup")
async def startup():
    await init_db()
