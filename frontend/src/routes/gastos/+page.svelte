<script lang="ts">
    import { onMount } from 'svelte'
    import { api } from '$lib/api/client'
    import type { Gasto } from '$lib/stores/gastos'

    let gastos = $state<Gasto[]>([])
    let cargando = $state(true)
    let error = $state('')

    const colores: Record<string, string> = {
        luz:       'var(--cat-luz)',
        gas:       'var(--cat-gas)',
        agua:      'var(--cat-agua)',
        impuesto:  'var(--cat-impuesto)',
        expensas:  'var(--cat-expensas)',
        telefonia: 'var(--cat-telefonia)',
    }

    onMount(async () => {
        try {
            gastos = await api.getGastos()
        } catch (e) {
            error = 'No se pudo cargar los gastos. ¿El backend está corriendo?'
        } finally {
            cargando = false
        }
    })

    async function marcarPagado(id: string) {
        await api.marcarPagado(id)
        gastos = gastos.map(g => g.id === id ? { ...g, pagado: true } : g)
    }

    $derived: var pendientes = gastos.filter(g => !g.pagado)
    $derived: var pagados    = gastos.filter(g =>  g.pagado)
    $derived: var totalMes   = gastos.reduce((acc, g) => acc + g.monto, 0)
</script>

<div style="
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
">
    {#if cargando}
        <div style="text-align: center; padding: 2rem; color: var(--muted-foreground);">
            Cargando gastos...
        </div>
    {:else if error}
        <div style="text-align: center; padding: 2rem; color: #ef4444; font-size: 0.875rem;">
            {error}
        </div>
    {:else}
        <!-- Resumen -->
        <div style="
        border-radius: 1rem;
        padding: 1.25rem;
        display: flex;
        justify-content: space-between;
        background: var(--primary);
        color: var(--primary-foreground);
      ">
            <div>
                <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Total del mes</p>
                <p style="font-size: 1.5rem; font-weight: 600; margin: 0;">
                    ${totalMes.toLocaleString('es-AR')}
                </p>
            </div>
            <div style="text-align: right;">
                <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Pendientes</p>
                <p style="font-size: 1.5rem; font-weight: 600; margin: 0;">{pendientes.length}</p>
            </div>
        </div>

        <!-- Pendientes -->
        {#if pendientes.length > 0}
            <section>
                <h2 style="font-size: 0.8rem; color: var(--muted-foreground); margin: 0 0 0.5rem;">
                    Pendientes
                </h2>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    {#each pendientes as gasto}
                        <div style="
                border-radius: 0.75rem;
                padding: 1rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border: 1px solid var(--border);
                background: var(--card);
              ">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="
                    width: 4px; height: 2.5rem;
                    border-radius: 99px;
                    background: {colores[gasto.categoria] ?? 'var(--cat-expensas)'};
                  "></div>
                                <div>
                                    <p style="font-weight: 500; font-size: 0.875rem; margin: 0;">{gasto.tipo}</p>
                                    <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0.2rem 0 0;">
                                        Vence {gasto.vencimiento ?? gasto.fecha}
                                    </p>
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <p style="font-weight: 600; margin: 0;">${gasto.monto.toLocaleString('es-AR')}</p>
                                <button
                                    onclick={() => marcarPagado(gasto.id)}
                                    style="
                      font-size: 0.7rem; padding: 0.25rem 0.5rem;
                      border-radius: 0.375rem; border: 1px solid var(--border);
                      background: transparent; cursor: pointer; color: var(--foreground);
                    "
                                >✓ Pagar</button>
                            </div>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        <!-- Pagados -->
        {#if pagados.length > 0}
            <section>
                <h2 style="font-size: 0.8rem; color: var(--muted-foreground); margin: 0 0 0.5rem;">
                    Pagados este mes
                </h2>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    {#each pagados as gasto}
                        <div style="
              border-radius: 0.75rem;
              padding: 1rem;
              display: flex;
              align-items: center;
              justify-content: space-between;
              border: 1px solid var(--border);
              background: var(--card);
              opacity: 0.6;
            ">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="
                  width: 4px; height: 2.5rem;
                  border-radius: 99px;
                  background: {colores[gasto.categoria] ?? 'var(--cat-expensas)'};
                "></div>
                                <div>
                                    <p style="font-weight: 500; font-size: 0.875rem; margin: 0;">{gasto.tipo}</p>
                                    <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0.2rem 0 0;">
                                        Pagado {gasto.fecha} ✓
                                    </p>
                                </div>
                            </div>
                            <p style="font-weight: 600; margin: 0;">${gasto.monto.toLocaleString('es-AR')}</p>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        {#if gastos.length === 0}
            <div style="text-align: center; padding: 3rem; color: var(--muted-foreground); font-size: 0.875rem;">
                No hay gastos registrados. ¡Usá el chat para agregar uno!
            </div>
        {/if}
    {/if}
</div>
