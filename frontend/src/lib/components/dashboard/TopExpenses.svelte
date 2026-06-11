<script lang="ts">
    import type { DashboardMovement } from '$lib/stores/dashboard.svelte'
    import { formatArs } from '$lib/stores/currency.svelte'

    let { expenses }: { expenses: DashboardMovement[] } = $props()
    const fmt = (value: number) => formatArs(value)
</script>

<section class="rounded-lg border border-border bg-card p-4">
    <h2 class="mb-3 text-sm font-semibold">Top 5 gastos</h2>
    <div class="flex flex-col gap-2">
        {#each expenses as item, index}
            <div class="flex items-center justify-between gap-3 rounded-md bg-muted/45 px-3 py-2">
                <div class="min-w-0">
                    <p class="truncate text-sm font-medium">{index + 1}. {item.descripcion}</p>
                    <p class="truncate text-xs text-muted-foreground">{item.categoria}</p>
                </div>
                <p class="shrink-0 font-semibold">{fmt(item.monto)}</p>
            </div>
        {/each}
        {#if expenses.length === 0}
            <p class="py-8 text-center text-sm text-muted-foreground">Sin gastos destacados.</p>
        {/if}
    </div>
</section>
