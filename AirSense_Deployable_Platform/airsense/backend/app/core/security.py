from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

def generate_api_key() -> str:
    return secrets.token_urlsafe(48)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
):
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    return payload

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_token(credentials.credentials)
