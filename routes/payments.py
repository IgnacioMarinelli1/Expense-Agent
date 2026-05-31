from fastapi import APIRouter, Request, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId
from models.payment import PaymentCreate, PaymentUpdate
from datetime import datetime
from typing import Optional
from db.security import current_user_id

router = APIRouter(prefix="/payments", tags=["payments"])


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid id: {value}")


@router.post("/", status_code=201)
async def create_payment(body: PaymentCreate, request: Request):
    db = request.app.state.db
    doc = body.model_dump(exclude_none=True)
    doc["user_id"] = current_user_id()
    doc["created_at"] = datetime.utcnow()
    result = await db["payments"].insert_one(doc)
    created = await db["payments"].find_one({"_id": result.inserted_id})
    return _serialize(created)


@router.get("/")
async def list_payments(
    request: Request,
    property_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
):
    db = request.app.state.db
    active_user_id = current_user_id()
    query: dict = {"user_id": active_user_id}
    if property_id:
        query["property_id"] = property_id
    if status:
        query["status"] = status
    if from_date or to_date:
        date_filter: dict = {}
        if from_date:
            date_filter["$gte"] = from_date
        if to_date:
            date_filter["$lte"] = to_date
        query["payment_date"] = date_filter

    cursor = db["payments"].find(query).sort("payment_date", -1)
    return [_serialize(doc) async for doc in cursor]


@router.get("/{payment_id}")
async def get_payment(payment_id: str, request: Request):
    db = request.app.state.db
    doc = await db["payments"].find_one(
        {"_id": _object_id(payment_id), "user_id": current_user_id()}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    return _serialize(doc)


@router.put("/{payment_id}")
async def update_payment(payment_id: str, body: PaymentUpdate, request: Request):
    db = request.app.state.db
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db["payments"].update_one(
        {"_id": _object_id(payment_id), "user_id": current_user_id()}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    doc = await db["payments"].find_one(
        {"_id": _object_id(payment_id), "user_id": current_user_id()}
    )
    return _serialize(doc)


@router.delete("/{payment_id}")
async def delete_payment(payment_id: str, request: Request):
    db = request.app.state.db
    result = await db["payments"].delete_one(
        {"_id": _object_id(payment_id), "user_id": current_user_id()}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"deleted": payment_id}
