"""ClearSpec AI — FastAPI backend."""
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import (  # noqa: E402
    AuthResponse,
    UserCreate,
    UserLogin,
    UserPublic,
    create_token,
    get_current_user,
    user_doc,
    verify_password,
)
from file_extract import extract_text  # noqa: E402
from llm_client import MODEL_NAME, call_llm  # noqa: E402
from prompts import (
    STORIES_SYSTEM,
    GAP_SYSTEM,
    TRACE_SYSTEM,
    stories_user_msg,
    gap_user_msg,
    trace_user_msg,
)

# ---------- DB ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ---------- App ----------
app = FastAPI(title="ClearSpec AI")
api = APIRouter(prefix="/api")


# ---------- Models ----------
class CleanRequest(BaseModel):
    raw_text: str
    domain: str = "general"
    title: Optional[str] = None


class AnalyzeRequest(BaseModel):
    stories: str
    context: str = ""
    history_id: Optional[str] = None


class TraceRequest(BaseModel):
    stories: str
    history_id: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    title: str
    domain: str
    created_at: str
    raw_text: str
    stories_md: Optional[str] = None
    gap_md: Optional[str] = None
    trace_md: Optional[str] = None


class ExtractResponse(BaseModel):
    text: str
    filename: str

class PublicConfig(BaseModel):
    inference_provider: str
    model: str
    model_label: str
    validator: str


# ---------- Auth routes ----------
@api.post("/auth/register", response_model=AuthResponse)
async def register(payload: UserCreate):
    email = payload.email.lower().strip()

    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")

    doc = user_doc(email, payload.name, payload.password)
    await db.users.insert_one(doc)

    return AuthResponse(
        token=create_token(doc["id"], doc["email"]),
        user=UserPublic(
            id=doc["id"],
            email=doc["email"],
            name=doc["name"]
        ),
    )


@api.post("/auth/login", response_model=AuthResponse)
async def login(payload: UserLogin):
    doc = await db.users.find_one({"email": payload.email.lower().strip()})

    if not doc or not verify_password(payload.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return AuthResponse(
        token=create_token(doc["id"], doc["email"]),
        user=UserPublic(
            id=doc["id"],
            email=doc["email"],
            name=doc["name"]
        ),
    )


@api.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    doc = await db.users.find_one({"id": user["id"]})

    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    return UserPublic(
        id=doc["id"],
        email=doc["email"],
        name=doc["name"]
    )


# ---------- File extraction ----------
@api.post("/extract", response_model=ExtractResponse)
async def extract(file: UploadFile = File(...), user=Depends(get_current_user)):
    text = await extract_text(file)
    return ExtractResponse(
        text=text,
        filename=file.filename or "upload"
    )


# ---------- AI pipeline ----------
def _model_display_name(
    model_name: str,
) -> str:
    """
    Convert an OpenRouter model identifier into a readable UI label.
    """

    cleaned = (model_name or "").strip()

    provider, separator, model = cleaned.partition("/")

    if not separator:
        provider = "openrouter"
        model = cleaned

    is_free = model.endswith(":free")

    if is_free:
        model = model.removesuffix(":free")

    provider_label = provider.replace(
        "_",
        " ",
    ).upper()

    model_label = model.replace(
        "_",
        " ",
    ).upper()

    display_name = (
        f"{provider_label} / {model_label}"
    )

    if is_free:
        display_name += " : FREE"

    return display_name

def _title_from(raw: str) -> str:
    snippet = (raw or "").strip().splitlines()[0] if raw else ""
    snippet = snippet[:80].strip()
    return snippet or "Untitled requirement"


@api.post("/clean")
async def clean(payload: CleanRequest, user=Depends(get_current_user)):
    if not payload.raw_text or len(payload.raw_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least 10 characters of input."
        )

    stories_md = await call_llm(
    STORIES_SYSTEM,
    stories_user_msg(
        raw_text=payload.raw_text,
        domain=payload.domain,
    ),
    stage="stories",
)

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "title": payload.title or _title_from(payload.raw_text),
        "domain": payload.domain,
        "raw_text": payload.raw_text,
        "stories_md": stories_md,
        "gap_md": None,
        "trace_md": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.history.insert_one(record)

    return {
        "id": record["id"],
        "stories_md": stories_md,
        "title": record["title"],
    }


@api.post("/analyze")
async def analyze(payload: AnalyzeRequest, user=Depends(get_current_user)):
    if not payload.stories:
        raise HTTPException(status_code=400, detail="Stories required.")

    gap_md = await call_llm(
    GAP_SYSTEM,
    gap_user_msg(
        stories_md=payload.stories,
        context=payload.context or "",
    ),
    stage="gap",
)

    if payload.history_id:
        await db.history.update_one(
            {"id": payload.history_id, "user_id": user["id"]},
            {"$set": {"gap_md": gap_md}},
        )

    return {"gap_md": gap_md}


@api.post("/trace")
async def trace(payload: TraceRequest, user=Depends(get_current_user)):
    if not payload.stories:
        raise HTTPException(status_code=400, detail="Stories required.")

    trace_md = await call_llm(
    TRACE_SYSTEM,
    trace_user_msg(
        stories_md=payload.stories,
    ),
    stage="trace",
)

    if payload.history_id:
        await db.history.update_one(
            {"id": payload.history_id, "user_id": user["id"]},
            {"$set": {"trace_md": trace_md}},
        )

    return {"trace_md": trace_md}


# ---------- History ----------
@api.get("/history", response_model=List[HistoryItem])
async def list_history(user=Depends(get_current_user)):
    cursor = (
        db.history
        .find({"user_id": user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(100)
    )

    items = []
    async for doc in cursor:
        items.append(
            HistoryItem(
                id=doc["id"],
                title=doc.get("title", "Untitled"),
                domain=doc.get("domain", "general"),
                created_at=doc["created_at"],
                raw_text=doc.get("raw_text", ""),
                stories_md=doc.get("stories_md"),
                gap_md=doc.get("gap_md"),
                trace_md=doc.get("trace_md"),
            )
        )

    return items


@api.get("/history/{item_id}", response_model=HistoryItem)
async def get_history(item_id: str, user=Depends(get_current_user)):
    doc = await db.history.find_one(
        {"id": item_id, "user_id": user["id"]},
        {"_id": 0}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return HistoryItem(
        id=doc["id"],
        title=doc.get("title", "Untitled"),
        domain=doc.get("domain", "general"),
        created_at=doc["created_at"],
        raw_text=doc.get("raw_text", ""),
        stories_md=doc.get("stories_md"),
        gap_md=doc.get("gap_md"),
        trace_md=doc.get("trace_md"),
    )


@api.delete("/history/{item_id}")
async def delete_history(item_id: str, user=Depends(get_current_user)):
    res = await db.history.delete_one(
        {"id": item_id, "user_id": user["id"]}
    )

    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")

    return {"ok": True}


@api.get("/config", response_model=PublicConfig)
async def public_config():
    return PublicConfig(
        inference_provider="OpenRouter",
        model=MODEL_NAME,
        model_label=_model_display_name(
            MODEL_NAME
        ),
        validator="online",
    )


@api.get("/")
async def root():
    return {"service": "ClearSpec AI", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()