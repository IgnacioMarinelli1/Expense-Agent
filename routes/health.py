from fastapi import APIRouter
from db.db import verify_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    db_ok = await verify_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "unreachable",
    }
