import base64
import glob
import hashlib
import hmac
import json
import logging
import os
import time
from typing import List, Optional

import bcrypt
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    APP_SECRET_KEY,
    CORS_ORIGINS,
    DATABASE_NAME,
    PORT,
    STUDENT_PASSWORD,
    STUDENT_USERNAME,
)
from backend.database import db_instance
from backend.pdf_ingestion import ingestion_engine
from backend.multi_agent import agent_council

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = FastAPI(
    title="Campus Nexus AI — Grounded Knowledge System",
    description="HN-AI-01: Multi-Agent RAG Engine with MongoDB Atlas & Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    language: Optional[str] = "English"


class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None


def _build_account_store() -> dict:
    account_entries = (
        (STUDENT_USERNAME, "student", "Student User", STUDENT_PASSWORD),
        (ADMIN_USERNAME, "admin", "HOD / Teacher", ADMIN_PASSWORD),
        ("hod", "admin", "HOD / Teacher", ADMIN_PASSWORD),
        ("teacher", "admin", "Teacher", ADMIN_PASSWORD),
    )
    store = {}
    for username, role, display_name, password in account_entries:
        if not username:
            continue
        password_bytes = (password or "").encode("utf-8")
        store[username] = {
            "username": username,
            "role": role,
            "name": display_name,
            "password_hash": bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8"),
        }
    return store


USER_ACCOUNT_STORE = _build_account_store()


def _encode_token(payload: dict) -> str:
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(APP_SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def _decode_token(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        payload_b64, signature = token.split(".", 1)
        expected = hmac.new(APP_SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(padded.encode("utf-8"))
        data = json.loads(payload.decode("utf-8"))

        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None


def get_current_user(authorization: Optional[str] = Header(default=None, alias="Authorization")) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    token = authorization.replace("Bearer ", "", 1).strip()
    user = _decode_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication expired or invalid.")
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Campus Knowledge Agent (HN-AI-01)",
        "mongodb_connected": db_instance.is_connected,
        "database_name": DATABASE_NAME,
        "documents_count": len(db_instance.get_documents()),
        "chunks_count": len(db_instance.get_all_chunks()),
    }


@app.get("/health")
def deployment_health_check():
    return {"status": "ok"}


@app.post("/api/login")
def login_user(req: LoginRequest):
    username = (req.username or "").strip()
    password = req.password or ""

    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    account = USER_ACCOUNT_STORE.get(username)
    if not account:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not bcrypt.checkpw(password.encode("utf-8"), account["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = _encode_token({
        "username": username,
        "role": account["role"],
        "name": account["name"],
        "exp": int(time.time()) + 86400,
    })

    return {
        "token": token,
        "user": {
            "username": username,
            "role": account["role"],
            "name": account["name"],
        },
    }


@app.get("/api/me")
def get_current_profile(current_user: dict = Depends(get_current_user)):
    return {
        "user": {
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "name": current_user.get("name"),
        }
    }


@app.get("/api/documents")
def list_documents(current_user: dict = Depends(get_current_user)):
    return {"documents": db_instance.get_documents(), "user": current_user.get("role")}


@app.post("/api/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(require_admin),
):
    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue

        filename = os.path.basename(file.filename.replace("\\", "/"))
        try:
            content = await file.read()
            res = ingestion_engine.process_pdf_bytes(content, custom_filename=filename)
            results.append(res)
        except Exception as e:
            logger.warning(f"Document upload failed for {filename}: {e}")
            results.append({
                "file_name": filename,
                "status": "error",
                "message": "We couldn't process this document. Please try again or upload a valid PDF.",
            })

    return {
        "processed_files": len(results),
        "results": results,
    }


@app.post("/api/query")
def process_query(req: QueryRequest, current_user: dict = Depends(get_current_user)):
    if not req.query or req.query.strip() == "":
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    normalized_lang = str(req.language or "English").strip()
    if normalized_lang.lower() == "tamil / tanglish":
        normalized_lang = "Tamil"
    elif normalized_lang.lower() == "தமிழ்":
        normalized_lang = "Tamil"
    elif normalized_lang.lower() == "tanglish":
        normalized_lang = "Tanglish"
    elif normalized_lang.lower() == "english":
        normalized_lang = "English"
    elif normalized_lang.lower() == "auto":
        normalized_lang = "auto"

    try:
        response = agent_council.process_student_query(req.query.strip(), normalized_lang)
        return response
    except Exception as exc:
        logger.exception("Query processing failed")
        return {
            "answer": "AI service is temporarily unavailable.",
            "citations": [],
            "status": "error",
            "language": normalized_lang,
            "latency_ms": 0,
            "agent_logs": [],
        }


@app.get("/api/analytics")
def get_analytics(current_user: dict = Depends(require_admin)):
    return db_instance.get_analytics()


@app.post("/api/seed")
def seed_sample_docs(current_user: dict = Depends(require_admin)):
    """Seeds default 5 campus PDFs if available."""
    sample_files = glob.glob("sample_docs/*.pdf")
    if not sample_files:
        raise HTTPException(status_code=404, detail="No sample PDF documents found in sample_docs/.")

    results = []
    for pdf in sample_files:
        try:
            res = ingestion_engine.process_pdf_file(pdf)
            results.append(res)
        except Exception as e:
            logger.warning(f"Seed PDF failed: {e}")
            results.append({"file": pdf, "error": "We couldn't process this document. Please try again."})

    return {
        "message": f"Successfully processed {len(results)} sample PDFs into MongoDB.",
        "results": results,
    }


# Serve frontend static assets
os.makedirs("frontend", exist_ok=True)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=PORT, reload=True)
