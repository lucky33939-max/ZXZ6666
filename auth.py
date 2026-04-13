import jwt, datetime, bcrypt
from fastapi import HTTPException

SECRET = "SECRET_KEY"

def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_password(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_token(user_id, tenant_id):
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
