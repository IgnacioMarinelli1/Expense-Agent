<script lang="ts">
    import { ArrowDownRight, ArrowUpRight, PiggyBank, Wallet, Gauge, CalendarDays, ShieldCheck, Banknote } from '@lucide/svelte'
    import type { DashboardSummary } from '$lib/stores/dashboard.svelte'
    import { formatArs } from '$lib/stores/currency.svelte'

    let { summary }: { summary: DashboardSummary } = $props()

    const fmt = (value: number | null | undefined) => formatArs(value)

    const pct = (value: number | null | undefined) =>
        value === null || value === undefined ? 'Sin presupuesto' : `${Math.round(value)}%`

    const budgetRemaining = $derived(
        summary.budget != null ? summary.budget - summary.expenses : null
    )
</script>

<section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Sueldo</span>
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
            <span class="text-xs font-medium">Presupuesto disponible</span>
            <ShieldCheck class="size-4 text-violet-500" />
        </div>
        {#if budgetRemaining !== null}
            <p class="text-2xl font-semibold" class:text-emerald-500={budgetRemaining >= 0} class:text-red-500={budgetRemaining < 0}>
                {fmt(budgetRemaining)}
            </p>
        {:else}
            <p class="text-2xl font-semibold text-muted-foreground">Sin presupuesto</p>
        {/if}
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Promedio diario</span>
            <CalendarDays class="size-4 text-sky-500" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.daily_average_expense)}</p>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between text-muted-foreground">
            <span class="text-xs font-medium">Cobrado</span>
            <Banknote class="size-4 text-emerald-400" />
        </div>
        <p class="text-2xl font-semibold">{fmt(summary.cobrado)}</p>
    </div>
</section>
