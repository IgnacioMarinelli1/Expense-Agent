from typing import Literal
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    period: str
    income: float
    expenses: float
    available_balance: float
    monthly_savings: float
    budget: float | None = None
    budget_used_pct: float | None = None
    daily_average_expense: float
    previous_month_expenses: float
    month_over_month_delta: float
    month_over_month_delta_pct: float | None = None
    projected_month_expense: float
    fixed_expenses: float
    variable_expenses: float


class DashboardCategory(BaseModel):
    category: str
    amount: float
    count: int
    color: str


class DashboardEvolutionPoint(BaseModel):
    date: str
    amount: float
    cumulative: float


class DashboardBudgetItem(BaseModel):
    category: str
    budgeted: float | None = None
    spent: float
    remaining: float | None = None
    used_pct: float | None = None
    status: Literal["ok", "warning", "exceeded", "unset"]


class DashboardMovement(BaseModel):
    id: str
    fecha: str
    tipo: Literal["ingreso", "gasto"]
    categoria: str
    subcategoria: str | None = None
    descripcion: str
    medioPago: str | None = None
    cuenta: str | None = None
    monto: float
    esFijo: bool
    createdAt: str | None = None
    updatedAt: str | None = None


class DashboardAlert(BaseModel):
    category: str
    message: str
    level: Literal["info", "warning", "danger"]


class DashboardFilters(BaseModel):
    categories: list[str]
    paymentMethods: list[str]
    accounts: list[str]
    types: list[str] = ["all", "expense", "income"]


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    categories: list[DashboardCategory]
    evolution: list[DashboardEvolutionPoint]
    budgets: list[DashboardBudgetItem]
    movements: list[DashboardMovement]
    topExpenses: list[DashboardMovement]
    alerts: list[DashboardAlert]
    filters: DashboardFilters
