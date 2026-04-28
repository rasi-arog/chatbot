from fastapi import APIRouter, HTTPException
from models.user import UserRequest
from config.db import users_collection
from services.auth import hash_password, verify_password, create_token

router = APIRouter()

@router.post("/register")
def register(user: UserRequest):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    users_collection.insert_one({"email": user.email, "password": hash_password(user.password)})
    return {"message": "User created"}

@router.post("/login")
def login(user: UserRequest):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(user.email), "email": user.email}
