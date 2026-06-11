<script lang="ts">
    import type { DashboardBudgetItem } from '$lib/stores/dashboard.svelte'
    import { formatArs } from '$lib/stores/currency.svelte'

    let { budgets }: { budgets: DashboardBudgetItem[] } = $props()

    const fmt = (value: number | null | undefined) =>
        value === null || value === undefined ? 'Sin definir' : formatArs(value)

    function color(status: DashboardBudgetItem['status']) {
        if (status === 'exceeded') return 'bg-red-500'
        if (status === 'warning') return 'bg-amber-500'
        if (status === 'ok') return 'bg-emerald-500'
        return 'bg-slate-400'
    }

    function width(item: DashboardBudgetItem) {
        return Math.min(100, Math.max(0, item.used_pct ?? 0))
    }
</script>

<section class="rounded-lg border border-border bg-card p-4">
    <h2 class="mb-3 text-sm font-semibold">Presupuesto vs gasto real</h2>
    <div class="flex max-h-[330px] flex-col gap-3 overflow-y-auto pr-1">
        {#each budgets as item}
            <div>
                <div class="mb-1 flex items-center justify-between gap-3 text-sm">
                    <span class="truncate font-medium">{item.category}</span>
                    <span class="shrink-0 text-xs text-muted-foreground">{fmt(item.spent)} / {fmt(item.budgeted)}</span>
                </div>
                <div class="h-2 overflow-hidden rounded-full bg-muted">
                    <div class="h-full rounded-full {color(item.status)}" style="width: {width(item)}%"></div>
                </div>
            </div>
        {/each}
    </div>
</section>
