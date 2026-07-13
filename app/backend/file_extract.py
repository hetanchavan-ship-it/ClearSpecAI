"""Extract text from uploaded PDF / DOCX / TXT transcripts."""
import io

from fastapi import HTTPException, UploadFile
from PyPDF2 import PdfReader
from docx import Document

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


async def extract_text(upload: UploadFile) -> str:
    raw = await upload.read()

    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB).")

    name = (upload.filename or "").lower()

    try:
        if name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            ).strip()

        if name.endswith(".docx"):
            doc = Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs).strip()

        if name.endswith(".txt") or name.endswith(".md"):
            return raw.decode("utf-8", errors="ignore").strip()

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    raise HTTPException(
        status_code=415,
        detail="Unsupported file type. Use PDF, DOCX, TXT or MD."
    )