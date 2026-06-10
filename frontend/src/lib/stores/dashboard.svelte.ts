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

function currentMonth() {
    return new Date().toISOString().slice(0, 7)
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
        _data = await api.getDashboard(_filters)
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
