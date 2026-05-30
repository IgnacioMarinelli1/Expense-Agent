from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from db.db import get_db

_USER_ID = "demo_user"

CHART_TYPES = {
    "auto",
    "bar",
    "stacked_bar",
    "line",
    "area",
    "pie",
    "donut",
    "treemap",
    "heatmap",
    "radar",
    "scatter",
    "waterfall",
    "bar3d",
    "scatter3d",
    "category_month_bar3d",
}
VISUAL_MODES = {"auto", "2d", "3d"}
METRICS = {"amount", "count", "average"}
GROUP_BY = {"category", "status", "period", "currency", "service", "notes"}
THEMES = {"auto", "light", "dark"}
EXECUTABLE_PREFIXES = ("function", "javascript:", "data:text/html", "=>")
_PENDING_CHART_SPECS: list[dict[str, Any]] = []
_DARK_TEXT = "#d4d4d8"
_DARK_MUTED = "#a1a1aa"
_DARK_GRID = "rgba(255,255,255,0.14)"


def queue_pending_chart_spec(chart_spec: dict[str, Any]) -> None:
    """Stores a generated chart for the SSE streamer.

    ADK sub-agent tool calls are not always surfaced as root-level function
    responses, so successful chart specs also travel through this local queue.
    """
    _PENDING_CHART_SPECS.append(chart_spec)


def pop_pending_chart_specs() -> list[dict[str, Any]]:
    specs = list(_PENDING_CHART_SPECS)
    _PENDING_CHART_SPECS.clear()
    return specs


def contains_executable_string(value: Any) -> bool:
    if isinstance(value, str):
        stripped = value.strip().lower()
        return any(stripped.startswith(prefix) for prefix in EXECUTABLE_PREFIXES)
    if isinstance(value, dict):
        return any(contains_executable_string(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_executable_string(v) for v in value)
    return False


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_axis_dark(axis: Any) -> Any:
    axis_defaults = {
        "axisLabel": {"color": _DARK_MUTED},
        "axisLine": {"lineStyle": {"color": "rgba(255,255,255,0.22)"}},
        "splitLine": {"lineStyle": {"color": _DARK_GRID}},
        "nameTextStyle": {"color": _DARK_MUTED},
    }
    if isinstance(axis, list):
        return [_normalize_axis_dark(item) for item in axis]
    if isinstance(axis, dict):
        return _merge_dict(axis_defaults, axis)
    return axis


def _apply_dark_chart_defaults(option: dict[str, Any]) -> dict[str, Any]:
    normalized = _merge_dict(
        {
            "backgroundColor": "transparent",
            "textStyle": {"color": _DARK_TEXT},
            "tooltip": {
                "backgroundColor": "rgba(24,24,27,0.96)",
                "borderColor": "rgba(255,255,255,0.16)",
                "textStyle": {"color": _DARK_TEXT},
            },
            "legend": {"textStyle": {"color": _DARK_MUTED}},
        },
        option,
    )
    for key in ("xAxis", "yAxis", "radiusAxis", "angleAxis"):
        if key in normalized:
            normalized[key] = _normalize_axis_dark(normalized[key])
    for key in ("xAxis3D", "yAxis3D", "zAxis3D"):
        if key in normalized and isinstance(normalized[key], dict):
            normalized[key] = _merge_dict({"axisLabel": {"color": _DARK_MUTED}}, normalized[key])
    return normalized


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _category_from_payment(payment: dict[str, Any], category_overrides: dict[str, str] | None = None) -> str:
    if category_overrides:
        candidates = [
            payment.get("notes"),
            payment.get("service_name"),
            payment.get("service_id"),
            payment.get("category"),
        ]
        normalized_overrides = {
            _normalized_text(key): str(value).strip()
            for key, value in category_overrides.items()
            if str(value).strip()
        }
        for candidate in candidates:
            match = normalized_overrides.get(_normalized_text(candidate))
            if match:
                return match

    text = " ".join(
        str(payment.get(key) or "")
        for key in ("category", "notes", "service_name")
    ).lower()
    if any(k in text for k in ("luz", "electr", "edesur", "edenor")):
        return "luz"
    if any(k in text for k in ("gas", "metrogas", "camuzzi")):
        return "gas"
    if any(k in text for k in ("agua", "aysa")):
        return "agua"
    if any(k in text for k in ("abl", "impuest", "municipal", "tasa")):
        return "impuesto"
    if any(k in text for k in ("expensa", "admin")):
        return "expensas"
    if any(k in text for k in ("internet", "wifi", "tel", "cable", "movistar", "claro", "personal")):
        return "telefonia"
    if any(k in text for k in ("super", "mercado", "verduler", "farmacia", "comida")):
        return "consumo"
    return "otros"


def _period_from_payment(payment: dict[str, Any]) -> str:
    period = payment.get("period")
    if period:
        return str(period)
    for key in ("payment_date", "due_date", "created_at"):
        value = payment.get(key)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m")
        if isinstance(value, str) and len(value) >= 7:
            return value[:7]
    return "sin período"


def _dimension_value(payment: dict[str, Any], group_by: str, category_overrides: dict[str, str] | None = None) -> str:
    if group_by == "category":
        return _category_from_payment(payment, category_overrides)
    if group_by == "period":
        return _period_from_payment(payment)
    if group_by == "service":
        return str(payment.get("service_name") or payment.get("service_id") or "sin servicio")
    if group_by == "notes":
        return str(payment.get("notes") or "sin descripción")
    return str(payment.get(group_by) or f"sin {group_by}")


def _metric_value(payments: list[dict[str, Any]], metric: str) -> float:
    if metric == "count":
        return float(len(payments))
    total = sum(float(payment.get("amount") or 0) for payment in payments)
    if metric == "average":
        return round(total / len(payments), 2) if payments else 0.0
    return float(total)


def _filter_payments(
    payments: list[dict[str, Any]],
    *,
    period: str | None,
    compare_period: str | None,
    status: str | None,
    currency: str | None,
    group_by: str,
    secondary_group_by: str | None,
) -> list[dict[str, Any]]:
    periods = {p for p in (period, compare_period) if p}
    keep_all_periods = group_by == "period" or secondary_group_by == "period"
    filtered = []
    for payment in payments:
        if status and payment.get("status") != status:
            continue
        if currency and payment.get("currency", "ARS") != currency:
            continue
        if periods and not keep_all_periods and _period_from_payment(payment) not in periods:
            continue
        filtered.append(payment)
    return filtered


def _choose_chart_type(chart_type: str, visual_mode: str, group_by: str, secondary_group_by: str | None) -> str:
    if chart_type != "auto":
        return chart_type
    if visual_mode == "3d" or secondary_group_by:
        if group_by == "category" and secondary_group_by == "period":
            return "category_month_bar3d"
        return "bar3d"
    if group_by == "period":
        return "line"
    if group_by == "status":
        return "donut"
    return "bar"


def _choose_visual_mode(visual_mode: str, secondary_group_by: str | None) -> str:
    if visual_mode != "auto":
        return visual_mode
    return "3d" if secondary_group_by else "2d"


def _sorted_labels(groups: dict[str, list[dict[str, Any]]], metric: str, group_by: str) -> list[str]:
    if group_by == "period":
        return sorted(groups)
    return sorted(groups, key=lambda label: _metric_value(groups[label], metric), reverse=True)


def _series_name(metric: str) -> str:
    return {"amount": "Monto", "count": "Cantidad", "average": "Promedio"}[metric]


def _build_single_axis_option(
    chart_type: str,
    groups: dict[str, list[dict[str, Any]]],
    metric: str,
    group_by: str,
    title: str,
) -> dict[str, Any]:
    labels = _sorted_labels(groups, metric, group_by)
    values = [_metric_value(groups[label], metric) for label in labels]
    if chart_type in {"pie", "donut"}:
        return {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "item"},
            "legend": {"bottom": 0},
            "series": [
                {
                    "name": _series_name(metric),
                    "type": "pie",
                    "radius": ["45%", "70%"] if chart_type == "donut" else "65%",
                    "data": [{"name": label, "value": value} for label, value in zip(labels, values)],
                }
            ],
        }
    if chart_type == "treemap":
        return {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "series": [{"type": "treemap", "data": [{"name": label, "value": value} for label, value in zip(labels, values)]}],
        }
    if chart_type == "radar":
        return {
            "title": {"text": title},
            "tooltip": {},
            "radar": {"indicator": [{"name": label, "max": max(values) or 1} for label in labels]},
            "series": [{"type": "radar", "data": [{"value": values, "name": _series_name(metric)}]}],
        }
    if chart_type == "scatter":
        return {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "category", "data": labels},
            "yAxis": {"type": "value"},
            "series": [{"name": _series_name(metric), "type": "scatter", "data": values}],
        }
    if chart_type == "waterfall":
        cumulative = []
        running = 0.0
        for value in values:
            cumulative.append(running)
            running += value
        return {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": labels},
            "yAxis": {"type": "value"},
            "series": [
                {"name": "Base", "type": "bar", "stack": "total", "data": cumulative, "itemStyle": {"color": "transparent"}},
                {"name": _series_name(metric), "type": "bar", "stack": "total", "data": values},
            ],
        }
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 24, "top": 56, "bottom": 48},
        "xAxis": {"type": "category", "data": labels},
        "yAxis": {"type": "value"},
        "series": [
            {
                "name": _series_name(metric),
                "type": "line" if chart_type in {"line", "area"} else "bar",
                "smooth": chart_type in {"line", "area"},
                "areaStyle": {} if chart_type == "area" else None,
                "data": values,
            }
        ],
    }


def _build_two_axis_option(
    chart_type: str,
    payments: list[dict[str, Any]],
    metric: str,
    group_by: str,
    secondary_group_by: str,
    title: str,
    category_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    primary_labels = sorted({_dimension_value(payment, group_by, category_overrides) for payment in payments})
    secondary_labels = sorted({_dimension_value(payment, secondary_group_by, category_overrides) for payment in payments})
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for payment in payments:
        buckets[
            (
                _dimension_value(payment, group_by, category_overrides),
                _dimension_value(payment, secondary_group_by, category_overrides),
            )
        ].append(payment)

    if chart_type in {"bar3d", "category_month_bar3d", "scatter3d"}:
        data = [
            [primary_labels.index(primary), secondary_labels.index(secondary), _metric_value(items, metric)]
            for (primary, secondary), items in buckets.items()
        ]
        return {
            "title": {"text": title},
            "tooltip": {},
            "xAxis3D": {"type": "category", "data": primary_labels},
            "yAxis3D": {"type": "category", "data": secondary_labels},
            "zAxis3D": {"type": "value"},
            "grid3D": {"boxWidth": 130, "boxDepth": 80, "viewControl": {"projection": "perspective"}},
            "series": [{"type": "scatter3D" if chart_type == "scatter3d" else "bar3D", "data": data, "shading": "lambert"}],
        }

    series = []
    for secondary in secondary_labels:
        series.append(
            {
                "name": secondary,
                "type": "bar",
                "stack": "total" if chart_type == "stacked_bar" else None,
                "data": [_metric_value(buckets.get((primary, secondary), []), metric) for primary in primary_labels],
            }
        )
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0},
        "grid": {"left": 48, "right": 24, "top": 56, "bottom": 72},
        "xAxis": {"type": "category", "data": primary_labels},
        "yAxis": {"type": "value"},
        "series": series,
    }


def _insights(groups: dict[str, list[dict[str, Any]]], metric: str) -> list[str]:
    if not groups:
        return ["No hay datos para graficar con esos filtros."]
    ranked = sorted(groups, key=lambda label: _metric_value(groups[label], metric), reverse=True)
    top = ranked[0]
    total = sum(_metric_value(items, metric) for items in groups.values())
    top_value = _metric_value(groups[top], metric)
    share = round(top_value / total * 100, 1) if total else 0
    return [
        f"{top} concentra {top_value:,.0f} ({share}% del total).",
        f"Total analizado: {total:,.0f}.",
    ]


def build_custom_chart_spec(
    title: str,
    mode: str,
    chart_type: str,
    option: dict[str, Any],
    subtitle: str = "Generado por agente de visualización",
    insights: list[str] = None,
    source: dict[str, Any] = None,
) -> dict[str, Any]:
    """Builds a ChartSpec from an agent-authored ECharts option."""
    if mode not in {"2d", "3d"}:
        return {"status": "error", "error_message": f"mode inválido: {mode}"}
    if not title or not title.strip():
        return {"status": "error", "error_message": "El título del gráfico es requerido"}
    if not chart_type or not chart_type.strip():
        return {"status": "error", "error_message": "chart_type es requerido"}
    if not isinstance(option, dict) or not option:
        return {"status": "error", "error_message": "option debe ser un objeto ECharts no vacío"}
    if contains_executable_string(option):
        return {"status": "error", "error_message": "La especificación contiene strings no permitidos."}
    option = _apply_dark_chart_defaults(option)

    spec = {
        "id": f"chart_{uuid4().hex[:10]}",
        "title": title.strip(),
        "subtitle": subtitle,
        "mode": mode,
        "chartType": chart_type.strip(),
        "option": option,
        "insights": insights or [],
        "source": source or {"custom": True},
        "generatedAt": datetime.now(UTC).isoformat(),
    }
    return {"status": "success", "chart_spec": spec, "insights": spec["insights"]}


async def generate_custom_chart(
    title: str,
    mode: str,
    chart_type: str,
    option: dict[str, Any],
    subtitle: str = "Generado por agente de visualización",
    insights: list[str] = None,
    source: dict[str, Any] = None,
) -> dict[str, Any]:
    """Genera un ChartSpec desde opciones completas de ECharts creadas por el agente.

    Usar cuando el agente necesite libertad total de diseño: datasets,
    múltiples series, encodings, leyendas, colores, grids, 3D, tooltips o
    composiciones que `generate_financial_chart` no cubre.
    """
    result = build_custom_chart_spec(
        title=title,
        mode=mode,
        chart_type=chart_type,
        option=option,
        subtitle=subtitle,
        insights=insights,
        source=source,
    )
    if result.get("status") == "success" and isinstance(result.get("chart_spec"), dict):
        queue_pending_chart_spec(result["chart_spec"])
    return result


def build_financial_chart_spec(
    payments: list[dict[str, Any]],
    chart_type: str = "auto",
    visual_mode: str = "auto",
    metric: str = "amount",
    period: str | None = None,
    compare_period: str | None = None,
    group_by: str = "category",
    secondary_group_by: str | None = None,
    status: str | None = None,
    currency: str | None = None,
    theme: str = "auto",
    limit: int = 12,
    category_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Builds a safe ECharts option from already-loaded financial records."""
    if chart_type not in CHART_TYPES:
        return {"status": "error", "error_message": f"chart_type inválido: {chart_type}"}
    if visual_mode not in VISUAL_MODES:
        return {"status": "error", "error_message": f"visual_mode inválido: {visual_mode}"}
    if metric not in METRICS:
        return {"status": "error", "error_message": f"metric inválida: {metric}"}
    if group_by not in GROUP_BY:
        return {"status": "error", "error_message": f"group_by inválido: {group_by}"}
    if secondary_group_by and secondary_group_by not in GROUP_BY:
        return {"status": "error", "error_message": f"secondary_group_by inválido: {secondary_group_by}"}
    if theme not in THEMES:
        return {"status": "error", "error_message": f"theme inválido: {theme}"}

    filtered = _filter_payments(
        payments,
        period=period,
        compare_period=compare_period,
        status=status,
        currency=currency,
        group_by=group_by,
        secondary_group_by=secondary_group_by,
    )
    mode = _choose_visual_mode(visual_mode, secondary_group_by)
    resolved_chart_type = _choose_chart_type(chart_type, mode, group_by, secondary_group_by)
    title_period = period or "todos los períodos"
    title = f"{_series_name(metric)} por {group_by} ({title_period})"

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payment in filtered:
        groups[_dimension_value(payment, group_by, category_overrides)].append(payment)

    if not filtered:
        option = _build_single_axis_option("bar", {}, metric, group_by, title)
    elif secondary_group_by:
        option = _build_two_axis_option(
            resolved_chart_type,
            filtered,
            metric,
            group_by,
            secondary_group_by,
            title,
            category_overrides,
        )
    else:
        limited_groups = {
            label: groups[label]
            for label in _sorted_labels(groups, metric, group_by)[: max(1, min(limit, 50))]
        }
        option = _build_single_axis_option(resolved_chart_type, limited_groups, metric, group_by, title)

    if contains_executable_string(option):
        return {"status": "error", "error_message": "La especificación generada contiene strings no permitidos."}

    spec = {
        "id": f"chart_{uuid4().hex[:10]}",
        "title": title,
        "subtitle": "Generado por Expense Agent",
        "mode": mode,
        "chartType": resolved_chart_type,
        "option": option,
        "insights": _insights(groups, metric),
        "source": {
            "collection": "payments",
            "period": period,
            "comparePeriod": compare_period,
            "records": len(filtered),
            "metric": metric,
            "groupBy": group_by,
            "secondaryGroupBy": secondary_group_by,
            "categoryOverrides": bool(category_overrides),
        },
        "generatedAt": datetime.now(UTC).isoformat(),
    }
    return {"status": "success", "chart_spec": spec, "insights": spec["insights"]}


async def generate_financial_chart(
    chart_type: str = "auto",
    visual_mode: str = "auto",
    metric: str = "amount",
    period: str = None,
    compare_period: str = None,
    group_by: str = "category",
    secondary_group_by: str = None,
    status: str = None,
    currency: str = None,
    theme: str = "auto",
    limit: int = 12,
    category_overrides: dict[str, str] = None,
) -> dict[str, Any]:
    """Genera un ChartSpec interactivo para visualizar gastos del usuario.

    Usar cuando el usuario pida gráficos, visualizaciones, comparaciones,
    evolución, distribución, ranking o resúmenes visuales.
    """
    db = get_db()
    query: dict[str, Any] = {"user_id": _USER_ID}
    if status:
        query["status"] = status
    if currency:
        query["currency"] = currency
    if period and group_by != "period" and secondary_group_by != "period":
        query["period"] = {"$in": [period, compare_period]} if compare_period else period

    docs = await db["payments"].find(query).sort("payment_date", -1).to_list(length=500)
    result = build_financial_chart_spec(
        payments=docs,
        chart_type=chart_type,
        visual_mode=visual_mode,
        metric=metric,
        period=period,
        compare_period=compare_period,
        group_by=group_by,
        secondary_group_by=secondary_group_by,
        status=status,
        currency=currency,
        theme=theme,
        limit=limit,
        category_overrides=category_overrides,
    )
    if result.get("status") == "success" and isinstance(result.get("chart_spec"), dict):
        queue_pending_chart_spec(result["chart_spec"])
    return result


async def get_chart_source_data(
    period: str = None,
    compare_period: str = None,
    status: str = None,
    currency: str = None,
    limit: int = 80,
) -> dict[str, Any]:
    """Devuelve pagos resumidos para que el agente de visualización categorice semánticamente.

    Esta tool no genera gráficos. Usarla antes de `generate_financial_chart`
    cuando el gráfico agrupe por categoría y las descripciones requieran criterio contable.
    """
    db = get_db()
    query: dict[str, Any] = {"user_id": _USER_ID}
    if status:
        query["status"] = status
    if currency:
        query["currency"] = currency
    periods = [p for p in (period, compare_period) if p]
    if periods:
        query["period"] = {"$in": periods}

    docs = await db["payments"].find(query).sort("payment_date", -1).to_list(length=max(1, min(limit, 200)))
    payments = []
    for doc in docs:
        payments.append(
            {
                "key": str(doc.get("notes") or doc.get("service_id") or doc.get("_id")),
                "notes": doc.get("notes"),
                "amount": doc.get("amount"),
                "currency": doc.get("currency", "ARS"),
                "period": doc.get("period"),
                "status": doc.get("status"),
                "service_id": str(doc.get("service_id")) if doc.get("service_id") else None,
                "existing_category": doc.get("category"),
            }
        )
    return {"status": "success", "payments": payments, "count": len(payments)}
