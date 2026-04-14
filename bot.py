import asyncio
import logging
from typing import Dict

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import get_user, get_pool, create_user
from payment import create_invoice

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# CONSTANTS
# =========================
STAR_PACKAGES: Dict[str, int] = {
    "buy_star_1": 1,
    "buy_star_2": 2,
    "buy_star_5": 5,
    "buy_star_10": 10,
}

TOPUP_PACKAGES: Dict[str, int] = {
    "top_10": 10,
    "top_50": 50,
    "top_100": 100,
    "top_500": 500,
    "top_1000": 1000,
    "top_5000": 5000,
}


# =========================
# KEYBOARDS
# =========================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Thuê số 888", callback_data="rent")],
        [InlineKeyboardButton(text="🛒 Mua số", callback_data="buy_number")],
        [
            InlineKeyboardButton(text="💎 VIP", callback_data="vip"),
            InlineKeyboardButton(text="⭐ Mua sao", callback_data="stars")
        ],
        [
            InlineKeyboardButton(text="💰 Nạp tiền", callback_data="topup"),
            InlineKeyboardButton(text="👤 Hồ sơ", callback_data="profile")
        ]
    ])


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Quay lại", callback_data="back")]
    ])


# =========================
# UTILS
# =========================
async def get_or_create_user(user_id: int):
    user = await get_user(user_id)
    if not user:
        user = await create_user(user_id)
    return user


async def create_order(pool, user_id: int, amount: int):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO orders(user_id, amount) VALUES($1,$2) RETURNING id",
            user_id, amount
        )


# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):
    user = await get_or_create_user(msg.from_user.id)

    text = (
        "💎 Chào mừng đến hệ thống VIP\n\n"
        f"👤 ID: {msg.from_user.id}\n"
        f"💰 Số dư: {user['balance']} USDT\n\n"
        "Chọn chức năng 👇"
    )

    await msg.answer(text, reply_markup=main_menu())


# =========================
# STARS
# =========================
@dp.callback_query(F.data == "stars")
async def stars_menu(call: types.CallbackQuery):
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="50⭐ / 1$", callback_data="buy_star_1"),
            InlineKeyboardButton(text="100⭐ / 2$", callback_data="buy_star_2")
        ],
        [
            InlineKeyboardButton(text="500⭐", callback_data="buy_star_5"),
            InlineKeyboardButton(text="1000⭐", callback_data="buy_star_10")
        ],
        [InlineKeyboardButton(text="🔙 Quay lại", callback_data="back")]
    ])

    await call.message.edit_text("⭐ Chọn gói sao", reply_markup=kb)


@dp.callback_query(F.data.startswith("buy_star"))
async def buy_star(call: types.CallbackQuery):
    await call.answer()

    amount = STAR_PACKAGES.get(call.data)
    if not amount:
        return await call.message.answer("❌ Gói không hợp lệ")

    pool = await get_pool()
    order_id = await create_order(pool, call.from_user.id, amount)
    link = await create_invoice(order_id, amount)

    await call.message.answer(
        f"💳 Đơn #{order_id}\n\nThanh toán 👇\n{link}"
    )


# =========================
# TOPUP
# =========================
@dp.callback_query(F.data == "topup")
async def topup_menu(call: types.CallbackQuery):
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10 USDT", callback_data="top_10"),
            InlineKeyboardButton(text="50 USDT", callback_data="top_50")
        ],
        [
            InlineKeyboardButton(text="100 USDT", callback_data="top_100"),
            InlineKeyboardButton(text="500 USDT", callback_data="top_500")
        ],
        [
            InlineKeyboardButton(text="1000 USDT", callback_data="top_1000"),
            InlineKeyboardButton(text="5000 USDT", callback_data="top_5000")
        ],
        [InlineKeyboardButton(text="🔙 Quay lại", callback_data="back")]
    ])

    await call.message.edit_text("💰 Chọn số tiền nạp", reply_markup=kb)


@dp.callback_query(F.data.startswith("top_"))
async def topup(call: types.CallbackQuery):
    await call.answer()

    amount = TOPUP_PACKAGES.get(call.data)
    if not amount:
        return await call.message.answer("❌ Số tiền không hợp lệ")

    pool = await get_pool()
    order_id = await create_order(pool, call.from_user.id, amount)
    link = await create_invoice(order_id, amount)

    await call.message.answer(
        f"💰 Đơn nạp #{order_id}\n\n👉 {link}"
    )


# =========================
# PROFILE
# =========================
@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    await call.answer()

    user = await get_or_create_user(call.from_user.id)

    await call.message.edit_text(
        f"👤 Hồ sơ\n\n💰 Số dư: {user['balance']} USDT",
        reply_markup=main_menu()
    )


# =========================
# RENT / BUY
# =========================
@dp.callback_query(F.data == "rent")
async def rent(call: types.CallbackQuery):
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+888 0519 3764 🟢", callback_data="rent_1")],
        [InlineKeyboardButton(text="+888 0795 1643 🟢", callback_data="rent_2")],
        [InlineKeyboardButton(text="🔙 Quay lại", callback_data="back")]
    ])

    await call.message.edit_text("📦 Danh sách số", reply_markup=kb)


@dp.callback_query(F.data == "buy_number")
async def buy_number(call: types.CallbackQuery):
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇦🇪 UAE - 2.85$", callback_data="buy_uae")],
        [InlineKeyboardButton(text="🇵🇭 Philippines - 0.79$", callback_data="buy_ph")],
        [InlineKeyboardButton(text="🔙 Quay lại", callback_data="back")]
    ])

    await call.message.edit_text("🌍 Chọn quốc gia", reply_markup=kb)


# =========================
# BACK
# =========================
@dp.callback_query(F.data == "back")
async def back(call: types.CallbackQuery):
    await call.answer()

    user = await get_or_create_user(call.from_user.id)

    await call.message.edit_text(
        f"💎 VIP System\n\n💰 Số dư: {user['balance']} USDT",
        reply_markup=main_menu()
    )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ Bot đang hoạt động...")


# =========================
# RUN
# =========================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
