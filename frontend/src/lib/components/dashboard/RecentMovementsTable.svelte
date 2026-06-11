<script lang="ts">
    import type { DashboardMovement } from '$lib/stores/dashboard.svelte'
    import { formatArs } from '$lib/stores/currency.svelte'

    let { movements }: { movements: DashboardMovement[] } = $props()

    const fmt = (value: number) => formatArs(value)
</script>

<section class="rounded-lg border border-border bg-card">
    <div class="border-b border-border px-4 py-3">
        <h2 class="text-sm font-semibold">Ultimos movimientos</h2>
    </div>
    <div class="overflow-x-auto">
        <table class="w-full min-w-[780px] text-sm">
            <thead class="bg-muted/50 text-xs text-muted-foreground">
                <tr>
                    <th class="px-4 py-2 text-left font-medium">Fecha</th>
                    <th class="px-4 py-2 text-left font-medium">Tipo</th>
                    <th class="px-4 py-2 text-left font-medium">Categoria</th>
                    <th class="px-4 py-2 text-left font-medium">Subcategoria</th>
                    <th class="px-4 py-2 text-left font-medium">Descripcion</th>
                    <th class="px-4 py-2 text-left font-medium">Medio</th>
                    <th class="px-4 py-2 text-left font-medium">Cuenta</th>
                    <th class="px-4 py-2 text-right font-medium">Monto</th>
                </tr>
            </thead>
            <tbody>
                {#each movements as movement}
                    <tr class="border-t border-border">
                        <td class="px-4 py-3">{movement.fecha}</td>
                        <td class="px-4 py-3">
                            <span class="rounded-full px-2 py-0.5 text-xs {movement.tipo === 'ingreso' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'}">
                                {movement.tipo}
                            </span>
                        </td>
                        <td class="px-4 py-3">{movement.categoria}</td>
                        <td class="px-4 py-3 text-muted-foreground">{movement.subcategoria ?? '-'}</td>
                        <td class="px-4 py-3">{movement.descripcion}</td>
                        <td class="px-4 py-3 text-muted-foreground">{movement.medioPago ?? '-'}</td>
                        <td class="px-4 py-3 text-muted-foreground">{movement.cuenta ?? '-'}</td>
                        <td class="px-4 py-3 text-right font-semibold {movement.tipo === 'ingreso' ? 'text-emerald-600' : ''}">
                            {fmt(movement.monto)}
                        </td>
                    </tr>
                {/each}
                {#if movements.length === 0}
                    <tr>
                        <td colspan="8" class="px-4 py-10 text-center text-muted-foreground">No hay movimientos para estos filtros.</td>
                    </tr>
                {/if}
            </tbody>
        </table>
    </div>
</section>
