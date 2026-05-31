import os
from hashlib import sha256


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)


def current_user_id() -> str:
    return os.getenv("EXPENSE_AGENT_USER_ID", "demo_user").strip() or "demo_user"


def current_session_id(user_id: str | None = None) -> str:
    value = user_id or current_user_id()
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"session_{digest}"


def cors_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if not raw:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
