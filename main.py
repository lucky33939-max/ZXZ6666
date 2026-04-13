from fastapi import FastAPI, Request, Depends, Header, HTTPException
from aiogram import Bot, Dispatcher, types
from db import init_db, db
from auth import *

app = FastAPI()

bots = {}
dispatchers = {}

# ================= INIT =================
@app.on_event("startup")
async def startup():
    await init_db()

    rows = await db.fetch("SELECT * FROM tenants")

    for r in rows:
        bot = Bot(token=r["bot_token"])
        dp = Dispatcher()

        register(dp, r["id"], bot)

        bots[r["bot_token"]] = bot
        dispatchers[r["bot_token"]] = dp

# ================= AUTH =================
async def get_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401)

    token = authorization.split(" ")[1]
    return verify_token(token)

# ================= BOT =================
def register(dp, tenant_id, bot):

    @dp.message(lambda m: m.text == "/start")
    async def start(msg: types.Message):
        await db.execute("""
            INSERT INTO users (tenant_id, telegram_id)
            VALUES ($1,$2)
            ON CONFLICT DO NOTHING
        """, tenant_id, msg.from_user.id)

        await msg.answer("🚀 Welcome")

    @dp.message(lambda m: "888" in m.text)
    async def rent(msg: types.Message):
        await msg.answer("🔥 888 available")

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    if token not in bots:
        return {"ok": False}

    data = await request.json()

    update = types.Update(**data)
    await dispatchers[token].process_update(update)

    return {"ok": True}

# ================= ADMIN LOGIN =================
@app.post("/admin/login")
async def login(data: dict):
    user = await db.fetchrow("SELECT * FROM admins WHERE username=$1", data["username"])

    if not user or not check_password(data["password"], user["password"]):
        return {"ok": False}

    token = create_token(user["id"], user["tenant_id"])
    return {"token": token}

# ================= GET ORDERS =================
@app.get("/admin/orders")
async def orders(user=Depends(get_user)):
    rows = await db.fetch("""
        SELECT * FROM orders WHERE tenant_id=$1 ORDER BY id DESC
    """, user["tenant_id"])

    return [dict(r) for r in rows]

# ================= CONFIRM =================
@app.post("/admin/confirm/{order_id}")
async def confirm(order_id: int, user=Depends(get_user)):
    order = await db.fetchrow("""
        SELECT * FROM orders WHERE id=$1 AND tenant_id=$2
    """, order_id, user["tenant_id"])

    if not order:
        return {"ok": False}

    await db.execute("UPDATE orders SET status='done' WHERE id=$1", order_id)

    tenant = await db.fetchrow("SELECT * FROM tenants WHERE id=$1", user["tenant_id"])
    bot = bots.get(tenant["bot_token"])

    u = await db.fetchrow("SELECT telegram_id FROM users WHERE id=$1", order["user_id"])

    await bot.send_message(u["telegram_id"], f"✅ Order #{order_id} done")

    return {"ok": True}
