<script lang="ts">
    import { onMount } from 'svelte'
    import { api } from '$lib/api/client'

    let total = $state(0)
    let pagado = $state(0)
    let pendiente = $state(0)
    let cantidad_pagos = $state(0)
    let cantidad_pendientes = $state(0)
    let cargando = $state(true)
    let error = $state('')

    const mesActual = new Date().toISOString().slice(0, 7) // YYYY-MM
    const mesLabel = new Date().toLocaleString('es-AR', { month: 'long', year: 'numeric' })

    onMount(async () => {
        try {
            const res = await api.getResumen(mesActual)
            total = res.total
            pagado = res.pagado
            pendiente = res.pendiente
            cantidad_pagos = res.cantidad_pagos
            cantidad_pendientes = res.cantidad_pendientes
        } catch (e) {
            error = 'No se pudo cargar el resumen.'
        } finally {
            cargando = false
        }
    })

    function fmt(n: number) {
        return '$' + n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    }
</script>

<div style="
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
">
    <h1 style="font-size: 1.1rem; font-weight: 600; margin: 0; text-transform: capitalize;">
        Resumen {mesLabel}
    </h1>

    {#if cargando}
        <div style="text-align: center; padding: 2rem; color: var(--muted-foreground);">
            Cargando resumen...
        </div>
    {:else if error}
        <div style="text-align: center; padding: 2rem; color: #ef4444; font-size: 0.875rem;">
            {error}
        </div>
    {:else}
        <!-- Tarjetas -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;">
            <div style="border-radius: 0.75rem; padding: 0.875rem; border: 1px solid var(--border); background: var(--card);">
                <p style="font-size: 0.7rem; color: var(--muted-foreground); margin: 0 0 0.25rem;">Gastado</p>
                <p style="font-weight: 600; font-size: 0.875rem; margin: 0;">{fmt(pagado)}</p>
            </div>
            <div style="border-radius: 0.75rem; padding: 0.875rem; border: 1px solid var(--border); background: var(--card);">
                <p style="font-size: 0.7rem; color: var(--muted-foreground); margin: 0 0 0.25rem;">Pendiente</p>
                <p style="font-weight: 600; font-size: 0.875rem; margin: 0;">{fmt(pendiente)}</p>
            </div>
            <div style="border-radius: 0.75rem; padding: 0.875rem; border: 1px solid var(--border); background: var(--card);">
                <p style="font-size: 0.7rem; color: var(--muted-foreground); margin: 0 0 0.25rem;">Pagos</p>
                <p style="font-weight: 600; font-size: 0.875rem; margin: 0;">{cantidad_pagos} / {cantidad_pagos + cantidad_pendientes}</p>
            </div>
        </div>

        <!-- Total -->
        {#if total > 0}
            <div style="
            border-radius: 0.75rem; padding: 1.25rem;
            background: var(--primary); color: var(--primary-foreground);
            display: flex; justify-content: space-between; align-items: center;
          ">
                <div>
                    <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Total del mes</p>
                    <p style="font-size: 1.5rem; font-weight: 600; margin: 0;">{fmt(total)}</p>
                </div>
                <div style="text-align: right;">
                    <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Pagado</p>
                    <p style="font-size: 1rem; font-weight: 600; margin: 0;">
                        {total > 0 ? Math.round(pagado / total * 100) : 0}%
                    </p>
                </div>
            </div>
        {/if}
    {/if}

    <!-- Placeholders Sprint 3 -->
    <div style="
    border-radius: 0.75rem; border: 1px solid var(--border); background: var(--card);
    height: 200px; display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 0.5rem;
  ">
        <span style="font-size: 2rem;">📊</span>
        <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 0;">Gráfico por categoría</p>
        <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0;">Disponible en Sprint 3</p>
    </div>

    <div style="
    border-radius: 0.75rem; border: 1px solid var(--border); background: var(--card);
    height: 160px; display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 0.5rem;
  ">
        <span style="font-size: 2rem;">📅</span>
        <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 0;">Calendario de vencimientos</p>
        <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0;">Disponible en Sprint 3</p>
    </div>
</div>
