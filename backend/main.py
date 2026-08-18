import os
import random
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
# Prefer this project's .env over stale variables inherited by an IDE terminal.
load_dotenv(ROOT_DIR / ".env", override=True)

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from prompts import SYSTEM_PROMPT, ANALYTICS_PROMPT
from llm_client import chat_completion, safe_json_parse
from whatsapp_notifier import whatsapp_notifications_ready, send_booking_confirmation

app = FastAPI(title="Northstar Homes AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_dev_asset_cache(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response

SESSIONS = {}

BOOKING_KEYWORDS = ["book", "site visit", "visit", "confirm", "slot"]


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    force_booking_failure: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    whatsapp_confirmation_queued: bool = False


class EndRequest(BaseModel):
    session_id: str


def get_session(session_id: str | None):
    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "history": [{"role": "system", "content": SYSTEM_PROMPT}],
            "booking_outcome_decided": False,
            "booking_confirmed": False,
            "booking_request": None,
            "customer_whatsapp": None,
            "whatsapp_confirmation_queued": False,
        }
    return session_id, SESSIONS[session_id]


def looks_like_booking_attempt(text: str) -> bool:
    lowered = text.lower()
    has_keyword = any(k in lowered for k in BOOKING_KEYWORDS)
    has_number = any(ch.isdigit() for ch in text)
    return has_keyword and has_number


def extract_whatsapp_number(text: str) -> str | None:
    """Return an E.164-style number without '+' when one is supplied."""
    candidate = re.search(r"(?:\+|00)?\d(?:[\s().-]*\d){8,14}", text)
    if not candidate:
        return None

    raw = candidate.group(0).strip()
    number = re.sub(r"\D", "", raw)
    if raw.startswith("00"):
        number = number[2:]
    elif not raw.startswith("+") and len(number) == 10:
        number = f"{os.getenv('WHATSAPP_DEFAULT_COUNTRY_CODE', '91')}{number}"

    return number if 8 <= len(number) <= 15 else None


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    session_id, session = get_session(req.session_id)
    history = session["history"]

    history.append({"role": "user", "content": req.message})
    whatsapp_number = extract_whatsapp_number(req.message)
    if whatsapp_number:
        session["customer_whatsapp"] = whatsapp_number

    whatsapp_confirmation_queued = False
    if not session["booking_outcome_decided"] and looks_like_booking_attempt(req.message):
        session["booking_outcome_decided"] = True
        should_fail = req.force_booking_failure or random.random() < 0.3
        if should_fail:
            history.append({
                "role": "system",
                "content": (
                    "[SYSTEM NOTE: The site visit slot the customer just requested "
                    "could not be confirmed due to a booking system error. Apologize "
                    "briefly, do not blame the customer, and offer either an alternate "
                    "slot suggestion or a human coordinator callback so they have a "
                    "clear next step.]"
                ),
            })
        else:
            session["booking_confirmed"] = True
            session["booking_request"] = req.message
            history.append({
                "role": "system",
                "content": (
                    "[SYSTEM NOTE: The requested site visit is available. If the "
                    "customer has provided a WhatsApp number, the booking is now "
                    "confirmed and a WhatsApp confirmation will be queued. If they "
                    "have not provided one, ask them for their WhatsApp number before "
                    "saying the booking is confirmed.]"
                ),
            })

    if (
        session["booking_confirmed"]
        and session["customer_whatsapp"]
        and not session["whatsapp_confirmation_queued"]
        and whatsapp_notifications_ready()
    ):
        session["whatsapp_confirmation_queued"] = True
        whatsapp_confirmation_queued = True
        background_tasks.add_task(
            send_booking_confirmation,
            session_id=session_id,
            customer_whatsapp=session["customer_whatsapp"],
            booking_request=session["booking_request"],
        )
        history.append({
            "role": "system",
            "content": (
                "[SYSTEM NOTE: The site visit is confirmed and the customer's "
                "WhatsApp confirmation has been queued. Clearly confirm the date, "
                "time, location, and that the details are being sent on WhatsApp.]"
            ),
        })

    reply = chat_completion(history)
    history.append({"role": "assistant", "content": reply})

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        whatsapp_confirmation_queued=whatsapp_confirmation_queued,
    )


@app.post("/api/end")
def end_conversation(req: EndRequest):
    session = SESSIONS.get(req.session_id)
    if not session:
        return {"error": "session not found"}

    transcript_lines = []
    for m in session["history"]:
        if m["role"] == "user":
            transcript_lines.append(f"Customer: {m['content']}")
        elif m["role"] == "assistant":
            transcript_lines.append(f"Riya: {m['content']}")
    transcript = "\n".join(transcript_lines)

    messages = [
        {"role": "system", "content": ANALYTICS_PROMPT},
        {"role": "user", "content": transcript},
    ]
    raw = chat_completion(messages, temperature=0.1, json_mode=True)
    analytics = safe_json_parse(raw)
    return {"session_id": req.session_id, "analytics": analytics}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/health")
def health_check():
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    return {
        "status": "ok",
        "provider": provider,
        "model": os.getenv("GEMINI_MODEL" if provider == "gemini" else "OPENAI_MODEL", "default"),
        "api_key_configured": bool((os.getenv(key_name) or "").strip()),
    }


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")
