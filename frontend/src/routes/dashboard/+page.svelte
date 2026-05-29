<script lang="ts">
    import { onMount } from 'svelte'
    import { api } from '$lib/api/client'
    import { Receipt, Clock, ListChecks, PieChart, CalendarDays } from '@lucide/svelte'

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
            cargarDatosFallback()
        } finally {
            loading = false
        }

        // El canvas ya existe en el DOM en este punto
        buildChart()

        return () => chartInstance?.destroy()
    })

    // Re-construir el gráfico si cambian las categorías (ej: después de un fetch)
    $effect(() => {
        if (!cargando && categorias.length > 0) {
            buildChart()
        }
    })
</script>

<div class="flex max-h-[calc(100vh-120px)] flex-col gap-4 overflow-y-auto p-4">
    <h1 class="text-lg font-semibold capitalize">
        Resumen {mesLabel}
    </h1>

    {#if cargando}
        <div class="py-8 text-center text-sm text-muted-foreground">
            Cargando resumen...
        </div>

    {:else if error && total === 0}
        <div class="py-8 text-center text-sm text-destructive font-semibold">
            {error}
        </div>

    {:else}
        <div class="grid grid-cols-3 gap-3">
            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                    <Receipt class="size-3.5" />
                    <p class="text-[0.7rem]">Gastado</p>
                </div>
                <p class="text-sm font-semibold">{fmt(pagado)}</p>
            </div>

            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                    <Clock class="size-3.5" />
                    <p class="text-[0.7rem]">Pendiente</p>
                </div>
                <p class="text-sm font-semibold">{fmt(pendiente)}</p>
            </div>

            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                    <ListChecks class="size-3.5" />
                    <p class="text-[0.7rem]">Pagos</p>
                </div>
                <p class="text-sm font-semibold">{cantidad_pagos} / {cantidad_pagos + cantidad_pendientes}</p>
            </div>
        </div>

        {#if total > 0}
            <div
                class="flex items-center justify-between rounded-xl bg-primary px-5 py-5 text-primary-foreground shadow-sm"
            >
                <div>
                    <p class="mb-1 text-xs opacity-80">Total del mes</p>
                    <p class="text-2xl font-semibold">{fmt(total)}</p>
                </div>
                <div class="text-right">
                    <p class="mb-1 text-xs opacity-80">Pagado</p>
                    <p class="text-base font-semibold">
                        {total > 0 ? Math.round(pagado / total * 100) : 0}%
                    </p>
                </div>
                <p class="mt-1.5 text-right text-[10px] opacity-70 font-medium">
                    {fmt(pendiente)} pendiente
                </p>
            </div>
        {/if}

        <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div class="mb-3 flex items-center justify-between">
                <p class="text-sm font-bold">Por categoría</p>
                <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 capitalize">
                    {mesLabel}
                </span>
            </div>

            <div class="mx-auto w-full max-w-[320px] pb-4">
                <canvas bind:this={chartCanvas}></canvas>
            </div>
        </div>

        <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
            <div class="mb-4 flex items-center justify-between border-b border-border pb-3">
                <p class="text-sm font-bold">Vencimientos</p>
                {#if vencimientosPendientes.length > 0}
                    <span class="rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold text-zinc-600 dark:text-zinc-300">
                        {vencimientosPendientes.length} pendientes
                    </span>
                {/if}
            </div>

            <div class="max-h-64 space-y-5 overflow-y-auto pr-1 scrollbar-thin">
                
                {#each Object.entries(vencimientosAgrupados) as [categoria, items]}
                    <div>
                        <h3 class="text-[11px] font-bold uppercase tracking-widest text-zinc-500 dark:text-zinc-400 mb-2">
                            {categoria}
                        </h3>
                        
                        <div class="space-y-2">
                            {#each items as item (item.nombre)}
                                <div
                                    class="flex items-center justify-between rounded-lg border px-3 py-2.5 transition-colors
                                           {esCritico(item.vencimiento)
                                               ? 'border-red-500/30 bg-red-500/5'
                                               : 'border-border bg-zinc-50 dark:bg-zinc-800/50 hover:border-zinc-300 dark:hover:border-zinc-700'}"
                                >
                                    <div class="flex min-w-0 items-center gap-2.5">
                                        <span
                                            class="size-2 flex-shrink-0 rounded-full
                                                   {esCritico(item.vencimiento) ? 'bg-red-500' : 'bg-zinc-300 dark:bg-zinc-600'}"
                                        ></span>

                                        <div class="min-w-0">
                                            <p class="truncate text-sm font-bold leading-tight">{item.nombre}</p>
                                            <p
                                                class="text-[11px] leading-tight font-medium
                                                       {esCritico(item.vencimiento) ? 'text-red-500' : 'text-zinc-500 dark:text-zinc-400'}"
                                            >
                                                {labelFecha(item.vencimiento)}
                                                {#if diasRestantes(item.vencimiento) >= 2}
                                                    · {diasRestantes(item.vencimiento)}d
                                                {/if}
                                            </p>
                                        </div>
                                    </div>

                                    <span class="ml-3 flex-shrink-0 font-mono text-sm font-bold">
                                        {fmt(item.monto)}
                                    </span>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}

                {#if vencimientosPendientes.length === 0}
                    <p class="py-4 text-center text-sm text-zinc-500 dark:text-zinc-400 font-medium">¡Todo al día! 🎉</p>
                {/if}
            </div>
        </div>

        {#if error}
            <p class="text-center text-[11px] text-zinc-500 dark:text-zinc-400 font-medium">
                ⚠️ Mostrando datos de ejemplo · {error}
            </p>
        {/if}

    {/if}
</div>

<style>
    .scrollbar-thin::-webkit-scrollbar        { width: 3px; }
    .scrollbar-thin::-webkit-scrollbar-track  { background: transparent; }
    .scrollbar-thin::-webkit-scrollbar-thumb  { background: hsl(var(--border)); border-radius: 99px; }
</style>