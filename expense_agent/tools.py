import os
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import get_db
<<<<<<< Updated upstream
=======
from db.security import current_user_id
from helpers.categorizer import categorize, is_known_category
>>>>>>> Stashed changes

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
    service_id: str = None,
    property_id: str = None,
    category: str = None,
) -> dict:
<<<<<<< Updated upstream
    """Guarda un gasto en la base de datos. Requerido: amount."""
=======
    """Guarda un gasto en la base de datos. Requerido: amount.
    Retorna status 'duplicate' si el pago ya existe — en ese caso NO reintentar.

    category (opcional): bucket canónico para el gasto. Valores:
    'luz', 'gas', 'agua', 'impuesto', 'expensas', 'telefonia',
    'subscription', 'comida', 'transporte', 'salud', 'otros'.
    Si no se pasa, se infiere automáticamente desde notes."""
>>>>>>> Stashed changes
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
    if service_id:  doc["service_id"] = service_id
    if property_id: doc["property_id"] = property_id

    # Persist a canonical category. Prefer the explicit value when valid,
    # otherwise infer it from notes so legacy/manual calls also produce
    # categorized rows for the UI to color correctly.
    resolved_category: str | None = None
    if category and is_known_category(category.strip().lower()):
        resolved_category = category.strip().lower()
    elif notes:
        resolved_category = categorize(notes)
    if resolved_category:
        doc["category"] = resolved_category

    result = await db["payments"].insert_one(doc)
    return {"status": "success", "payment_id": str(result.inserted_id)}


async def save_service(
    name: str,
    category: str,
    provider: str = None,
    recurring_amount: float = None,
    currency: str = "ARS",
    billing_frequency: str = "monthly",
    default_due_day: int = None,
    property_id: str = None,
    account_number: str = None,
    notes: str = None,
    active: bool = True,
) -> dict:
    """Crea o actualiza un servicio recurrente/suscripción. Usar para obligaciones periódicas, no para gastos únicos."""
    if not name or not name.strip():
        return {"status": "error", "error_message": "El nombre del servicio es requerido"}
    if not category or not category.strip():
        return {"status": "error", "error_message": "La categoría del servicio es requerida"}

    db = get_db()
    normalized_name = name.strip().lower()
    now = datetime.utcnow()
    doc: dict[str, Any] = {
        "user_id": _USER_ID,
        "name": name.strip(),
        "normalized_name": normalized_name,
        "category": category.strip().lower(),
        "provider": provider.strip() if provider else name.strip(),
        "billing_frequency": billing_frequency,
        "currency": currency,
        "active": active,
        "updated_at": now,
    }
    metadata: dict[str, Any] = {}
    if recurring_amount is not None:
        if recurring_amount <= 0:
            return {"status": "error", "error_message": "El monto recurrente debe ser mayor a 0"}
        metadata["recurring_amount"] = recurring_amount
    if notes:
        metadata["notes"] = notes
    if metadata:
        doc["metadata"] = metadata
    if default_due_day:
        doc["default_due_day"] = default_due_day
    if property_id:
        doc["property_id"] = property_id
    if account_number:
        doc["account_number"] = account_number

    result = await db["services"].update_one(
        {"user_id": _USER_ID, "normalized_name": normalized_name},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    saved = await db["services"].find_one({"user_id": _USER_ID, "normalized_name": normalized_name})
    return {
        "status": "success",
        "service_id": str(saved["_id"]),
        "created": bool(result.upserted_id),
    }


async def consultar_servicios(
    category: str = None,
    active: bool = True,
    limit: int = 20,
) -> dict:
    """Lista servicios recurrentes/suscripciones del usuario. Filtros opcionales: category y active."""
    db = get_db()
    query: dict[str, Any] = {"user_id": _USER_ID}
    if category:
        query["category"] = category.strip().lower()
    if active is not None:
        query["active"] = active

    cursor = db["services"].find(query).sort("name", 1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        for key in ("created_at", "updated_at"):
            if key in doc and hasattr(doc[key], "isoformat"):
                doc[key] = doc[key].isoformat()
    return {"status": "success", "servicios": docs, "count": len(docs)}


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
<<<<<<< Updated upstream
    return {"status": "success", "gasto": doc}
=======
    return {"status": "success", "expense": doc}


async def update_expense(
    payment_id: str,
    status: str = None,
    amount: float = None,
    notes: str = None,
    payment_date: str = None,
    category: str = None,
) -> dict:
    """Actualiza un gasto existente por su ID. Usá esta tool para marcar pagos como 'paid', corregir montos, notas o categoría.
    status puede ser: 'paid', 'pending', 'overdue'.
    category (opcional): 'luz', 'gas', 'agua', 'impuesto', 'expensas', 'telefonia',
    'subscription', 'comida', 'transporte', 'salud', 'otros'.
    Solo se actualizan los campos que se pasen explícitamente."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from datetime import datetime

    if not any([status, amount, notes, payment_date, category]):
        return {"status": "error", "error_message": "Debés indicar al menos un campo para actualizar."}

    db = get_db()
    update: dict[str, Any] = {}
    if status:
        update["status"] = status
    if amount is not None:
        if amount <= 0:
            return {"status": "error", "error_message": "El monto debe ser mayor a 0."}
        update["amount"] = amount
    if notes:
        update["notes"] = notes
        # Re-infer category when notes change unless caller passes one explicitly.
        if not category:
            update["category"] = categorize(notes)
    if payment_date:
        update["payment_date"] = datetime.fromisoformat(payment_date)
    if category:
        normalized = category.strip().lower()
        if is_known_category(normalized):
            update["category"] = normalized

    try:
        result = await db["payments"].update_one(
            {"_id": ObjectId(payment_id), "user_id": current_user_id()},
            {"$set": update},
        )
    except InvalidId:
        return {"status": "error", "error_message": f"ID inválido: {payment_id}"}

    if result.matched_count == 0:
        return {"status": "error", "error_message": "Gasto no encontrado."}
    return {"status": "success", "updated_fields": list(update.keys())}
>>>>>>> Stashed changes


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
