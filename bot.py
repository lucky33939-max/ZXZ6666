import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from bot import dp
from db import init_db, create_tables

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)


async def main():
    # ✅ INIT DATABASE
    await init_db()
    await create_tables()

    print("✅ DB connected")

    # ✅ START BOT
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

# =========================
# RUN
# =========================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
