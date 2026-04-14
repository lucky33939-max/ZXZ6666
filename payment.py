import httpx
from config import NOWPAY_KEY

API = "https://api.nowpayments.io/v1/invoice"

async def create_invoice(order_id, price):
    headers = {"x-api-key": NOWPAY_KEY}

    data = {
        "price_amount": price,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_id": str(order_id)
    }

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(API, json=data, headers=headers)
        return res.json()["invoice_url"]
