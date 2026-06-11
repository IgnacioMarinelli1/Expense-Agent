<script lang="ts">
    import { ArrowDownRight, ArrowUpRight, PiggyBank, Wallet, Gauge, CalendarDays } from '@lucide/svelte'
    import type { DashboardSummary } from '$lib/stores/dashboard.svelte'

    let { summary }: { summary: DashboardSummary } = $props()

    const fmt = (value: number | null | undefined) =>
        '$' + Number(value ?? 0).toLocaleString('es-AR', { maximumFractionDigits: 0 })

    const pct = (value: number | null | undefined) =>
        value === null || value === undefined ? 'Sin presupuesto' : `${Math.round(value)}%`
</script>

<section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Ingresos</span>
            <ArrowUpRight class="size-4 text-emerald-500" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.income)}</p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Gastos</span>
            <ArrowDownRight class="size-4 text-red-500" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.expenses)}</p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Saldo disponible</span>
            <Wallet class="size-4 text-blue-500" />
        </div>
        <p class="text-2xl font-semibold" class:text-emerald-500={summary.available_balance >= 0} class:text-red-500={summary.available_balance < 0}>
            {fmt(summary.available_balance)}
        </p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Ahorro del mes</span>
            <PiggyBank class="size-4 text-emerald-500" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.monthly_savings)}</p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Presupuesto usado</span>
            <Gauge class="size-4 text-amber-500" />
        </div>
        <p class="text-2xl font-semibold">{pct(summary.budget_used_pct)}</p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Promedio diario</span>
            <CalendarDays class="size-4 text-sky-500" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.daily_average_expense)}</p>
    </div>
</section>
