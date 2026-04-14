import httpx
from config import NOWPAY_KEY

API_URL = "https://api.nowpayments.io/v1/invoice"


async def create_invoice(order_id: int, amount: float):
    try:
        headers = {"x-api-key": NOWPAY_KEY}

        data = {
            "price_amount": amount,
            "price_currency": "usd",
            "pay_currency": "usdttrc20",
            "order_id": str(order_id),
            "ipn_callback_url": "https://zxz666-production.up.railway.app/payment-hook"
        }

        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(API_URL, json=data, headers=headers)

        result = res.json()

        link = result.get("invoice_url")

        # 💣 FIX NONE
        if not link:
            print("ERROR NOWPAY:", result)
            return "❌ Payment error, try again"

        return link

    except Exception as e:
        print("PAY ERROR:", e)
        return "❌ Payment system error"
