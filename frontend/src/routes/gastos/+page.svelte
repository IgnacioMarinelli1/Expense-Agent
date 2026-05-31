<script lang="ts">
    import { onMount } from 'svelte'
    import { appState, invalidar } from '$lib/stores/appState.svelte'
    import { api } from '$lib/api/client'
    import { Check, CheckCircle2 } from '@lucide/svelte'

    const mesActual = new Date().toISOString().slice(0, 7)

    const colores: Record<string, string> = {
        luz:       'var(--cat-luz)',
        gas:       'var(--cat-gas)',
        agua:      'var(--cat-agua)',
        impuesto:  'var(--cat-impuesto)',
        expensas:  'var(--cat-expensas)',
        telefonia: 'var(--cat-telefonia)',
    }

    onMount(() => {
        if (appState.gastos.length === 0) {
            invalidar(mesActual)
        }
    })

    async function marcarPagado(id: string) {
        await api.marcarPagado(id)
    }

    const gastos     = $derived(appState.gastos)
    const cargando   = $derived(appState.cargando)
    const error      = $derived(appState.error)
    const pendientes = $derived(gastos.filter((g) => !g.pagado))
    const pagados    = $derived(gastos.filter((g) =>  g.pagado))
    const totalMes   = $derived(gastos.reduce((acc: number, g) => acc + g.monto, 0))
</script>

<div class="flex max-h-[calc(100vh-120px)] flex-col gap-4 overflow-y-auto p-4">
    {#if cargando && gastos.length === 0}
        <div class="py-8 text-center text-sm text-muted-foreground">
            Cargando gastos...
        </div>
    {:else if error && gastos.length === 0}
        <div class="py-8 text-center text-sm text-destructive">
            {error}
        </div>
    {:else}
        <!-- Resumen -->
        <div
            class="flex items-center justify-between rounded-2xl bg-primary px-5 py-5 text-primary-foreground shadow-sm"
        >
            <div>
                <p class="mb-1 text-xs opacity-80">Total del mes</p>
                <p class="text-2xl font-semibold">
                    ${totalMes.toLocaleString('es-AR')}
                </p>
            </div>
            <div class="text-right">
                <p class="mb-1 text-xs opacity-80">Pendientes</p>
                <p class="text-2xl font-semibold">{pendientes.length}</p>
            </div>
        </div>

        <!-- Pendientes -->
        {#if pendientes.length > 0}
            <section>
                <h2 class="mb-2 text-xs font-medium text-muted-foreground">
                    Pendientes
                </h2>
                <div class="flex flex-col gap-2">
                    {#each pendientes as gasto (gasto.id)}
                        <div
                            class="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 shadow-sm transition-colors hover:border-foreground/20"
                        >
                            <div class="flex items-center gap-3">
                                <div
                                    class="h-10 w-1 shrink-0 rounded-full"
                                    style="background: {colores[gasto.categoria] ?? 'var(--cat-expensas)'};"
                                ></div>
                                <div>
                                    <p class="text-sm font-medium">{gasto.tipo}</p>
                                    <p class="mt-0.5 text-xs text-muted-foreground">
                                        {#if gasto.vencimiento}
                                            Vence {gasto.vencimiento}
                                        {:else}
                                            Sin fecha de vencimiento
                                        {/if}
                                    </p>
                                </div>
                            </div>
                            <div class="flex items-center gap-3">
                                <p class="font-semibold">${gasto.monto.toLocaleString('es-AR')}</p>
                                <button
                                    onclick={() => marcarPagado(gasto.id)}
                                    class="inline-flex items-center gap-1 rounded-md border border-border bg-transparent px-2.5 py-1.5 text-xs font-medium text-foreground transition-all hover:bg-muted active:scale-95"
                                >
                                    <Check class="size-3.5" /> Pagar
                                </button>
                            </div>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        <!-- Pagados -->
        {#if pagados.length > 0}
            <section>
                <h2 class="mb-2 text-xs font-medium text-muted-foreground">
                    Pagados este mes
                </h2>
                <div class="flex flex-col gap-2">
                    {#each pagados as gasto (gasto.id)}
                        <div
                            class="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 opacity-60 shadow-sm transition-opacity hover:opacity-100"
                        >
                            <div class="flex items-center gap-3">
                                <div
                                    class="h-10 w-1 shrink-0 rounded-full"
                                    style="background: {colores[gasto.categoria] ?? 'var(--cat-expensas)'};"
                                ></div>
                                <div>
                                    <p class="text-sm font-medium">{gasto.tipo}</p>
                                    <p class="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                                        Pagado {gasto.fecha} <CheckCircle2 class="size-3" />
                                    </p>
                                </div>
                            </div>
                            <p class="font-semibold">${gasto.monto.toLocaleString('es-AR')}</p>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        {#if gastos.length === 0}
            <div class="py-12 text-center text-sm text-muted-foreground">
                No hay gastos registrados. ¡Usá el chat para agregar uno!
            </div>
        {/if}
    {/if}
</div>