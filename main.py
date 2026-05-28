from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.db import get_db, close_connection
from helpers.db_helpers import safe_create_collection
from routes.health import router as health_router
from routes.summary import router as summary_router
from routes.payments import router as payments_router
from routes.users import router as users_router
from routes.frontend_compat import router as compat_router
from routes.agente import router as agente_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    app.state.db = db
    for collection in ("users", "properties", "services", "payments"):
        await safe_create_collection(db, collection)
    yield
    close_connection()


app = FastAPI(title="Expense Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(agente_router)
app.include_router(compat_router)
app.include_router(summary_router)   # before payments to avoid /{payment_id} clash
app.include_router(payments_router)
app.include_router(users_router)
