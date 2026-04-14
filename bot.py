from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db import get_user, create_order
from payment import create_invoice

dp = Dispatcher()


# =========================
# MAIN MENU
# =========================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 租赁 888 号码", callback_data="rent")],
        [InlineKeyboardButton(text="🛒 购买号码", callback_data="buy_number")],
        [
            InlineKeyboardButton(text="💎 开通会员", callback_data="vip"),
            InlineKeyboardButton(text="⭐ 购买星星", callback_data="stars")
        ],
        [
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup"),
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile")
        ]
    ])


# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):
    user = await get_user(msg.from_user.id)

    text = (
        "💎 欢迎使用 VIP 系统\n\n"
        f"👤 用户ID: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT\n\n"
        "请选择功能👇"
    )

    await msg.answer(text, reply_markup=main_menu())


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer()

    user_id = call.from_user.id

    # =========================
    # ⭐ STARS
    # =========================
    if call.data == "stars":
        await call.message.edit_text(
            "⭐ 选择星星套餐",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="50⭐ / 1$", callback_data="buy_star_1"),
                    InlineKeyboardButton(text="100⭐ / 2$", callback_data="buy_star_2")
                ],
                [
                    InlineKeyboardButton(text="500⭐ / 5$", callback_data="buy_star_5"),
                    InlineKeyboardButton(text="1000⭐ / 10$", callback_data="buy_star_10")
                ],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    elif call.data.startswith("buy_star"):
        amount = int(call.data.split("_")[-1])

        # ✅ CREATE ORDER
        order_id = await create_order(user_id, amount, "stars")

        link = await create_invoice(order_id, amount)

        await call.message.answer(
            f"💳 订单 #{order_id}\n\n点击支付👇\n{link}"
        )

    # =========================
    # 💰 TOPUP
    # =========================
    elif call.data == "topup":
        await call.message.edit_text(
            "💰 选择充值金额",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    elif call.data.startswith("top_"):
        amount = int(call.data.split("_")[1])

        # ✅ CREATE ORDER
        order_id = await create_order(user_id, amount, "topup")

        link = await create_invoice(order_id, amount)

        await call.message.answer(
            f"💰 充值订单 #{order_id}\n\n👉 {link}"
        )

    # =========================
    # 👤 PROFILE
    # =========================
    elif call.data == "profile":
        user = await get_user(user_id)

        await call.message.edit_text(
            f"👤 用户中心\n\n💰 余额: {user['balance']} USDT",
            reply_markup=main_menu()
        )

    # =========================
    # 📦 RENT
    # =========================
    elif call.data == "rent":
        await call.message.edit_text(
            "📦 可租号码",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="+888 0519 3764 🟢", callback_data="rent_1")],
                [InlineKeyboardButton(text="+888 0795 1643 🟢", callback_data="rent_2")],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    # =========================
    # 🛒 BUY NUMBER
    # =========================
    elif call.data == "buy_number":
        await call.message.edit_text(
            "🌍 选择国家",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇦🇪 UAE - 2.85$", callback_data="buy_uae")],
                [InlineKeyboardButton(text="🇵🇭 Philippines - 0.79$", callback_data="buy_ph")],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    # =========================
    # BACK
    # =========================
    elif call.data == "back":
        user = await get_user(user_id)

        await call.message.edit_text(
            f"💎 VIP 系统\n\n💰 余额: {user['balance']} USDT",
            reply_markup=main_menu()
        )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统运行中...")

# =========================
# RUN
# =========================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
