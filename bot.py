@dp.callback_query()
async def cb(call: types.CallbackQuery):

    # 🔥 FIX timeout
    try:
        await call.answer()
    except:
        pass

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 🏠 HOME
    # =========================
    if call.data == "back":
        user = await get_user(user_id)
        await call.message.edit_text(
            f"💎 VIP系统\n\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )

    # =========================
    # 🌍 MARKET
    # =========================
    elif call.data == "country":

        await call.message.edit_text("""
🌍 <b>全球号码市场</b>

🇺🇸 USA  
🇬🇧 UK  
💎 888专区  
""", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 888专区", callback_data="rent")],
            [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
        ]))

    # =========================
    # 📦 LIST
    # =========================
    elif call.data == "rent":

        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM numbers LIMIT 10")

        text = "📦 <b>号码列表</b>\n\n"
        keyboard = []

        for r in rows:
            text += f"🟢 <code>{r['number']}</code>\n"

            keyboard.append([
                InlineKeyboardButton(
                    text=r['number'],
                    callback_data=f"select_{r['id']}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="🔙 返回", callback_data="back")])

        await call.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    # =========================
    # 🔒 LOCK
    # =========================
    elif call.data.startswith("select_"):

        num_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if not row:
                return

            await conn.execute("""
            UPDATE numbers
            SET status='locked',
                locked_by=$1,
                locked_until=NOW() + INTERVAL '5 minutes'
            WHERE id=$2
            """, user_id, num_id)

        # 💎 invoice UI
        await call.message.edit_text(f"""
💳 <b>订单确认</b>

━━━━━━━━━━━━━━
📞 <code>{row['number']}</code>
💰 1个月: {row['price_1m']}U
💰 3个月: {row['price_3m']}U
━━━━━━━━━━━━━━

⏳ 请在5分钟内付款
""", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 1个月", callback_data=f"pay1_{num_id}")],
            [InlineKeyboardButton(text="💳 3个月", callback_data=f"pay3_{num_id}")],
            [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
        ]))

    # =========================
    # 💳 CREATE ORDER + INVOICE
    # =========================
    elif call.data.startswith("pay"):

        num_id = int(call.data.split("_")[1])
        amount = 99 if "pay1" in call.data else 268

        async with pool.acquire() as conn:

            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
                user_id, amount
            )

        # 💎 HOÁ ĐƠN XỊN
        await call.message.edit_text(f"""
💳 <b>订单已创建</b>

━━━━━━━━━━━━━━
🆔 <code>#{order_id}</code>
💰 <b>{amount} USDT</b>
━━━━━━━━━━━━━━

📥 请转账并提交凭证
""", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 上传凭证", callback_data=f"upload_{order_id}")],
            [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
        ]))

        # 👨‍💼 gửi admin
        await bot.send_message(
            ADMIN_ID,
            f"""
🆕 订单通知

🆔 {order_id}
👤 用户: {user_id}
💰 金额: {amount}U
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ 已收款", callback_data=f"confirm_{order_id}"),
                    InlineKeyboardButton(text="❌ 未收款", callback_data=f"reject_{order_id}")
                ]
            ])
        )

    # =========================
    # 👨‍💼 ADMIN CONFIRM
    # =========================
    elif call.data.startswith("confirm_"):

        order_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            await conn.execute(
                "UPDATE orders SET status='paid' WHERE id=$1",
                order_id
            )

            row = await conn.fetchrow(
                "SELECT * FROM orders WHERE id=$1",
                order_id
            )

            user_id = row["user_id"]

            acc = await conn.fetchrow("""
            SELECT * FROM accounts WHERE status='free' LIMIT 1
            """)

            if acc:
                await conn.execute(
                    "UPDATE accounts SET status='used' WHERE id=$1",
                    acc["id"]
                )

                await bot.send_message(
                    user_id,
                    f"""
🎉 购买成功

👤 {acc['username']}
🔑 {acc['password']}
"""
                )

        await call.message.edit_text("✅ 已确认收款")

    elif call.data.startswith("reject_"):
        await call.message.edit_text("❌ 未收款")
