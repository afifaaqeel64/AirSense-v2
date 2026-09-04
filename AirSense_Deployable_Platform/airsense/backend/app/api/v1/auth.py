from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.core.security import hash_password, verify_password, create_access_token, generate_api_key
import asyncpg
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])
DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    city: str = "lahore"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(req: RegisterRequest):
    conn = await asyncpg.connect(DSN)
    try:
        existing = await conn.fetchval("SELECT id FROM users WHERE email=$1", req.email)
        if existing:
            raise HTTPException(400, "Email already registered")
        api_key = generate_api_key()
        user_id = await conn.fetchval("""
            INSERT INTO users (email, password_hash, full_name, city, api_key)
            VALUES ($1,$2,$3,$4,$5) RETURNING id
        """, req.email, hash_password(req.password), req.full_name, req.city, api_key)
        return {"message": "Account created", "api_key": api_key,
                "token": create_access_token({"sub": str(user_id), "email": req.email})}
    finally:
        await conn.close()

@router.post("/login")
async def login(req: LoginRequest):
    conn = await asyncpg.connect(DSN)
    try:
        user = await conn.fetchrow("SELECT * FROM users WHERE email=$1 AND is_active=TRUE", req.email)
        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        return {
            "token": create_access_token({"sub": str(user["id"]), "email": user["email"], "role": user["role"]}),
            "api_key": user["api_key"],
            "user": {"email": user["email"], "full_name": user["full_name"], "city": user["city"]},
        }
    finally:
        await conn.close()
