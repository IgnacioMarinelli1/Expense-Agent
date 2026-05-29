import httpx
from datetime import datetime

_IPC_SERIES_ID = "103.1_I2N_2016_M_15"
_API_BASE = "https://apis.datos.gob.ar/series/api/series/"


async def _fetch_ipc_range(start: str, end: str) -> dict[str, float]:
    """Returns {YYYY-MM: index_value} for each month in [start, end]."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            _API_BASE,
            params={"ids": _IPC_SERIES_ID, "start_date": start, "end_date": end, "format": "json"},
        )
        r.raise_for_status()
        data = r.json().get("data", [])
    return {row[0][:7]: float(row[1]) for row in data if row[1] is not None}


async def calculate_inflation_coefficient(from_period: str, to_period: str) -> dict:
    """Calcula el coeficiente de ajuste por inflación entre dos períodos usando el IPC nacional del INDEC.

    Args:
        from_period: Período base en formato YYYY-MM (ej: "2026-01").
        to_period: Período destino en formato YYYY-MM (ej: "2026-05").

    Returns:
        Dict con coefficient (float), inflation_pct (float), from_index y to_index.
    """
    try:
        indices = await _fetch_ipc_range(from_period, to_period)
    except Exception as e:
        return {"error": f"No se pudo obtener el IPC: {e}"}

    base = indices.get(from_period)
    target = indices.get(to_period)

    if base is None or target is None:
        available = sorted(indices.keys())
        return {
            "error": f"Período no disponible. Disponibles: {available[-6:] if available else 'ninguno'}",
            "from_period": from_period,
            "to_period": to_period,
        }

    coefficient = target / base
    inflation_pct = round((coefficient - 1) * 100, 2)

    return {
        "from_period": from_period,
        "to_period": to_period,
        "from_index": round(base, 4),
        "to_index": round(target, 4),
        "coefficient": round(coefficient, 6),
        "inflation_pct": inflation_pct,
    }


async def get_current_period() -> dict:
    """Devuelve el período actual (YYYY-MM) y el período anterior disponible en el IPC.

    Returns:
        Dict con current_period y previous_period.
    """
    now = datetime.utcnow()
    current = f"{now.year}-{now.month:02d}"
    if now.month == 1:
        previous = f"{now.year - 1}-12"
    else:
        previous = f"{now.year}-{now.month - 1:02d}"
    return {"current_period": current, "previous_period": previous}
