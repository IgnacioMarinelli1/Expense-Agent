from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from db.db import get_db

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
    doc = {
        "user_id": DEFAULT_USER,
        "amount": float(body.get("monto", 0)),
        "currency": "ARS",
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
    result = await db["payments"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_gasto(doc)


@router.patch("/gastos/{gasto_id}/pagar")
async def marcar_pagado(gasto_id: str):
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


@router.get("/resumen")
async def get_resumen(mes: Optional[str] = Query(None)):
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
