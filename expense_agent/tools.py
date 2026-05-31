import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.db import get_db
from db.security import current_user_id

# user_id is resolved server-side, never from model input
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _is_valid_period(period: str) -> bool:
    return bool(period and _PERIOD_RE.match(period))


def _serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    for key, value in list(serialized.items()):
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
    return serialized


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
) -> dict:
    """Guarda un gasto en la base de datos. Requerido: amount.
    Retorna status 'duplicate' si el pago ya existe — en ese caso NO reintentar."""
    if amount <= 0:
        return {"status": "error", "error_message": "El monto debe ser mayor a 0"}

    db = get_db()
    now = datetime.utcnow()
    user_id = current_user_id()

    # Dedup: build the narrowest possible query to detect an existing payment.
    # Priority: service+period (most specific) > notes+period > notes+recent window.
    if service_id and period:
        dedup_q = {"user_id": user_id, "service_id": service_id, "period": period}
    elif notes and period:
        dedup_q = {"user_id": user_id, "amount": amount, "currency": currency,
                   "notes": notes, "period": period}
    elif notes:
        dedup_q = {"user_id": user_id, "amount": amount, "currency": currency,
                   "notes": notes, "created_at": {"$gte": now - timedelta(minutes=10)}}
    else:
        dedup_q = {"user_id": user_id, "amount": amount, "currency": currency,
                   "created_at": {"$gte": now - timedelta(minutes=5)}}

    existing = await db["payments"].find_one(dedup_q)
    if existing:
        return {
            "status": "duplicate",
            "payment_id": str(existing["_id"]),
            "message": "Este pago ya existe. No se volvió a registrar.",
        }

    doc = {
        "user_id": user_id,
        "amount": amount,
        "currency": currency,
        "payment_date": datetime.fromisoformat(payment_date) if payment_date else now,
        "status": status,
        "input_method": input_method,
        "created_at": now,
    }
    if due_date:    doc["due_date"] = datetime.fromisoformat(due_date)
    if notes:       doc["notes"] = notes
    if period:      doc["period"] = period
    if service_id:  doc["service_id"] = service_id
    if property_id: doc["property_id"] = property_id

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
    total_installments: int = None,
    current_installment: int = None,
    start_date: str = None,
) -> dict:
    """Crea o actualiza un servicio recurrente/suscripción. Usar para obligaciones periódicas, no para gastos únicos.

    Para compras en cuotas usar:
    - total_installments: cantidad total de cuotas (ej: 12).
    - current_installment: número de cuota actual (ej: 3). Default 1 si no se especifica.
    - start_date: fecha de inicio del plan en formato YYYY-MM-DD.
    """
    if not name or not name.strip():
        return {"status": "error", "error_message": "El nombre del servicio es requerido"}
    if not category or not category.strip():
        return {"status": "error", "error_message": "La categoría del servicio es requerida"}

    db = get_db()
    normalized_name = name.strip().lower()
    now = datetime.now(timezone.utc)
    user_id = current_user_id()
    doc: dict[str, Any] = {
        "user_id": user_id,
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
    if total_installments is not None:
        metadata["total_installments"] = total_installments
        metadata["current_installment"] = current_installment or 1
        metadata["remaining_installments"] = total_installments - (current_installment or 1)
        if start_date:
            metadata["start_date"] = start_date
    if metadata:
        doc["metadata"] = metadata
    if default_due_day:
        doc["default_due_day"] = default_due_day
    if property_id:
        doc["property_id"] = property_id
    if account_number:
        doc["account_number"] = account_number

    result = await db["services"].update_one(
        {"user_id": user_id, "normalized_name": normalized_name},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    saved = await db["services"].find_one({"user_id": user_id, "normalized_name": normalized_name})
    response = {
        "status": "success",
        "service_id": str(saved["_id"]),
        "created": bool(result.upserted_id),
    }
    if total_installments:
        remaining = total_installments - (current_installment or 1)
        response["installments_info"] = f"Cuota {current_installment or 1} de {total_installments} — quedan {remaining}"
    return response


async def get_services(
    category: str = None,
    active: bool = True,
    limit: int = 20,
) -> dict:
    """Lista servicios recurrentes/suscripciones del usuario. Filtros opcionales: category y active."""
    db = get_db()
    query: dict[str, Any] = {"user_id": current_user_id()}
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
    return {"status": "success", "services": docs, "count": len(docs)}


async def get_expenses(
    status: str = None,
    period: str = None,
    limit: int = 20,
) -> dict:
    """Lista los gastos del usuario. Filtros opcionales: status (pending/paid/overdue), period (YYYY-MM)."""
    db = get_db()
    query: dict = {"user_id": current_user_id()}
    if status: query["status"] = status
    if period: query["period"] = period

    cursor = db["payments"].find(query).sort("payment_date", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        for key in ("payment_date", "due_date", "created_at"):
            if key in doc and hasattr(doc[key], "isoformat"):
                doc[key] = doc[key].isoformat()
    return {"status": "success", "expenses": docs, "count": len(docs)}


async def get_expense(payment_id: str) -> dict:
    """Obtiene un gasto específico por su ID de MongoDB."""
    from bson import ObjectId
    from bson.errors import InvalidId

    db = get_db()
    try:
        doc = await db["payments"].find_one({"_id": ObjectId(payment_id), "user_id": current_user_id()})
    except InvalidId:
        return {"status": "error", "error_message": f"ID inválido: {payment_id}"}
    if not doc:
        return {"status": "error", "error_message": "Gasto no encontrado"}
    doc["_id"] = str(doc["_id"])
    for key in ("payment_date", "due_date", "created_at"):
        if key in doc and hasattr(doc[key], "isoformat"):
            doc[key] = doc[key].isoformat()
    return {"status": "success", "expense": doc}


async def get_monthly_summary(period: str) -> dict:
    """Resumen de gastos de un mes. period en formato YYYY-MM (ej: 2026-05)."""
    db = get_db()
    pipeline = [
        {"$match": {"user_id": current_user_id(), "period": period}},
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


async def save_monthly_finance(
    period: str,
    salary: float = None,
    budget: float = None,
    currency: str = "ARS",
    notes: str = None,
) -> dict:
    """Guarda o actualiza sueldo y presupuesto mensual. period debe ser YYYY-MM."""
    if not _is_valid_period(period):
        return {"status": "error", "error_message": "El período debe tener formato YYYY-MM"}
    if salary is None and budget is None and notes is None:
        return {"status": "error", "error_message": "Indicá al menos sueldo, presupuesto o notas para guardar"}
    if salary is not None and salary < 0:
        return {"status": "error", "error_message": "El sueldo no puede ser negativo"}
    if budget is not None and budget < 0:
        return {"status": "error", "error_message": "El presupuesto no puede ser negativo"}

    now = datetime.now(timezone.utc)
    update: dict[str, Any] = {
        "currency": currency,
        "updated_at": now,
    }
    if salary is not None:
        update["salary"] = salary
    if budget is not None:
        update["budget"] = budget
    if notes is not None:
        update["notes"] = notes

    db = get_db()
    user_id = current_user_id()
    result = await db["monthly_finances"].update_one(
        {"user_id": user_id, "period": period},
        {"$set": update, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    saved = await db["monthly_finances"].find_one({"user_id": user_id, "period": period})
    return {
        "status": "success",
        "monthly_finance": _serialize_doc(saved),
        "created": bool(result.upserted_id),
    }


async def get_monthly_finance(period: str) -> dict:
    """Consulta sueldo y presupuesto guardados para un período YYYY-MM."""
    if not _is_valid_period(period):
        return {"status": "error", "error_message": "El período debe tener formato YYYY-MM"}
    db = get_db()
    doc = await db["monthly_finances"].find_one({"user_id": current_user_id(), "period": period})
    return {"status": "success", "period": period, "monthly_finance": _serialize_doc(doc)}


async def get_monthly_finance_summary(period: str) -> dict:
    """Compara gastos del mes contra sueldo y presupuesto guardados."""
    if not _is_valid_period(period):
        return {"status": "error", "error_message": "El período debe tener formato YYYY-MM"}

    db = get_db()
    user_id = current_user_id()
    finance_doc = await db["monthly_finances"].find_one({"user_id": user_id, "period": period})
    cursor = db["payments"].find({"user_id": user_id, "period": period})
    payments = await cursor.to_list(length=1000)

    paid_total = 0.0
    pending_total = 0.0
    overdue_total = 0.0
    for payment in payments:
        amount = float(payment.get("amount") or 0)
        status = payment.get("status")
        if status == "paid":
            paid_total += amount
        elif status == "overdue":
            overdue_total += amount
            pending_total += amount
        elif status == "pending":
            pending_total += amount
        else:
            paid_total += amount

    spent_total = paid_total + pending_total
    finance = _serialize_doc(finance_doc)
    budget = float(finance_doc.get("budget")) if finance_doc and finance_doc.get("budget") is not None else None
    salary = float(finance_doc.get("salary")) if finance_doc and finance_doc.get("salary") is not None else None

    return {
        "status": "success",
        "period": period,
        "monthly_finance": finance,
        "spent_total": round(spent_total, 2),
        "paid_total": round(paid_total, 2),
        "pending_total": round(pending_total, 2),
        "overdue_total": round(overdue_total, 2),
        "payments_count": len(payments),
        "budget_remaining": round(budget - spent_total, 2) if budget is not None else None,
        "salary_remaining_after_spend": round(salary - spent_total, 2) if salary is not None else None,
        "budget_usage_pct": round((spent_total / budget) * 100, 2) if budget else None,
    }
