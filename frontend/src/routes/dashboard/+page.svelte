<script lang="ts">
    import { onMount } from 'svelte'
    import { api } from '$lib/api/client'
    import { Receipt, Clock, ListChecks } from '@lucide/svelte'
    import { Chart, registerables } from 'chart.js'

    Chart.register(...registerables)

    // ─── Tipos ───────────────────────────────────────────────────────────────────
    interface Categoria {
        label: string
        valor: number
        color: string
    }

interface Vencimiento {
        nombre: string
        vencimiento: string // "YYYY-MM-DD"
        monto: number
        pagado: boolean
        categoria: string // <-- NUEVO: Para separar en secciones
    }

    // ─── Estado reactivo (Svelte 5 runes) ────────────────────────────────────────
    let total              = $state(0)
    let pagado             = $state(0)
    let pendiente          = $state(0)
    let cantidad_pagos     = $state(0)
    let cantidad_pendientes = $state(0)
    let categorias         = $state<Categoria[]>([])
    let vencimientos       = $state<Vencimiento[]>([])
    let cargando           = $state(true)
    let error              = $state('')

    const mesActual = new Date().toISOString().slice(0, 7)
    const mesLabel  = new Date().toLocaleString('es-AR', { month: 'long', year: 'numeric' })

    // ─── Chart.js canvas ─────────────────────────────────────────────────────────
    let chartCanvas: HTMLCanvasElement
    let chartInstance: Chart | null = null

    // ─── Helpers ─────────────────────────────────────────────────────────────────
    function fmt(n: number): string {
        return '$' + n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    }

    function diasRestantes(fechaStr: string): number {
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        const fecha = new Date(fechaStr + 'T00:00:00')
        return Math.round((fecha.getTime() - hoy.getTime()) / 86_400_000)
    }

    function labelFecha(fechaStr: string): string {
        const dias = diasRestantes(fechaStr)
        if (dias === 0)  return 'Hoy'
        if (dias === 1)  return 'Mañana'
        if (dias < 0)   return 'Vencido'
        const d = new Date(fechaStr + 'T00:00:00')
        return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })
    }

    function esCritico(fechaStr: string): boolean {
        return diasRestantes(fechaStr) < 2
    }

    // ─── Derivados ────────────────────────────────────────────────────────────────
    const porcentaje = $derived(total > 0 ? Math.round((pagado / total) * 100) : 0)

    const vencimientosPendientes = $derived(
        vencimientos
            .filter(v => !v.pagado)
            .sort((a, b) => diasRestantes(a.vencimiento) - diasRestantes(b.vencimiento))
    )

    // NUEVO: Agrupamos los vencimientos por su categoría
    const vencimientosAgrupados = $derived(
        vencimientosPendientes.reduce((acc, curr) => {
            if (!acc[curr.categoria]) acc[curr.categoria] = [];
            acc[curr.categoria].push(curr);
            return acc;
        }, {} as Record<string, Vencimiento[]>)
    )

    // ─── Datos de fallback (para desarrollo sin backend) ─────────────────────────
    function cargarDatosFallback() {
        const hoy = new Date()
        function fechaOffset(dias: number): string {
            const d = new Date(hoy)
            d.setDate(d.getDate() + dias)
            return d.toISOString().split('T')[0]
        }

        total               = 1_115_000
        pagado              = 1_080_060
        pendiente           = 34_940
        cantidad_pagos      = 12
        cantidad_pendientes = 2

        categorias = [
            { label: 'Supermercado',  valor: 420_000, color: '#34d399' },
            { label: 'Suscripciones', valor:  85_000, color: '#60a5fa' },
            { label: 'Ferrari',       valor: 350_000, color: '#f472b6' },
            { label: 'Servicios',     valor: 120_000, color: '#a78bfa' },
            { label: 'Otros',         valor: 105_060, color: '#fbbf24' },
        ]

        vencimientos = [
            { nombre: 'Netflix',          vencimiento: fechaOffset(0),  monto:  6_500, pagado: false, categoria: 'Entretenimiento' },
            { nombre: 'Spotify',          vencimiento: fechaOffset(1),  monto:  3_499, pagado: false, categoria: 'Entretenimiento' },
            { nombre: 'Expensas',         vencimiento: fechaOffset(4),  monto: 85_000, pagado: false, categoria: 'Hogar y Expensas' },
            { nombre: 'Internet',         vencimiento: fechaOffset(6),  monto: 12_000, pagado: true,  categoria: 'Servicios' },
            { nombre: 'Luz (EDESUR)',     vencimiento: fechaOffset(9),  monto: 18_400, pagado: false, categoria: 'Impuestos y Servicios' },
            { nombre: 'Gas (Metrogas)',   vencimiento: fechaOffset(11), monto:  9_200, pagado: false, categoria: 'Impuestos y Servicios' },
            { nombre: 'Gym',              vencimiento: fechaOffset(13), monto: 22_000, pagado: true,  categoria: 'Salud' },
        ]
    }
    // ─── Chart builder ───────────────────────────────────────────────────────────
    function buildChart() {
        if (!chartCanvas || categorias.length === 0) return
        chartInstance?.destroy()

        chartInstance = new Chart(chartCanvas, {
            type: 'doughnut',
            data: {
                labels: categorias.map(c => c.label),
                datasets: [{
                    data:            categorias.map(c => c.valor),
                    backgroundColor: categorias.map(c => c.color),
                    borderWidth: 0,
                    hoverOffset: 6,
                }],
            },
            options: {
                cutout: '72%', // <-- Reducido de 78% a 72% para que el anillo sea más grueso
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: 'hsl(var(--muted-foreground))',
                            font: { size: 12 }, // <-- Letra un poco más grande
                            usePointStyle: true,
                            pointStyleWidth: 10,
                            padding: 24, // <-- Mayor separación entre los ítems de la leyenda
                        },
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${fmt(ctx.parsed)}`,
                        },
                    },
                },
                animation: { animateRotate: true, duration: 700 },
            },
        })
    }

    // ─── onMount: fetch real al backend FastAPI ───────────────────────────────────
    onMount(async () => {
        try {
            const res = await api.getResumen(mesActual)
            total               = res.total
            pagado              = res.pagado
            pendiente           = res.pendiente
            cantidad_pagos      = res.cantidad_pagos
            cantidad_pendientes = res.cantidad_pendientes

            // TODO: descomentar cuando el backend exponga estos endpoints
            // const [cats, venc] = await Promise.all([
            //     api.getCategorias(mesActual),
            //     api.getVencimientos(mesActual),
            // ])
            // categorias   = cats
            // vencimientos = venc

            // Mientras tanto, cargamos el resto como fallback
            cargarDatosFallback()
            categorias = categorias   // Nota: reemplazar con datos reales cuando estén
            vencimientos = vencimientos

        } catch (e) {
            error = 'No se pudo cargar el resumen.'
            cargarDatosFallback()
        } finally {
            cargando = false
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

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!--  TEMPLATE                                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

<div class="flex max-h-[calc(100vh-120px)] flex-col gap-4 overflow-y-auto p-4 text-zinc-900 dark:text-white">

    <h1 class="text-lg font-bold capitalize">
        Resumen {mesLabel}
    </h1>

    {#if cargando}
        <div class="animate-pulse space-y-3">
            <div class="grid grid-cols-3 gap-3">
                {#each [1, 2, 3] as _}
                    <div class="h-[72px] rounded-xl bg-muted"></div>
                {/each}
            </div>
            <div class="h-[100px] rounded-xl bg-muted"></div>
            <div class="h-[260px] rounded-xl bg-muted"></div>
            <div class="h-[200px] rounded-xl bg-muted"></div>
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
                <p class="text-sm font-bold">{fmt(pagado)}</p>
            </div>

            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                    <Clock class="size-3.5" />
                    <p class="text-[0.7rem]">Pendiente</p>
                </div>
                <p class="text-sm font-bold">{fmt(pendiente)}</p>
            </div>

            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-zinc-500 dark:text-zinc-400">
                    <ListChecks class="size-3.5" />
                    <p class="text-[0.7rem]">Pagos</p>
                </div>
                <p class="text-sm font-bold">{cantidad_pagos} / {cantidad_pagos + cantidad_pendientes}</p>
            </div>
        </div>

        {#if total > 0}
            <div class="rounded-xl bg-primary px-5 py-5 text-primary-foreground shadow-sm">
                <div class="mb-3 flex items-start justify-between">
                    <div>
                        <p class="mb-1 text-xs opacity-80">Total del mes</p>
                        <p class="text-2xl font-bold tracking-tight">{fmt(total)}</p>
                    </div>
                    <div class="text-right">
                        <p class="mb-1 text-xs opacity-80">Pagado</p>
                        <p class="text-xl font-bold">{porcentaje}%</p>
                    </div>
                </div>

                <div class="relative h-[6px] w-full overflow-hidden rounded-full bg-black/20 dark:bg-white/20">
                    <div
                        class="absolute left-0 top-0 h-full rounded-full bg-white transition-all duration-700"
                        style="width: {porcentaje}%"
                    ></div>
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