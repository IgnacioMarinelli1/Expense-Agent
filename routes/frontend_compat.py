from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from db.db import get_db
<<<<<<< Updated upstream
=======
from db.security import current_user_id
from helpers.categorizer import categorize, is_known_category
>>>>>>> Stashed changes

router = APIRouter(tags=["frontend"])

DEFAULT_USER = "demo_user"
CURRENT_YEAR = datetime.now().year


def _parse_fecha(fecha: str) -> Optional[datetime]:
    try:
        day, month = fecha.strip().split("/")
        return datetime(CURRENT_YEAR, int(month), int(day))
    except Exception:
        return None


def _fmt(dt) -> Optional[str]:
    return dt.strftime("%d/%m") if dt else None


<<<<<<< Updated upstream
def _categoria(tipo: str) -> str:
    t = tipo.lower()
    if any(k in t for k in ["luz", "electr", "edesur", "edenor"]):
        return "luz"
    if any(k in t for k in ["gas", "metrogas", "camuzzi"]):
        return "gas"
    if any(k in t for k in ["agua", "aysa"]):
        return "agua"
    if any(k in t for k in ["abl", "impuest", "municipal", "tasa"]):
        return "impuesto"
    if any(k in t for k in ["expensa", "admin"]):
        return "expensas"
    if any(k in t for k in ["internet", "wifi", "tel", "cable", "movistar", "claro", "personal"]):
        return "telefonia"
    return "expensas"


def _to_gasto(doc: dict) -> dict:
    tipo = doc.get("notes") or "Gasto"
    return {
        "id": str(doc["_id"]),
        "tipo": tipo,
        "categoria": _categoria(tipo),
        "monto": doc.get("amount", 0),
        "fecha": _fmt(doc.get("payment_date")),
        "vencimiento": _fmt(doc.get("due_date")),
        "pagado": doc.get("status") == "paid",
        "notas": (doc.get("metadata") or {}).get("notas"),
    }


@router.get("/gastos")
async def get_gastos(mes: Optional[str] = Query(None)):
=======
def _category(expense_type: str) -> str:
    """Legacy keyword-based category resolver.

    Kept for backward compatibility: older payments stored without a
    `category` field still get categorized at read-time. New writes prefer
    the explicit `category` value provided by the agent or the manual form.
    """
    return categorize(expense_type)


def _to_expense(doc: dict) -> dict:
    metadata_notes = (doc.get("metadata") or {}).get("notas")
    notes_field = doc.get("notes")

    if notes_field:
        expense_type = notes_field
    elif metadata_notes:
        expense_type = metadata_notes
    else:
        currency = doc.get("currency", "ARS")
        expense_type = f"Gasto {currency}" if currency != "ARS" else "Gasto sin descripción"

    stored_category = doc.get("category")
    if is_known_category(stored_category):
        category = stored_category
    else:
        category = categorize(expense_type, metadata_notes)

    return {
        "id": str(doc["_id"]),
        "type": expense_type,
        "category": category,
        "amount": doc.get("amount", 0),
        "date": _fmt(doc.get("payment_date")),
        "due_date": _fmt(doc.get("due_date")),
        "paid": doc.get("status") == "paid",
        "notes": metadata_notes if metadata_notes != expense_type else None,
    }


def _resolve_category(body: dict, expense_type: str, notes_text: Optional[str]) -> str:
    """Pick the category for a write. Prefer an explicit, valid value from the
    client; otherwise infer it from the free-form text."""
    explicit = (body.get("category") or "").strip().lower()
    if is_known_category(explicit):
        return explicit
    return categorize(expense_type, notes_text)


@router.get("/expenses")
async def get_expenses(month: Optional[str] = Query(None)):
>>>>>>> Stashed changes
    db = get_db()
    query: dict = {"user_id": DEFAULT_USER}
    if mes:
        query["period"] = mes
    cursor = db["payments"].find(query).sort("payment_date", -1)
    docs = await cursor.to_list(length=100)
    return [_to_gasto(doc) for doc in docs]


@router.post("/gastos", status_code=201)
async def crear_gasto(body: dict):
    db = get_db()
    expense_type = body.get("type", "") or ""
    user_notes = body.get("notes")
    category = _resolve_category(body, expense_type, user_notes)

    doc = {
        "user_id": DEFAULT_USER,
        "amount": float(body.get("monto", 0)),
        "currency": "ARS",
<<<<<<< Updated upstream
        "notes": body.get("tipo", ""),
        "status": "paid" if body.get("pagado") else "pending",
        "payment_date": _parse_fecha(body["fecha"]) if body.get("fecha") else datetime.utcnow(),
        "input_method": "manual",
        "created_at": datetime.utcnow(),
    }
    if body.get("vencimiento"):
        doc["due_date"] = _parse_fecha(body["vencimiento"])
    if body.get("notas"):
        doc["metadata"] = {"notas": body["notas"]}
=======
        "notes": expense_type,
        "category": category,
        "status": "paid" if body.get("paid") else "pending",
        "payment_date": _parse_date(body["date"]) if body.get("date") else datetime.utcnow(),
        "input_method": "manual",
        "created_at": datetime.utcnow(),
    }
    if body.get("due_date"):
        doc["due_date"] = _parse_date(body["due_date"])
    if user_notes:
        doc["metadata"] = {"notas": user_notes}
>>>>>>> Stashed changes
    result = await db["payments"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_gasto(doc)


<<<<<<< Updated upstream
@router.patch("/gastos/{gasto_id}/pagar")
async def marcar_pagado(gasto_id: str):
=======
@router.put("/expenses/{expense_id}")
async def update_expense(expense_id: str, body: dict):
    """Update an existing expense using the same UI-friendly shape as POST.

    All fields are optional; only the keys present in the body get updated.
    Passing an unknown or empty `category` triggers server-side re-inference
    from `type` + `notes` so manual edits stay consistent with the agent.
    """
    db = get_db()
    try:
        oid = ObjectId(expense_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")

    update: dict = {}
    unset: dict = {}

    if "amount" in body and body["amount"] is not None:
        try:
            amount = float(body["amount"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Monto inválido")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        update["amount"] = amount

    if "type" in body and body["type"] is not None:
        update["notes"] = str(body["type"])

    if "paid" in body:
        update["status"] = "paid" if body["paid"] else "pending"

    if "date" in body and body["date"]:
        parsed = _parse_date(body["date"])
        if parsed:
            update["payment_date"] = parsed

    if "due_date" in body:
        if body["due_date"]:
            parsed = _parse_date(body["due_date"])
            if parsed:
                update["due_date"] = parsed
        else:
            unset["due_date"] = ""

    if "notes" in body:
        if body["notes"]:
            update["metadata.notas"] = str(body["notes"])
        else:
            unset["metadata.notas"] = ""

    # Category: explicit-and-valid wins; otherwise re-infer if type/notes changed.
    explicit_category = (body.get("category") or "").strip().lower() if "category" in body else ""
    if explicit_category and is_known_category(explicit_category):
        update["category"] = explicit_category
    elif "type" in body or "notes" in body:
        expense_type = body.get("type") or ""
        user_notes = body.get("notes") or ""
        inferred = categorize(expense_type, user_notes)
        update["category"] = inferred

    if not update and not unset:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    mongo_update: dict = {}
    if update:
        mongo_update["$set"] = update
    if unset:
        mongo_update["$unset"] = unset

    result = await db["payments"].update_one(
        {"_id": oid, "user_id": current_user_id()},
        mongo_update,
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    doc = await db["payments"].find_one({"_id": oid, "user_id": current_user_id()})
    return _to_expense(doc)


@router.patch("/expenses/{expense_id}/pay")
async def mark_paid(expense_id: str):
>>>>>>> Stashed changes
    db = get_db()
    try:
        oid = ObjectId(gasto_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db["payments"].update_one(
        {"_id": oid, "user_id": DEFAULT_USER},
        {"$set": {"status": "paid"}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"ok": True}


<<<<<<< Updated upstream
@router.get("/resumen")
async def get_resumen(mes: Optional[str] = Query(None)):
=======
@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str):
    db = get_db()
    try:
        oid = ObjectId(expense_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db["payments"].delete_one(
        {"_id": oid, "user_id": current_user_id()}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"deleted": expense_id}


@router.get("/summary")
async def get_summary(month: Optional[str] = Query(None)):
>>>>>>> Stashed changes
    db = get_db()
    match: dict = {"user_id": DEFAULT_USER}
    if mes:
        match["period"] = mes
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"},
                "pagado": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, "$amount", 0]}},
                "pendiente": {"$sum": {"$cond": [{"$ne": ["$status", "paid"]}, "$amount", 0]}},
                "cantidad_pagos": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}},
                "cantidad_pendientes": {"$sum": {"$cond": [{"$ne": ["$status", "paid"]}, 1, 0]}},
            }
        },
        {"$project": {"_id": 0}},
    ]
    results = await db["payments"].aggregate(pipeline).to_list(length=1)
    if not results:
        return {"total": 0, "pagado": 0, "pendiente": 0, "cantidad_pagos": 0, "cantidad_pendientes": 0}
    return results[0]
