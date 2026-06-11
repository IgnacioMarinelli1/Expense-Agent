<script lang="ts">
    import { Filter } from '@lucide/svelte'
    import type { DashboardFilterOptions, DashboardQuery, DashboardTypeFilter } from '$lib/stores/dashboard.svelte'

    let {
        filters,
        options,
        onChange,
    }: {
        filters: DashboardQuery
        options: DashboardFilterOptions
        onChange: (filters: Partial<DashboardQuery>) => void
    } = $props()

    function valueFrom(event: Event) {
        return (event.currentTarget as HTMLInputElement | HTMLSelectElement).value || undefined
    }
</script>

<section class="rounded-lg border border-border bg-card p-3">
    <div class="mb-3 flex items-center gap-2 text-sm font-medium">
        <Filter class="size-4 text-muted-foreground" />
        Filtros
    </div>
    <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <input
            type="month"
            value={filters.month}
            onchange={(event) => onChange({ month: valueFrom(event) })}
            class="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/30"
        />
        <select
            value={filters.category ?? ''}
            onchange={(event) => onChange({ category: valueFrom(event) })}
            class="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/30"
        >
            <option value="">Todas las categorias</option>
            {#each options.categories as category}
                <option value={category}>{category}</option>
            {/each}
        </select>
        <select
            value={filters.payment_method ?? ''}
            onchange={(event) => onChange({ payment_method: valueFrom(event) })}
            class="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/30"
        >
            <option value="">Todos los medios</option>
            {#each options.paymentMethods as method}
                <option value={method}>{method}</option>
            {/each}
        </select>
        <select
            value={filters.account ?? ''}
            onchange={(event) => onChange({ account: valueFrom(event) })}
            class="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/30"
        >
            <option value="">Todas las cuentas</option>
            {#each options.accounts as account}
                <option value={account}>{account}</option>
            {/each}
        </select>
        <select
            value={filters.type}
            onchange={(event) => onChange({ type: (valueFrom(event) ?? 'all') as DashboardTypeFilter })}
            class="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/30"
        >
            <option value="all">Todo</option>
            <option value="expense">Gastos</option>
            <option value="income">Ingresos</option>
        </select>
    </div>
</section>
