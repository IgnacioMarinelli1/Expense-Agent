from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from models.user import UserCreate
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid id: {value}")


@router.post("/", status_code=201)
async def create_user(body: UserCreate, request: Request):
    db = request.app.state.db
    existing = await db["users"].find_one({"phone": body.phone})
    if existing:
        return _serialize(existing)
    doc = body.model_dump()
    doc["created_at"] = datetime.utcnow()
    result = await db["users"].insert_one(doc)
    created = await db["users"].find_one({"_id": result.inserted_id})
    return _serialize(created)


@router.get("/{user_id}")
async def get_user(user_id: str, request: Request):
    db = request.app.state.db
    doc = await db["users"].find_one({"_id": _object_id(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize(doc)
