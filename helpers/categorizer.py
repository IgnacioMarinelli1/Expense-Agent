"""
Payment categorization helper.

Single source of truth for mapping free-form expense text (notes, provider
name, agent input) to one of the canonical category buckets used by the
frontend (colors in app.css) and the agent prompt.

Adding a new bucket: append to CATEGORIES, add its synonyms to KEYWORDS,
and add a matching --cat-<name> token in frontend/src/app.css.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

# Canonical buckets. Order matters: first match wins when keywords overlap
# (e.g. "luz" before "expensas"). Keep aligned with --cat-<name> tokens.
CATEGORIES: tuple[str, ...] = (
    "luz",
    "gas",
    "agua",
    "impuesto",
    "expensas",
    "telefonia",
    "subscription",
    "comida",
    "transporte",
    "salud",
    "otros",
)

DEFAULT_CATEGORY = "otros"

# Synonyms per bucket. Keys are accent-insensitive, lower-cased, matched as
# whole-word substrings against the normalized input.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "luz": (
        "luz", "electricidad", "electrica", "electrico",
        "edesur", "edenor", "edelap", "edemsa", "epec", "epe", "eden",
        "energia electrica", "kwh", "kilowatt",
    ),
    "gas": (
        "gas", "metrogas", "camuzzi", "naturgy", "ecogas", "litoral gas",
        "garrafa", "envasado",
    ),
    "agua": (
        "agua", "aysa", "sameep", "abas", "obras sanitarias",
    ),
    "impuesto": (
        "impuesto", "impuestos", "abl", "arba", "afip", "dgr", "iibb",
        "ingresos brutos", "monotributo", "municipal", "tasa", "tasas",
        "inmobiliario", "patente", "automotor", "sirea", "rentas",
    ),
    "expensas": (
        "expensa", "expensas", "administracion", "consorcio",
    ),
    "telefonia": (
        "internet", "wifi", "fibra", "fibertel", "telecentro", "telecom",
        "movistar", "claro", "personal", "tuenti", "flow", "directv",
        "cablevision", "cable", "telefono", "telefonia", "celular",
        "linea fija", "datos moviles",
    ),
    "subscription": (
        "netflix", "spotify", "hbo", "max", "disney", "paramount",
        "prime video", "amazon prime", "youtube", "youtube premium",
        "apple tv", "apple music", "deezer", "tidal",
        "claude", "claude.ai", "chatgpt", "openai", "anthropic",
        "icloud", "dropbox", "google one", "drive", "microsoft 365",
        "office 365", "office", "github", "notion", "linear", "figma",
        "adobe", "canva", "duolingo",
        "suscripcion", "suscripciones", "membresia", "membresias",
        "mensualidad", "plan mensual", "saas",
    ),
    "comida": (
        "supermercado", "super", "almacen", "verduleria", "carniceria",
        "panaderia", "mercado",
        "carrefour", "coto", "dia", "disco", "jumbo", "vea", "chango mas",
        "changomas", "walmart", "makro", "la anonima",
        "pedidosya", "rappi", "uber eats", "glovo",
        "mcdonalds", "burger king", "kfc", "mostaza", "starbucks",
        "restaurante", "resto", "rotiseria", "comida", "almuerzo",
        "cena", "desayuno", "cafe", "cafeteria", "delivery",
    ),
    "transporte": (
        "uber", "cabify", "didi", "taxi", "remis",
        "sube", "colectivo", "subte", "tren", "premetro",
        "peaje", "autopista", "ausa",
        "ypf", "shell", "axion", "puma", "trafigura",
        "combustible", "nafta", "gasoil", "gnc",
        "estacionamiento", "garage", "garaje", "cochera",
    ),
    "salud": (
        "farmacia", "farmacity", "dr ahorro", "drogueria",
        "medico", "medica", "clinica", "hospital", "sanatorio",
        "swiss medical", "omint", "osde", "galeno", "medife", "sancor salud",
        "prepaga", "obra social",
        "dentista", "odontologo", "oftalmologo", "kinesiologo",
        "psicologo", "psicologa", "psiquiatra",
        "consulta medica", "estudio medico", "laboratorio",
    ),
}


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse non-alphanumerics to single spaces."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()


def _matches(haystack: str, needles: Iterable[str]) -> bool:
    """Whole-word containment check on a pre-normalized haystack."""
    for needle in needles:
        normalized_needle = _normalize(needle)
        if not normalized_needle:
            continue
        # Word-boundary match: surround haystack with spaces and look for
        # " <needle> " so "gas" doesn't match "regalo".
        if f" {normalized_needle} " in f" {haystack} ":
            return True
    return False


def categorize(*texts: str | None, default: str = DEFAULT_CATEGORY) -> str:
    """Return the canonical category for one or more free-form text fragments.

    Pass any combination of strings (notes, type, provider). The first bucket
    whose synonyms appear in the combined text wins. Returns `default` if
    nothing matches.
    """
    combined = _normalize(" ".join(t for t in texts if t))
    if not combined:
        return default
    for bucket in CATEGORIES:
        if bucket == DEFAULT_CATEGORY:
            continue
        if _matches(combined, KEYWORDS.get(bucket, ())):
            return bucket
    return default


def is_known_category(value: str | None) -> bool:
    """True if `value` is one of the canonical buckets."""
    return bool(value) and value in CATEGORIES
