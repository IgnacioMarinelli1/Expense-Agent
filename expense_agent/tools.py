import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import get_db

# user_id is resolved server-side, never from model input
_USER_ID = "demo_user"


async def save_expense(
    amount: float,
    currency: str = "ARS",
    payment_date: str = None,
    due_date: str = None,
    notes: str = None,
    period: str = None,
    status: str = "pending",
    input_method: str = "manual",
    property_id: str = None,
) -> dict:
    """Guarda un gasto en la base de datos. Requerido: amount."""
    if amount <= 0:
        return {"status": "error", "error_message": "El monto debe ser mayor a 0"}
    db = get_db()
    doc = {
        "user_id": _USER_ID,
        "amount": amount,
        "currency": currency,
        "payment_date": datetime.fromisoformat(payment_date) if payment_date else datetime.utcnow(),
        "status": status,
        "input_method": input_method,
        "created_at": datetime.utcnow(),
    }
    if due_date:    doc["due_date"] = datetime.fromisoformat(due_date)
    if notes:       doc["notes"] = notes
    if period:      doc["period"] = period
    if property_id: doc["property_id"] = property_id

    result = await db["payments"].insert_one(doc)
    return {"status": "success", "payment_id": str(result.inserted_id)}


async def consultar_gastos(
    status: str = None,
    period: str = None,
    limit: int = 20,
) -> dict:
    """Lista los gastos del usuario. Filtros opcionales: status (pending/paid/overdue), period (YYYY-MM)."""
    db = get_db()
    query: dict = {"user_id": _USER_ID}
    if status: query["status"] = status
    if period: query["period"] = period

    cursor = db["payments"].find(query).sort("payment_date", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        for key in ("payment_date", "due_date", "created_at"):
            if key in doc and hasattr(doc[key], "isoformat"):
                doc[key] = doc[key].isoformat()
    return {"status": "success", "gastos": docs, "count": len(docs)}


async def consultar_gasto(payment_id: str) -> dict:
    """Obtiene un gasto específico por su ID de MongoDB."""
    from bson import ObjectId
    from bson.errors import InvalidId

    db = get_db()
    try:
        doc = await db["payments"].find_one({"_id": ObjectId(payment_id), "user_id": _USER_ID})
    except InvalidId:
        return {"status": "error", "error_message": f"ID inválido: {payment_id}"}
    if not doc:
        return {"status": "error", "error_message": "Gasto no encontrado"}
    doc["_id"] = str(doc["_id"])
    for key in ("payment_date", "due_date", "created_at"):
        if key in doc and hasattr(doc[key], "isoformat"):
            doc[key] = doc[key].isoformat()
    return {"status": "success", "gasto": doc}


async def get_monthly_summary(period: str) -> dict:
    """Resumen de gastos de un mes. period en formato YYYY-MM (ej: 2026-05)."""
    db = get_db()
    pipeline = [
        {"$match": {"user_id": _USER_ID, "period": period}},
        {"$group": {"_id": "$status", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {
            "$group": {
                "_id": None,
                "by_status": {"$push": {"status": "$_id", "total": "$total", "count": "$count"}},
                "grand_total": {"$sum": "$total"},
                "total_count": {"$sum": "$count"},
            }
        },
        {"$project": {"_id": 0}},
    ]
    results = await db["payments"].aggregate(pipeline).to_list(length=1)
    if not results:
        return {"status": "success", "period": period, "grand_total": 0, "total_count": 0, "by_status": []}
    return {"status": "success", "period": period, **results[0]}
