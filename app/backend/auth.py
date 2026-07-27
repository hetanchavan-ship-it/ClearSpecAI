"""JWT-based authentication helpers for ClearSpec AI."""
from __future__ import annotations

import importlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING
from config import get_settings

bcrypt = None
try:
    bcrypt = importlib.import_module("bcrypt")
except ImportError:  # pragma: no cover - fallback when bcrypt isn't installed
    bcrypt = None
jwt = None
try:
    jwt = importlib.import_module("jwt")
except ImportError:  # pragma: no cover - fallback when PyJWT isn't installed
    jwt = None
Depends = None
HTTPException = None
HTTPAuthorizationCredentials = None
HTTPBearer = None
try:
    fastapi = importlib.import_module("fastapi")
    Depends = fastapi.Depends
    HTTPException = fastapi.HTTPException
    fastapi_security = importlib.import_module("fastapi.security")
    HTTPAuthorizationCredentials = fastapi_security.HTTPAuthorizationCredentials
    HTTPBearer = fastapi_security.HTTPBearer
except ImportError:  # pragma: no cover - fallback when FastAPI isn't installed
    pass

class _FastAPIHTTPException(Exception):
    def __init__(self, status_code: int = 500, detail: str = ""):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail

if HTTPException is None:
    HTTPException = _FastAPIHTTPException

try:
    pydantic = importlib.import_module("pydantic")
    BaseModel = pydantic.BaseModel
    Field = pydantic.Field
    try:
        EmailStr = pydantic.EmailStr
    except AttributeError:
        # Older pydantic versions expose EmailStr in pydantic.networks
        networks = importlib.import_module("pydantic.networks")
        EmailStr = networks.EmailStr
except Exception:  # pragma: no cover - pydantic is required at runtime
    raise RuntimeError("pydantic library is required")

settings = get_settings()

JWT_SECRET = settings.jwt_secret
JWT_ALG = settings.jwt_algorithm
JWT_EXP_DAYS = settings.jwt_exp_days

security = HTTPBearer(auto_error=False)


class UserCreate(BaseModel):
    email: "EmailStr" # type: ignore
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class UserLogin(BaseModel):
    email: "EmailStr" # type: ignore
    password: str


class UserPublic(BaseModel):
    id: str
    email: "EmailStr" # type: ignore
    name: str


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


def hash_password(password: str) -> str:
    if not bcrypt:
        raise RuntimeError("bcrypt library is required for password hashing")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        if not bcrypt:
            raise RuntimeError("bcrypt library is required for password verification")
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    creds: Optional[object] = Depends(security),
) -> dict:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    return {"id": payload["sub"], "email": payload["email"]}


def user_doc(email: str, name: str, password: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "email": email.lower().strip(),
        "name": name.strip(),
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
