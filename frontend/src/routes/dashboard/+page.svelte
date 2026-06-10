<script lang="ts">
    import { onMount } from 'svelte'
    import { RefreshCw } from '@lucide/svelte'
    import { dashboardState, loadDashboard, type DashboardQuery } from '$lib/stores/dashboard.svelte'
    import DashboardFilters from '$lib/components/dashboard/DashboardFilters.svelte'
    import MonthlySummaryCards from '$lib/components/dashboard/MonthlySummaryCards.svelte'
    import CategoryBreakdownChart from '$lib/components/dashboard/CategoryBreakdownChart.svelte'
    import ExpenseEvolutionChart from '$lib/components/dashboard/ExpenseEvolutionChart.svelte'
    import BudgetVsActual from '$lib/components/dashboard/BudgetVsActual.svelte'
    import RecentMovementsTable from '$lib/components/dashboard/RecentMovementsTable.svelte'
    import TopExpenses from '$lib/components/dashboard/TopExpenses.svelte'
    import DashboardAlerts from '$lib/components/dashboard/DashboardAlerts.svelte'

    const data = $derived(dashboardState.data)
    const filters = $derived(dashboardState.filters)
    const loading = $derived(dashboardState.loading)
    const error = $derived(dashboardState.error)

    const fmt = (value: number | null | undefined) =>
        '$' + Number(value ?? 0).toLocaleString('es-AR', { maximumFractionDigits: 0 })

    function updateFilters(next: Partial<DashboardQuery>) {
        loadDashboard(next)
    }

    onMount(() => {
        loadDashboard()
    })
</script>

<div class="h-full overflow-y-auto bg-background">
    <div class="mx-auto flex w-full max-w-[118rem] flex-col gap-4 p-4 sm:p-5">
        <header class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <h1 class="text-xl font-semibold tracking-tight">Dashboard personal</h1>
                <p class="text-sm text-muted-foreground">Ingresos, gastos, presupuesto y saldo disponible.</p>
            </div>
            <button
                type="button"
                onclick={() => loadDashboard()}
                disabled={loading}
                class="inline-flex h-9 w-fit items-center gap-2 rounded-md border border-border bg-card px-3 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
            >
                <RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
                Actualizar
            </button>
        </header>

        <DashboardFilters filters={filters} options={data.filters} onChange={updateFilters} />

        {#if error}
            <div class="rounded-lg border border-amber-300 bg-amber-100 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
                {error}
            </div>
        {/if}

        {#if loading && data.movements.length === 0}
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {#each [1, 2, 3, 4, 5, 6] as _}
                    <div class="h-[108px] animate-pulse rounded-lg bg-muted"></div>
                {/each}
            </div>
            <div class="grid gap-4 xl:grid-cols-[1fr_1fr]">
                <div class="h-[360px] animate-pulse rounded-lg bg-muted"></div>
                <div class="h-[360px] animate-pulse rounded-lg bg-muted"></div>
            </div>
        {:else}
            <MonthlySummaryCards summary={data.summary} />

            <section class="grid gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-2 xl:grid-cols-4">
                <div>
                    <p class="text-xs text-muted-foreground">Mes anterior</p>
                    <p class="mt-1 text-lg font-semibold">{fmt(data.summary.previous_month_expenses)}</p>
                </div>
                <div>
                    <p class="text-xs text-muted-foreground">Diferencia mensual</p>
                    <p class="mt-1 text-lg font-semibold" class:text-red-500={data.summary.month_over_month_delta > 0} class:text-emerald-500={data.summary.month_over_month_delta <= 0}>
                        {fmt(data.summary.month_over_month_delta)}
                    </p>
                </div>
                <div>
                    <p class="text-xs text-muted-foreground">Proyeccion fin de mes</p>
                    <p class="mt-1 text-lg font-semibold">{fmt(data.summary.projected_month_expense)}</p>
                </div>
                <div>
                    <p class="text-xs text-muted-foreground">Fijos / variables</p>
                    <p class="mt-1 text-lg font-semibold">{fmt(data.summary.fixed_expenses)} / {fmt(data.summary.variable_expenses)}</p>
                </div>
            </section>

            <div class="grid gap-4 xl:grid-cols-2">
                <CategoryBreakdownChart categories={data.categories} />
                <ExpenseEvolutionChart evolution={data.evolution} />
            </div>

            <div class="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
                <BudgetVsActual budgets={data.budgets} />
                <div class="grid gap-4">
                    <DashboardAlerts alerts={data.alerts} />
                    <TopExpenses expenses={data.topExpenses} />
                </div>
            </div>

            <RecentMovementsTable movements={data.movements} />
        {/if}
    </div>
</div>
