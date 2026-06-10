from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Query, Request

from db.db import get_db
from db.security import current_user_id
from models.dashboard import DashboardResponse


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

CATEGORY_LABELS = (
    "Comida / Supermercado",
    "Transporte",
    "Servicios",
    "Vivienda",
    "Salud",
    "Educacion",
    "Ocio",
    "Ropa",
    "Deudas / cuotas",
    "Ahorro / inversion",
    "Otros",
)

CATEGORY_COLORS = {
    "Comida / Supermercado": "#22c55e",
    "Transporte": "#3b82f6",
    "Servicios": "#06b6d4",
    "Vivienda": "#8b5cf6",
    "Salud": "#ef4444",
    "Educacion": "#f59e0b",
    "Ocio": "#ec4899",
    "Ropa": "#14b8a6",
    "Deudas / cuotas": "#f97316",
    "Ahorro / inversion": "#10b981",
    "Otros": "#64748b",
}

SERVICE_CATEGORY_MAP = {
    "subscription": "Ocio",
    "utility": "Servicios",
    "utilities": "Servicios",
    "tax": "Servicios",
    "housing": "Vivienda",
    "rent": "Vivienda",
    "insurance": "Salud",
    "loan": "Deudas / cuotas",
    "education": "Educacion",
    "savings": "Ahorro / inversion",
    "investment": "Ahorro / inversion",
}


def _current_period() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def _previous_period(period: str) -> str:
    year, month = [int(part) for part in period.split("-")]
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def _days_in_period(period: str) -> int:
    year, month = [int(part) for part in period.split("-")]
    return calendar.monthrange(year, month)[1]


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    year, month = [int(part) for part in period.split("-")]
    start = datetime(year, month, 1)
    if month == 12:
        return start, datetime(year + 1, 1, 1)
    return start, datetime(year, month + 1, 1)


def _payment_period_query(user_id: str, period: str) -> dict[str, Any]:
    start, end = _period_bounds(period)
    by_date = {"payment_date": {"$gte": start, "$lt": end}}
    return {
        "user_id": user_id,
        "$or": [
            {"period": period},
            {"period": {"$exists": False}, **by_date},
            {"period": None, **by_date},
            {"period": "", **by_date},
        ],
    }


def _analysis_day_count(period: str) -> int:
    today = date.today()
    current = f"{today.year}-{today.month:02d}"
    if period == current:
        return max(1, today.day)
    return _days_in_period(period)


def _round_money(value: float | int | None) -> float:
    return round(float(value or 0), 2)


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _iso_date(value: Any, fallback: datetime | None = None) -> str:
    dt = _as_datetime(value) or fallback or datetime.utcnow()
    return dt.date().isoformat()


def _iso_datetime(value: Any) -> str | None:
    dt = _as_datetime(value)
    return dt.isoformat() if dt else None


def _doc_id(doc: dict[str, Any]) -> str:
    return str(doc.get("_id") or doc.get("id") or "")


def _service_key(value: Any) -> str:
    return str(value or "")


def _normalized_category(raw: Any, description: str = "") -> str:
    text = str(raw or "").strip()
    if text in CATEGORY_LABELS:
        return text
    lowered = text.lower()
    if lowered in SERVICE_CATEGORY_MAP:
        return SERVICE_CATEGORY_MAP[lowered]

    haystack = f"{lowered} {description.lower()}"
    if any(k in haystack for k in ("super", "mercado", "comida", "restaurant", "delivery", "verduleria", "cafe")):
        return "Comida / Supermercado"
    if any(k in haystack for k in ("taxi", "uber", "nafta", "sube", "colectivo", "tren", "transporte")):
        return "Transporte"
    if any(k in haystack for k in ("luz", "gas", "agua", "internet", "telefono", "electric", "wifi", "edenor", "edesur")):
        return "Servicios"
    if any(
        k in haystack
        for k in (
            "alquiler",
            "expensa",
            "renta",
            "rentas",
            "inmueble",
            "consorcio",
            "administracion",
            "admin",
            "departamento",
            "depto",
            "abl",
            "vivienda",
            "hipoteca",
        )
    ):
        return "Vivienda"
    if any(k in haystack for k in ("farmacia", "medico", "salud", "prepaga", "hospital")):
        return "Salud"
    if any(k in haystack for k in ("curso", "educacion", "universidad", "colegio", "libro")):
        return "Educacion"
    if any(k in haystack for k in ("cine", "bar", "netflix", "spotify", "ocio", "juego", "gaming")):
        return "Ocio"
    if any(k in haystack for k in ("ropa", "zapatilla", "indumentaria")):
        return "Ropa"
    if any(k in haystack for k in ("deuda", "cuota", "prestamo", "tarjeta")):
        return "Deudas / cuotas"
    if any(k in haystack for k in ("ahorro", "inversion", "fci", "plazo fijo")):
        return "Ahorro / inversion"
    return "Otros"


def _payment_description(doc: dict[str, Any]) -> str:
    metadata = doc.get("metadata") or {}
    return str(doc.get("notes") or metadata.get("notas") or metadata.get("notes") or "Gasto sin descripcion")


def _payment_category(doc: dict[str, Any], service_map: dict[str, dict[str, Any]]) -> str:
    description = _payment_description(doc)
    if doc.get("category"):
        return _normalized_category(doc.get("category"), description)
    service = service_map.get(_service_key(doc.get("service_id")))
    if service:
        return _normalized_category(service.get("category"), description)
    return _normalized_category(None, description)


def _payment_is_fixed(doc: dict[str, Any], service_map: dict[str, dict[str, Any]]) -> bool:
    if doc.get("is_fixed") is not None:
        return bool(doc.get("is_fixed"))
    return _service_key(doc.get("service_id")) in service_map


def _payment_to_movement(doc: dict[str, Any], service_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    description = _payment_description(doc)
    category = _payment_category(doc, service_map)
    service = service_map.get(_service_key(doc.get("service_id"))) or {}
    return {
        "id": _doc_id(doc),
        "fecha": _iso_date(doc.get("payment_date"), _as_datetime(doc.get("created_at"))),
        "tipo": "gasto",
        "categoria": category,
        "subcategoria": doc.get("subcategory") or service.get("name"),
        "descripcion": description,
        "medioPago": doc.get("payment_method") or doc.get("input_method"),
        "cuenta": doc.get("account"),
        "monto": _round_money(doc.get("amount")),
        "esFijo": _payment_is_fixed(doc, service_map),
        "createdAt": _iso_datetime(doc.get("created_at")),
        "updatedAt": _iso_datetime(doc.get("updated_at")),
    }


def _income_movement(period: str, finance_doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not finance_doc or not finance_doc.get("salary"):
        return None
    return {
        "id": f"income-{period}",
        "fecha": f"{period}-01",
        "tipo": "ingreso",
        "categoria": "Ingresos",
        "subcategoria": "Sueldo",
        "descripcion": "Ingreso mensual",
        "medioPago": None,
        "cuenta": None,
        "monto": _round_money(finance_doc.get("salary")),
        "esFijo": True,
        "createdAt": _iso_datetime(finance_doc.get("created_at")),
        "updatedAt": _iso_datetime(finance_doc.get("updated_at")),
    }


def _budget_status(spent: float, budgeted: float | None) -> Literal["ok", "warning", "exceeded", "unset"]:
    if budgeted is None or budgeted <= 0:
        return "unset"
    used = spent / budgeted
    if used > 1:
        return "exceeded"
    if used >= 0.8:
        return "warning"
    return "ok"


def _build_dashboard_payload(
    *,
    period: str,
    payments: list[dict[str, Any]],
    previous_payments: list[dict[str, Any]],
    services: list[dict[str, Any]],
    finance_doc: dict[str, Any] | None,
    category_budgets: list[dict[str, Any]],
    movement_type: Literal["all", "expense", "income"],
    filter_payments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    service_map = {_service_key(service.get("_id")): service for service in services}
    expense_movements = [_payment_to_movement(doc, service_map) for doc in payments]
    filter_movements = [_payment_to_movement(doc, service_map) for doc in (filter_payments or payments)]
    income = _round_money(finance_doc.get("salary")) if finance_doc else 0.0
    budget = _round_money(finance_doc.get("budget")) if finance_doc and finance_doc.get("budget") is not None else None

    expenses = _round_money(sum(item["monto"] for item in expense_movements))
    previous_expenses = _round_money(sum(float(doc.get("amount") or 0) for doc in previous_payments))
    day_count = _analysis_day_count(period)
    daily_average = _round_money(expenses / day_count if day_count else 0)
    projected = _round_money(daily_average * _days_in_period(period))
    balance = _round_money(income - expenses)

    category_totals: dict[str, dict[str, Any]] = {}
    for movement in expense_movements:
        bucket = category_totals.setdefault(
            movement["categoria"],
            {"category": movement["categoria"], "amount": 0.0, "count": 0, "color": CATEGORY_COLORS.get(movement["categoria"], "#64748b")},
        )
        bucket["amount"] = _round_money(bucket["amount"] + movement["monto"])
        bucket["count"] += 1

    evolution_map: dict[str, float] = defaultdict(float)
    for movement in expense_movements:
        evolution_map[movement["fecha"]] += movement["monto"]
    cumulative = 0.0
    evolution = []
    for day in sorted(evolution_map):
        amount = _round_money(evolution_map[day])
        cumulative = _round_money(cumulative + amount)
        evolution.append({"date": day, "amount": amount, "cumulative": cumulative})

    budgets_by_category = {
        _normalized_category(doc.get("category")): _round_money(doc.get("amount") or doc.get("montoPresupuestado"))
        for doc in category_budgets
    }
    budget_categories = sorted(set(category_totals) | set(budgets_by_category) | set(CATEGORY_LABELS))
    budgets = []
    alerts = []
    for category in budget_categories:
        spent = _round_money(category_totals.get(category, {}).get("amount", 0))
        budgeted = budgets_by_category.get(category)
        status = _budget_status(spent, budgeted)
        used_pct = round((spent / budgeted) * 100, 2) if budgeted else None
        remaining = _round_money(budgeted - spent) if budgeted is not None else None
        item = {
            "category": category,
            "budgeted": budgeted,
            "spent": spent,
            "remaining": remaining,
            "used_pct": used_pct,
            "status": status,
        }
        budgets.append(item)
        if status == "warning":
            alerts.append({"category": category, "level": "warning", "message": f"{category} esta cerca del limite presupuestado."})
        elif status == "exceeded":
            alerts.append({"category": category, "level": "danger", "message": f"{category} supero el presupuesto asignado."})

    income_item = _income_movement(period, finance_doc)
    movements = []
    if movement_type in ("all", "income") and income_item:
        movements.append(income_item)
    if movement_type in ("all", "expense"):
        movements.extend(expense_movements)
    movements.sort(key=lambda item: item["fecha"], reverse=True)

    top_expenses = sorted(expense_movements, key=lambda item: item["monto"], reverse=True)[:5]
    filters = {
        "categories": sorted({item["categoria"] for item in filter_movements}),
        "paymentMethods": sorted({str(item["medioPago"]) for item in filter_movements if item.get("medioPago")}),
        "accounts": sorted({str(item["cuenta"]) for item in filter_movements if item.get("cuenta")}),
        "types": ["all", "expense", "income"],
    }

    delta = _round_money(expenses - previous_expenses)
    delta_pct = round((delta / previous_expenses) * 100, 2) if previous_expenses else None
    if budget is not None and budget > 0:
        used_global = round((expenses / budget) * 100, 2)
        if used_global >= 80 and used_global <= 100:
            alerts.append({"category": "Presupuesto mensual", "level": "warning", "message": "El gasto mensual esta cerca del presupuesto global."})
        elif used_global > 100:
            alerts.append({"category": "Presupuesto mensual", "level": "danger", "message": "El gasto mensual supero el presupuesto global."})
    else:
        used_global = None

    return {
        "summary": {
            "period": period,
            "income": income,
            "expenses": expenses,
            "available_balance": balance,
            "monthly_savings": max(balance, 0),
            "budget": budget,
            "budget_used_pct": used_global,
            "daily_average_expense": daily_average,
            "previous_month_expenses": previous_expenses,
            "month_over_month_delta": delta,
            "month_over_month_delta_pct": delta_pct,
            "projected_month_expense": projected,
            "fixed_expenses": _round_money(sum(item["monto"] for item in expense_movements if item["esFijo"])),
            "variable_expenses": _round_money(sum(item["monto"] for item in expense_movements if not item["esFijo"])),
        },
        "categories": sorted(category_totals.values(), key=lambda item: item["amount"], reverse=True),
        "evolution": evolution,
        "budgets": budgets,
        "movements": movements[:50],
        "topExpenses": top_expenses,
        "alerts": alerts,
        "filters": filters,
    }


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    request: Request,
    month: str = Query(default_factory=_current_period, pattern=r"^\d{4}-\d{2}$"),
    category: str | None = Query(None),
    payment_method: str | None = Query(None),
    account: str | None = Query(None),
    type: Literal["all", "expense", "income"] = Query("all"),
):
    db = getattr(request.app.state, "db", None) or get_db()
    user_id = current_user_id()
    previous_month = _previous_period(month)

    services = await db["services"].find({"user_id": user_id}).to_list(length=500)
    service_map = {_service_key(service.get("_id")): service for service in services}

    base_query = _payment_period_query(user_id, month)
    if payment_method:
        base_query["payment_method"] = payment_method
    if account:
        base_query["account"] = account

    all_month_docs = await db["payments"].find(base_query).sort("payment_date", -1).to_list(length=1000)
    docs = list(all_month_docs)
    if category:
        normalized_filter = _normalized_category(category)
        docs = [doc for doc in docs if _payment_category(doc, service_map) == normalized_filter]

    previous_docs = await db["payments"].find(_payment_period_query(user_id, previous_month)).to_list(length=1000)
    finance_doc = await db["monthly_finances"].find_one({"user_id": user_id, "period": month})
    category_budgets = await db["category_budgets"].find({"user_id": user_id, "period": month}).to_list(length=200)

    return _build_dashboard_payload(
        period=month,
        payments=docs,
        previous_payments=previous_docs,
        services=services,
        finance_doc=finance_doc,
        category_budgets=category_budgets,
        movement_type=type,
        filter_payments=all_month_docs,
    )
