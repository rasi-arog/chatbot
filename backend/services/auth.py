from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import os

SECRET_KEY = os.getenv("JWT_SECRET", "change_this_secret")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token=Depends(security)) -> str:
    try:
        data = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return data["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
