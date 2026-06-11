import { api } from '$lib/api/client'

export type DashboardTypeFilter = 'all' | 'expense' | 'income'
export type BudgetStatus = 'ok' | 'warning' | 'exceeded' | 'unset'
export type AlertLevel = 'info' | 'warning' | 'danger'

export interface DashboardQuery {
    month: string
    category?: string
    payment_method?: string
    account?: string
    type: DashboardTypeFilter
}

export interface DashboardSummary {
    period: string
    income: number
    expenses: number
    available_balance: number
    monthly_savings: number
    budget?: number | null
    budget_used_pct?: number | null
    daily_average_expense: number
    previous_month_expenses: number
    month_over_month_delta: number
    month_over_month_delta_pct?: number | null
    projected_month_expense: number
    fixed_expenses: number
    variable_expenses: number
}

export interface DashboardCategory {
    category: string
    amount: number
    count: number
    color: string
}

export interface DashboardEvolutionPoint {
    date: string
    amount: number
    cumulative: number
}

export interface DashboardBudgetItem {
    category: string
    budgeted?: number | null
    spent: number
    remaining?: number | null
    used_pct?: number | null
    status: BudgetStatus
}

export interface DashboardMovement {
    id: string
    fecha: string
    tipo: 'ingreso' | 'gasto'
    categoria: string
    subcategoria?: string | null
    descripcion: string
    medioPago?: string | null
    cuenta?: string | null
    monto: number
    esFijo: boolean
    createdAt?: string | null
    updatedAt?: string | null
}

export interface DashboardAlert {
    category: string
    message: string
    level: AlertLevel
}

export interface DashboardFilterOptions {
    categories: string[]
    paymentMethods: string[]
    accounts: string[]
    types: DashboardTypeFilter[]
}

export interface DashboardData {
    summary: DashboardSummary
    categories: DashboardCategory[]
    evolution: DashboardEvolutionPoint[]
    budgets: DashboardBudgetItem[]
    movements: DashboardMovement[]
    topExpenses: DashboardMovement[]
    alerts: DashboardAlert[]
    filters: DashboardFilterOptions
}

type LegacyExpense = {
    id: string
    type: string
    category: string
    amount: number
    date?: string | null
    due_date?: string | null
    paid: boolean
    notes?: string | null
}

const CATEGORY_LABELS = [
    'Comida / Supermercado',
    'Transporte',
    'Servicios',
    'Vivienda',
    'Salud',
    'Educacion',
    'Ocio',
    'Ropa',
    'Deudas / cuotas',
    'Ahorro / inversion',
    'Otros',
]

const CATEGORY_COLORS: Record<string, string> = {
    'Comida / Supermercado': '#22c55e',
    Transporte: '#3b82f6',
    Servicios: '#06b6d4',
    Vivienda: '#8b5cf6',
    Salud: '#ef4444',
    Educacion: '#f59e0b',
    Ocio: '#ec4899',
    Ropa: '#14b8a6',
    'Deudas / cuotas': '#f97316',
    'Ahorro / inversion': '#10b981',
    Otros: '#64748b',
}

function currentMonth() {
    return new Date().toISOString().slice(0, 7)
}

function previousMonth(period: string) {
    const [year, month] = period.split('-').map(Number)
    if (month === 1) return `${year - 1}-12`
    return `${year}-${String(month - 1).padStart(2, '0')}`
}

function daysInMonth(period: string) {
    const [year, month] = period.split('-').map(Number)
    return new Date(year, month, 0).getDate()
}

function analysisDayCount(period: string) {
    const today = new Date()
    const current = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
    return period === current ? Math.max(1, today.getDate()) : daysInMonth(period)
}

function roundMoney(value: number) {
    return Math.round((value + Number.EPSILON) * 100) / 100
}

function normalizeCategory(raw: string | null | undefined, description = '') {
    const text = (raw ?? '').trim()
    if (CATEGORY_LABELS.includes(text)) return text

    const haystack = `${text} ${description}`.toLowerCase()
    if (['super', 'mercado', 'comida', 'restaurant', 'delivery', 'verduleria', 'cafe'].some((k) => haystack.includes(k))) return 'Comida / Supermercado'
    if (['taxi', 'uber', 'nafta', 'sube', 'colectivo', 'tren', 'transporte'].some((k) => haystack.includes(k))) return 'Transporte'
    if (['luz', 'gas', 'agua', 'internet', 'telefono', 'telefonia', 'wifi', 'edenor', 'edesur'].some((k) => haystack.includes(k))) return 'Servicios'
    if (['alquiler', 'expensa', 'renta', 'inmueble', 'admin', 'consorcio', 'depto', 'vivienda', 'hipoteca'].some((k) => haystack.includes(k))) return 'Vivienda'
    if (['farmacia', 'medico', 'salud', 'prepaga', 'hospital'].some((k) => haystack.includes(k))) return 'Salud'
    if (['curso', 'educacion', 'universidad', 'colegio', 'libro'].some((k) => haystack.includes(k))) return 'Educacion'
    if (['cine', 'bar', 'netflix', 'spotify', 'ocio', 'juego', 'gaming', 'subscription'].some((k) => haystack.includes(k))) return 'Ocio'
    if (['ropa', 'zapatilla', 'indumentaria'].some((k) => haystack.includes(k))) return 'Ropa'
    if (['deuda', 'cuota', 'prestamo', 'tarjeta'].some((k) => haystack.includes(k))) return 'Deudas / cuotas'
    if (['ahorro', 'inversion', 'fci', 'plazo fijo'].some((k) => haystack.includes(k))) return 'Ahorro / inversion'
    return 'Otros'
}

function isoDateFromLegacy(value: string | null | undefined, period: string) {
    if (!value) return `${period}-01`
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value.slice(0, 10)

    const [day, month] = value.split('/')
    const year = period.slice(0, 4)
    if (!day || !month) return `${period}-01`
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
}

type MonthlyFinance = {
    salary: number | null
    budget: number | null
    currency: string
}

function budgetStatus(spent: number, budgeted: number | null | undefined): BudgetStatus {
    if (budgeted === null || budgeted === undefined || budgeted <= 0) return 'unset'
    if (spent > budgeted) return 'exceeded'
    if (spent > budgeted * 0.8) return 'warning'
    return 'ok'
}

function buildDashboard(
    period: string,
    expensesRaw: LegacyExpense[],
    previousTotal: number,
    summaryTotal: number,
    finance: MonthlyFinance | null,
    filters: DashboardQuery,
): DashboardData {
    const allMovements = expensesRaw.map((expense) => {
        const category = normalizeCategory(expense.category, expense.type)
        return {
            id: expense.id,
            fecha: isoDateFromLegacy(expense.date, period),
            tipo: 'gasto' as const,
            categoria: category,
            subcategoria: expense.category,
            descripcion: expense.type,
            medioPago: null,
            cuenta: null,
            monto: Number(expense.amount ?? 0),
            esFijo: false,
            createdAt: null,
            updatedAt: null,
        }
    })

    let movements = allMovements
    if (filters.category) movements = movements.filter((item) => item.categoria === filters.category)
    if (filters.type === 'income') movements = []

    const expenses = roundMoney(summaryTotal || allMovements.reduce((sum, item) => sum + item.monto, 0))
    const visibleExpenses = roundMoney(movements.reduce((sum, item) => sum + item.monto, 0))
    const dayCount = analysisDayCount(period)
    const dailyAverage = roundMoney(expenses / dayCount)
    const projected = roundMoney(dailyAverage * daysInMonth(period))

    const categoryTotals = new Map<string, DashboardCategory>()
    for (const movement of movements) {
        const item = categoryTotals.get(movement.categoria) ?? {
            category: movement.categoria,
            amount: 0,
            count: 0,
            color: CATEGORY_COLORS[movement.categoria] ?? CATEGORY_COLORS.Otros,
        }
        item.amount = roundMoney(item.amount + movement.monto)
        item.count += 1
        categoryTotals.set(movement.categoria, item)
    }

    const byDate = new Map<string, number>()
    for (const movement of movements) {
        byDate.set(movement.fecha, roundMoney((byDate.get(movement.fecha) ?? 0) + movement.monto))
    }

    let cumulative = 0
    const evolution = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, amount]) => {
        cumulative = roundMoney(cumulative + amount)
        return { date, amount, cumulative }
    })

    const salary = finance?.salary ?? null
    const budget = finance?.budget ?? null

    const generalBudget: DashboardBudgetItem = {
        category: 'Presupuesto general',
        budgeted: budget,
        spent: expenses,
        remaining: budget !== null ? roundMoney(budget - expenses) : null,
        used_pct: budget ? roundMoney((expenses / budget) * 100) : null,
        status: budgetStatus(expenses, budget),
    }

    const budgets = [
        generalBudget,
        ...CATEGORY_LABELS.map((category) => ({
            category,
            budgeted: null,
            spent: roundMoney(categoryTotals.get(category)?.amount ?? 0),
            remaining: null,
            used_pct: null,
            status: 'unset' as BudgetStatus,
        })),
    ]

    const alerts: DashboardAlert[] = []
    if (generalBudget.status === 'exceeded') {
        alerts.push({
            category: 'Presupuesto general',
            message: `Te pasaste del presupuesto del mes: gastaste $${expenses.toLocaleString('es-AR')} de $${(budget ?? 0).toLocaleString('es-AR')}.`,
            level: 'danger',
        })
    } else if (generalBudget.status === 'warning') {
        alerts.push({
            category: 'Presupuesto general',
            message: `Usaste mas del 80% del presupuesto del mes ($${expenses.toLocaleString('es-AR')} de $${(budget ?? 0).toLocaleString('es-AR')}).`,
            level: 'warning',
        })
    }
    if (salary !== null && expenses > salary) {
        alerts.push({
            category: 'Ingresos',
            message: 'Los gastos del mes superan los ingresos registrados.',
            level: 'danger',
        })
    }

    const delta = roundMoney(expenses - previousTotal)
    const deltaPct = previousTotal ? roundMoney((delta / previousTotal) * 100) : null

    return {
        summary: {
            period,
            income: salary ?? 0,
            expenses: visibleExpenses || expenses,
            available_balance: roundMoney((salary ?? 0) - expenses),
            monthly_savings: salary !== null ? roundMoney(salary - expenses) : 0,
            budget,
            budget_used_pct: budget ? roundMoney((expenses / budget) * 100) : null,
            daily_average_expense: dailyAverage,
            previous_month_expenses: previousTotal,
            month_over_month_delta: delta,
            month_over_month_delta_pct: deltaPct,
            projected_month_expense: projected,
            fixed_expenses: 0,
            variable_expenses: expenses,
        },
        categories: [...categoryTotals.values()].sort((a, b) => b.amount - a.amount),
        evolution,
        budgets,
        movements: [...movements].sort((a, b) => b.fecha.localeCompare(a.fecha)).slice(0, 50),
        topExpenses: [...movements].sort((a, b) => b.monto - a.monto).slice(0, 5),
        alerts,
        filters: {
            categories: [...new Set(allMovements.map((item) => item.categoria))].sort(),
            paymentMethods: [],
            accounts: [],
            types: ['all', 'expense', 'income'],
        },
    }
}

const emptyData: DashboardData = {
    summary: {
        period: currentMonth(),
        income: 0,
        expenses: 0,
        available_balance: 0,
        monthly_savings: 0,
        budget: null,
        budget_used_pct: null,
        daily_average_expense: 0,
        previous_month_expenses: 0,
        month_over_month_delta: 0,
        month_over_month_delta_pct: null,
        projected_month_expense: 0,
        fixed_expenses: 0,
        variable_expenses: 0,
    },
    categories: [],
    evolution: [],
    budgets: [],
    movements: [],
    topExpenses: [],
    alerts: [],
    filters: { categories: [], paymentMethods: [], accounts: [], types: ['all', 'expense', 'income'] },
}

let _data = $state<DashboardData>(emptyData)
let _filters = $state<DashboardQuery>({ month: currentMonth(), type: 'all' })
let _loading = $state(false)
let _error = $state('')

export async function loadDashboard(nextFilters?: Partial<DashboardQuery>) {
    _filters = { ..._filters, ...nextFilters }
    _loading = true
    _error = ''
    try {
        const [expensesRaw, summaryRaw, previousSummaryRaw, financeRaw] = await Promise.all([
            api.getExpenses(_filters.month),
            api.getSummary(_filters.month),
            api.getSummary(previousMonth(_filters.month)),
            // Backend viejo puede no tener /finance todavia; el dashboard no debe romperse.
            api.getFinance(_filters.month).catch(() => null),
        ])

        _data = buildDashboard(
            _filters.month,
            expensesRaw as LegacyExpense[],
            Number(previousSummaryRaw.total ?? 0),
            Number(summaryRaw.total ?? 0),
            financeRaw,
            _filters,
        )
    } catch (error) {
        _error = error instanceof Error ? error.message : 'No se pudo cargar el dashboard'
    } finally {
        _loading = false
    }
}

export const dashboardState = {
    get data() { return _data },
    get filters() { return _filters },
    get loading() { return _loading },
    get error() { return _error },
}
