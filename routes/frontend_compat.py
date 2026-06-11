import asyncio
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from db.db import get_db
from db.security import current_user_id

router = APIRouter(tags=["frontend"])

CURRENT_YEAR = datetime.now().year


def _parse_date(date_str: str) -> Optional[datetime]:
    try:
        day, month = date_str.strip().split("/")
        return datetime(CURRENT_YEAR, int(month), int(day))
    except Exception:
        return None


def _fmt(dt) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return None
    return dt.strftime("%d/%m")


def _category(expense_type: str) -> str:
    t = expense_type.lower()
    if any(k in t for k in ["luz", "electr", "edesur", "edenor"]):
        return "luz"
    if any(k in t for k in ["gas", "metrogas", "camuzzi"]):
        return "gas"
    if any(k in t for k in ["agua", "aysa"]):
        return "agua"
    if any(k in t for k in ["abl", "impuest", "municipal", "tasa"]):
        return "impuesto"
    if any(k in t for k in ["expensa", "alquiler", "consorcio", "admin"]):
        return "expensas"
    if any(k in t for k in ["internet", "wifi", "tel", "cable", "movistar", "claro", "personal"]):
        return "telefonia"
    if any(k in t for k in ["netflix", "spotify", "chatgpt", "claude", "suscrip", "subscription", "youtube", "disney", "hbo", "prime", "icloud"]):
        return "subscription"
    if any(k in t for k in ["super", "mercado", "comida", "restaurant", "delivery", "cena", "almuerzo", "desayuno", "verdul", "carnicer", "panader", "cafe", "pancho", "pizza", "hamburg", "jamon", "jamón"]):
        return "comida"
    if any(k in t for k in ["uber", "taxi", "nafta", "sube", "colectivo", "tren", "peaje", "transporte", "cabify"]):
        return "transporte"
    if any(k in t for k in ["farmacia", "medic", "salud", "prepaga", "hospital", "dentista"]):
        return "salud"
    return "otros"


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

    return {
        "id": str(doc["_id"]),
        "type": expense_type,
        "category": _category(expense_type),
        "amount": doc.get("amount", 0),
        "currency": doc.get("currency", "ARS"),
        "date": _fmt(doc.get("payment_date")),
        "due_date": _fmt(doc.get("due_date")),
        "paid": doc.get("status") == "paid",
        "notes": metadata_notes if metadata_notes != expense_type else None,
    }


@router.get("/expenses")
async def get_expenses(month: Optional[str] = Query(None)):
    db = get_db()
    # Exclude income entries — those go to the "cobrado" card, not the expense list
    query: dict = {"user_id": current_user_id(), "type": {"$ne": "income"}}
    if month:
        query["period"] = month
    cursor = db["payments"].find(query).sort("payment_date", -1)
    docs = await cursor.to_list(length=100)
    return [_to_expense(doc) for doc in docs]


@router.post("/expenses", status_code=201)
async def create_expense(body: dict):
    db = get_db()
    payment_date = (_parse_date(body["date"]) if body.get("date") else None) or datetime.utcnow()
    doc = {
        "user_id": current_user_id(),
        "amount": float(body.get("amount", 0)),
        "currency": "ARS",
        "notes": body.get("type", ""),
        "status": "paid" if body.get("paid") else "pending",
        "payment_date": payment_date,
        "period": payment_date.strftime("%Y-%m"),
        "input_method": "manual",
        "created_at": datetime.utcnow(),
    }
    if body.get("due_date"):
        doc["due_date"] = _parse_date(body["due_date"])
    if body.get("notes"):
        doc["metadata"] = {"notas": body["notes"]}
    result = await db["payments"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_expense(doc)


@router.patch("/expenses/{expense_id}/pay")
async def mark_paid(expense_id: str):
    db = get_db()
    try:
        oid = ObjectId(expense_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db["payments"].update_one(
        {"_id": oid, "user_id": current_user_id()},
        {"$set": {"status": "paid"}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return {"ok": True}


@router.get("/finance")
async def get_finance(month: Optional[str] = Query(None)):
    db = get_db()
    user_id = current_user_id()
    period = month or datetime.utcnow().strftime("%Y-%m")

    doc, income_rows = await asyncio.gather(
        db["monthly_finances"].find_one({"user_id": user_id, "period": period}),
        db["payments"].aggregate([
            {"$match": {"user_id": user_id, "period": period, "type": "income"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]).to_list(length=1),
    )

    cobrado = income_rows[0]["total"] if income_rows else 0.0

    if not doc:
        return {"period": period, "salary": None, "budget": None, "cobrado": cobrado, "currency": "ARS", "notes": None}
    return {
        "period": period,
        "salary": doc.get("salary"),
        "budget": doc.get("budget"),
        "cobrado": cobrado,
        "currency": doc.get("currency", "ARS"),
        "notes": doc.get("notes"),
    }


@router.get("/income")
async def get_income(month: Optional[str] = Query(None)):
    db = get_db()
    query: dict = {"user_id": current_user_id(), "type": "income"}
    if month:
        query["period"] = month
    cursor = db["payments"].find(query).sort("payment_date", -1)
    docs = await cursor.to_list(length=100)
    return [
        {
            "id": str(doc["_id"]),
            "description": doc.get("notes") or "Ingreso",
            "amount": doc.get("amount", 0),
            "currency": doc.get("currency", "ARS"),
            "date": _fmt(doc.get("payment_date")),
            "period": doc.get("period"),
        }
        for doc in docs
    ]


@router.get("/fx")
async def get_fx():
    """Cotizaciones para que el frontend convierta entre monedas al vuelo.
    `rates` son ARS por 1 unidad de la moneda (ARS=1, USD=blue venta)."""
    from expense_agent.charting import _fetch_fx_rates

    rates = await _fetch_fx_rates()
    return {
        "base": "ARS",
        "rates": rates,
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/summary")
async def get_summary(month: Optional[str] = Query(None)):
    db = get_db()
    match: dict = {"user_id": current_user_id()}
    if month:
        match["period"] = month
    # Agrupamos por moneda: sumar montos de distintas monedas en crudo no tiene
    # sentido. El frontend convierte cada moneda a la de visualizacion.
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"$ifNull": ["$currency", "ARS"]},
                "total": {"$sum": "$amount"},
                "paid": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, "$amount", 0]}},
                "pending": {"$sum": {"$cond": [{"$ne": ["$status", "paid"]}, "$amount", 0]}},
                "payments_count": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}},
                "pending_count": {"$sum": {"$cond": [{"$ne": ["$status", "paid"]}, 1, 0]}},
            }
        },
    ]
    rows = await db["payments"].aggregate(pipeline).to_list(length=20)

    by_currency: dict = {}
    total = paid = pending = payments_count = pending_count = 0
    for row in rows:
        currency = row["_id"] or "ARS"
        by_currency[currency] = {
            "total": row["total"],
            "paid": row["paid"],
            "pending": row["pending"],
        }
        # `total` legacy = suma cruda (se mantiene por compatibilidad).
        total += row["total"]
        paid += row["paid"]
        pending += row["pending"]
        payments_count += row["payments_count"]
        pending_count += row["pending_count"]

    return {
        "total": total,
        "paid": paid,
        "pending": pending,
        "payments_count": payments_count,
        "pending_count": pending_count,
        "by_currency": by_currency,
    }
