<script lang="ts">
    import { onMount } from 'svelte'
    import { appState, invalidar } from '$lib/stores/appState.svelte'
    import { Receipt, Clock, ListChecks, AlertTriangle, TrendingUp } from '@lucide/svelte'
    import { Chart, registerables } from 'chart.js'
    import type { TooltipItem, ChartData, ScriptableContext } from 'chart.js'

    Chart.register(...registerables)

    // ─── Tipos ───────────────────────────────────────────────────────────────────

    interface Categoria {
        label: string
        valor: number
        color: string
    }

    interface ItemPendiente {
        id: string
        nombre: string
        /** "YYYY-MM-DD" o undefined si no tiene fecha */
        vencimiento?: string
        /** Monto que falta pagar */
        monto: number
        categoria: string
    }

    // ─── Constantes ──────────────────────────────────────────────────────────────

    const mesActual = new Date().toISOString().slice(0, 7)
    const mesLabel  = new Date().toLocaleString('es-AR', { month: 'long', year: 'numeric' })

    // ─── Chart.js canvas ─────────────────────────────────────────────────────────

    let doughnutCanvas = $state<HTMLCanvasElement | undefined>(undefined)
    let barCanvas      = $state<HTMLCanvasElement | undefined>(undefined)
    let doughnutInstance: Chart | null = null
    let barInstance:      Chart | null = null

    // ─── Helpers de formato ───────────────────────────────────────────────────────

    function fmt(n: number): string {
        return '$' + n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    }

    function diasRestantes(fechaStr: string): number {
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        const fecha = new Date(fechaStr + 'T00:00:00')
        return Math.round((fecha.getTime() - hoy.getTime()) / 86_400_000)
    }

    function labelFecha(fechaStr?: string): string {
        if (!fechaStr) return 'Sin fecha'
        const dias = diasRestantes(fechaStr)
        if (dias < 0)   return 'Vencido'
        if (dias === 0) return 'Hoy'
        if (dias === 1) return 'Mañana'
        const d = new Date(fechaStr + 'T00:00:00')
        return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })
    }

    function esCritico(fechaStr?: string): boolean {
        if (!fechaStr) return false
        return diasRestantes(fechaStr) < 2
    }

    // ─── Clasificación por buckets (categorías) ───────────────────────────────────

    const BUCKET_COLORS: Record<string, string> = {
        luz:             '#fbbf24',
        gas:             '#f97316',
        agua:            '#38bdf8',
        impuesto:        '#a78bfa',
        expensas:        '#34d399',
        telefonia:       '#60a5fa',
        'Sin categoría': '#94a3b8',
    }

    function toBucket(categoria: string): string {
        const map: Record<string, string> = {
            luz:       'Servicios',
            gas:       'Servicios',
            agua:      'Servicios',
            telefonia: 'Servicios',
            impuesto:  'Impuestos',
            expensas:  'Hogar',
        }
        return map[categoria] ?? 'Otros'
    }

    function colorForCategoria(categoria: string): string {
        return BUCKET_COLORS[categoria] ?? '#94a3b8'
    }

    // ─── Helper para construir categorías desde gastos ────────────────────────────

    function buildCategorias(gastos: { categoria: string; monto: number }[]): Categoria[] {
        const mapa = new Map<string, number>()
        for (const g of gastos) {
            const key = g.categoria || 'Sin categoría'
            mapa.set(key, (mapa.get(key) ?? 0) + g.monto)
        }
        return Array.from(mapa.entries()).map(([label, valor]) => ({
            label,
            valor,
            color: colorForCategoria(label),
        }))
    }

    // ─── Derivados desde appState (datos reales) ──────────────────────────────────

    const resumen = $derived(appState.resumen)

    const pendientes = $derived(
        appState.gastos
            .filter((g) => !g.pagado)
            .map<ItemPendiente>((g) => ({
                id:          g.id,
                nombre:      g.tipo,
                vencimiento: g.vencimiento ?? undefined,
                monto:       g.monto,
                categoria:   g.categoria,
            }))
            .sort((a: ItemPendiente, b: ItemPendiente) => {
                const da = a.vencimiento ? diasRestantes(a.vencimiento) : Infinity
                const db = b.vencimiento ? diasRestantes(b.vencimiento) : Infinity
                return da - db
            })
    )

    const categorias = $derived(buildCategorias(appState.gastos))

    const topCategorias = $derived(
        [...categorias].sort((a: Categoria, b: Categoria) => b.valor - a.valor).slice(0, 5)
    )

    const porcentaje = $derived(
        resumen.total > 0 ? Math.round((resumen.pagado / resumen.total) * 100) : 0
    )

    const montoPendienteProximo = $derived(
        pendientes
            .filter((v: ItemPendiente) => v.vencimiento && diasRestantes(v.vencimiento) <= 3)
            .reduce((s: number, v: ItemPendiente) => s + v.monto, 0)
    )

    const cargando = $derived(appState.cargando)
    const error    = $derived(appState.error)

    // ─── Chart: colores adaptativos dark/light ────────────────────────────────────

    function isDark(): boolean { return document.documentElement.classList.contains('dark') }
    function getTextColor(): string  { return isDark() ? '#f4f4f5' : '#18181b' }
    function getMutedColor(): string { return isDark() ? '#71717a' : '#a1a1aa' }
    function getGridColor(): string  { return isDark() ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)' }

    // ─── Doughnut chart ───────────────────────────────────────────────────────────

    function buildDoughnut() {
        if (!doughnutCanvas || categorias.length === 0) return
        doughnutInstance?.destroy()

        doughnutInstance = new Chart(doughnutCanvas, {
            type: 'doughnut',
            data: {
                labels:   categorias.map((c: Categoria) => c.label),
                datasets: [{
                    data:            categorias.map((c: Categoria) => c.valor),
                    backgroundColor: categorias.map((c: Categoria) => c.color),
                    borderWidth: 0,
                    hoverOffset: 8
                }],
            },
            options: {
                cutout: '75%', responsive: true, maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true, position: 'bottom',
                        labels: { color: getTextColor(), font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8, padding: 14 }
                    },
                    tooltip: {
                        backgroundColor: isDark() ? '#27272a' : '#ffffff',
                        titleColor: getTextColor(), bodyColor: getMutedColor(),
                        borderColor: isDark() ? '#3f3f46' : '#e4e4e7', borderWidth: 1,
                        callbacks: { label: (ctx: TooltipItem<'doughnut'>) => ` ${fmt(ctx.parsed)}` },
                    },
                },
                animation: { animateRotate: true, duration: 700 },
            },
        })
    }

    // ─── Bar chart ────────────────────────────────────────────────────────────────

    function buildBar() {
        if (!barCanvas || topCategorias.length === 0) return
        barInstance?.destroy()

        const maxVal = Math.max(...topCategorias.map((c: Categoria) => c.valor))

        barInstance = new Chart(barCanvas, {
            type: 'bar',
            data: {
                labels:   topCategorias.map((c: Categoria) => c.label),
                datasets: [{
                    data:            topCategorias.map((c: Categoria) => c.valor),
                    backgroundColor: topCategorias.map((c: Categoria) => c.color + 'cc'),
                    borderColor:     topCategorias.map((c: Categoria) => c.color),
                    borderWidth: 0, borderRadius: 6, borderSkipped: false,
                }],
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDark() ? '#27272a' : '#ffffff',
                        titleColor: getTextColor(), bodyColor: getMutedColor(),
                        borderColor: isDark() ? '#3f3f46' : '#e4e4e7', borderWidth: 1,
                        callbacks: { label: (ctx: TooltipItem<'bar'>) => ` ${fmt(ctx.raw as number)}` },
                    },
                },
                scales: {
                    x: {
                        max: maxVal * 1.15,
                        grid: { color: getGridColor() },
                        ticks: {
                            color: getMutedColor(), font: { size: 10 },
                            callback(value: number | string) {
                                const n = Number(value)
                                if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M'
                                if (n >= 1_000)     return '$' + (n / 1_000).toFixed(0) + 'k'
                                return '$' + n
                            },
                        },
                        border: { display: false },
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: getTextColor(), font: { size: 12 } },
                        border: { display: false }
                    },
                },
                animation: { duration: 600 },
            },
        })
    }

    function buildCharts() {
        buildDoughnut()
        buildBar()
    }

    // ─── Ciclo de vida ────────────────────────────────────────────────────────────

    onMount(() => {
        invalidar(mesActual)

        const observer = new MutationObserver(() => buildCharts())
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

        return () => {
            doughnutInstance?.destroy()
            barInstance?.destroy()
            observer.disconnect()
        }
    })

    $effect(() => {
        if (!cargando && categorias.length > 0) {
            buildCharts()
        }
    })
</script>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!--  TEMPLATE                                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

<div class="flex max-h-[calc(100vh-120px)] flex-col gap-4 overflow-y-auto p-4">

    <!-- Header -->
    <div class="flex items-center justify-between">
        <h1 class="text-lg font-semibold capitalize text-zinc-900 dark:text-white">
            Resumen {mesLabel}
        </h1>
        {#if error}
            <span class="flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <AlertTriangle class="size-3" />
                Sin conexión
            </span>
        {/if}
    </div>

    {#if cargando}
        <!-- ── Skeleton ──────────────────────────────────────────────────────── -->
        <div class="animate-pulse space-y-3">
            <div class="grid grid-cols-2 gap-3">
                {#each [1, 2, 3, 4] as _}
                    <div class="h-[80px] rounded-xl bg-zinc-100 dark:bg-zinc-800"></div>
                {/each}
            </div>
            <div class="h-[90px] rounded-xl bg-zinc-100 dark:bg-zinc-800"></div>
            <div class="h-[180px] rounded-xl bg-zinc-100 dark:bg-zinc-800"></div>
            <div class="h-[220px] rounded-xl bg-zinc-100 dark:bg-zinc-800"></div>
        </div>

    {:else}

        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <!-- KPI CARDS                                                             -->
        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <div class="grid grid-cols-2 gap-3">

            <!-- Pendiente (azul oscuro) -->
            <div class="col-span-1 rounded-xl bg-gradient-to-br from-blue-700 to-blue-900 p-4 shadow-sm">
                <p class="mb-1.5 text-[11px] font-medium text-blue-200">Monto pendiente</p>
                <p class="text-xl font-bold text-white">{fmt(resumen.pendiente)}</p>
            </div>

            <!-- Vence pronto (cyan) -->
            <div class="col-span-1 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 p-4 shadow-sm">
                <p class="mb-1.5 text-[11px] font-medium text-teal-100">Vence pronto</p>
                <p class="text-xl font-bold text-white">{fmt(montoPendienteProximo)}</p>
            </div>

            <!-- Total gastado (verde) -->
            <div class="col-span-1 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 p-4 shadow-sm">
                <p class="mb-1.5 text-[11px] font-medium text-emerald-100">Total gastado</p>
                <p class="text-xl font-bold text-white">{fmt(resumen.pagado)}</p>
            </div>

            <!-- Pagos completados (violeta) -->
            <div class="col-span-1 rounded-xl bg-gradient-to-br from-violet-600 to-violet-800 p-4 shadow-sm">
                <p class="mb-1.5 text-[11px] font-medium text-violet-200">Pagos completos</p>
                <p class="text-xl font-bold text-white">
                    {resumen.cantidad_pagos} / {resumen.cantidad_pagos + resumen.cantidad_pendientes}
                </p>
            </div>

        </div>

        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <!-- TOTAL + PROGRESS BAR                                                  -->
        <!-- ══════════════════════════════════════════════════════════════════════ -->
        {#if resumen.total > 0}
            <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
                <div class="mb-3 flex items-start justify-between">
                    <div>
                        <p class="mb-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">Total del mes</p>
                        <p class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">{fmt(resumen.total)}</p>
                    </div>
                    <div class="text-right">
                        <p class="mb-0.5 text-[11px] text-zinc-500 dark:text-zinc-400">Pagado</p>
                        <p class="text-xl font-bold text-zinc-900 dark:text-white">{porcentaje}%</p>
                    </div>
                </div>
                <div class="relative h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                    <div
                        class="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-blue-500 to-teal-400 transition-all duration-700"
                        style="width: {porcentaje}%"
                    ></div>
                </div>
                <div class="mt-2 flex justify-between text-[10px] text-zinc-400 dark:text-zinc-500">
                    <span class="flex items-center gap-1">
                        <span class="inline-block size-1.5 rounded-full bg-blue-500"></span>
                        Pagado: {fmt(resumen.pagado)}
                    </span>
                    <span class="flex items-center gap-1">
                        <span class="inline-block size-1.5 rounded-full bg-zinc-300 dark:bg-zinc-600"></span>
                        Pendiente: {fmt(resumen.pendiente)}
                    </span>
                </div>
            </div>
        {/if}

        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <!-- BAR CHART HORIZONTAL                                                  -->
        <!-- ══════════════════════════════════════════════════════════════════════ -->
        {#if topCategorias.length > 0}
            <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
                <div class="mb-3 flex items-center justify-between">
                    <p class="text-sm font-semibold text-zinc-900 dark:text-white">Top gastos por categoría</p>
                    <span class="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                        <TrendingUp class="size-3" />
                        {mesLabel}
                    </span>
                </div>
                <div style="height: {topCategorias.length * 44}px; min-height: 140px;">
                    <canvas bind:this={barCanvas}></canvas>
                </div>
            </div>
        {/if}

        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <!-- DOUGHNUT CHART                                                        -->
        <!-- ══════════════════════════════════════════════════════════════════════ -->
        {#if categorias.length > 0}
            <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
                <div class="mb-3 flex items-center justify-between">
                    <p class="text-sm font-semibold text-zinc-900 dark:text-white">Distribución</p>
                    <span class="text-[10px] font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500 capitalize">
                        {mesLabel}
                    </span>
                </div>
                <div class="mx-auto w-full max-w-[180px]">
                    <canvas bind:this={doughnutCanvas}></canvas>
                </div>
            </div>
        {/if}

        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <!-- TABLA DE VENCIMIENTOS PENDIENTES                                      -->
        <!-- ══════════════════════════════════════════════════════════════════════ -->
        <div class="rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-700 dark:bg-zinc-900">

            <!-- Header -->
            <div class="flex items-center justify-between border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
                <p class="text-sm font-semibold text-zinc-900 dark:text-white">Vencimientos pendientes</p>
                {#if pendientes.length > 0}
                    <span class="rounded-full bg-zinc-100 px-2.5 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                        {pendientes.length} pendiente{pendientes.length > 1 ? 's' : ''}
                    </span>
                {/if}
            </div>

            <!-- Cabecera de columnas -->
            <div class="grid grid-cols-3 border-b border-zinc-100 px-4 py-2 dark:border-zinc-800">
                <p class="col-span-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Concepto</p>
                <p class="col-span-1 text-center text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Próx. pago</p>
                <p class="col-span-1 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">Monto</p>
            </div>

            <!-- Filas -->
            <div class="max-h-64 overflow-y-auto scrollbar-thin">
                {#each pendientes as item (item.id)}
                    {@const critico = esCritico(item.vencimiento)}
                    <div
                        class="grid grid-cols-3 items-center px-4 py-3 transition-colors
                               {critico ? 'bg-red-50 dark:bg-red-950/20' : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50'}"
                    >
                        <!-- Nombre + categoría -->
                        <div class="col-span-1 flex items-center gap-2 min-w-0">
                            <span
                                class="size-2 flex-shrink-0 rounded-full"
                                style="background: {colorForCategoria(item.categoria)}"
                            ></span>
                            <div class="min-w-0">
                                <p class="truncate text-sm font-medium text-zinc-900 dark:text-white leading-tight">{item.nombre}</p>
                                <p class="truncate text-[10px] text-zinc-400 dark:text-zinc-500">{toBucket(item.categoria)}</p>
                            </div>
                        </div>

                        <!-- Fecha -->
                        <div class="col-span-1 text-center">
                            {#if item.vencimiento}
                                <p class="text-xs font-medium {critico ? 'text-red-600 dark:text-red-400' : 'text-zinc-600 dark:text-zinc-400'}">
                                    {labelFecha(item.vencimiento)}
                                </p>
                                {#if diasRestantes(item.vencimiento) >= 2}
                                    <p class="text-[10px] text-zinc-400 dark:text-zinc-500">{diasRestantes(item.vencimiento)}d</p>
                                {/if}
                            {:else}
                                <p class="text-xs font-medium text-zinc-400 dark:text-zinc-500 italic">Sin fecha</p>
                            {/if}
                        </div>

                        <!-- Monto -->
                        <p class="col-span-1 text-right font-mono text-sm font-semibold text-zinc-900 dark:text-white">
                            {fmt(item.monto)}
                        </p>
                    </div>

                    <div class="mx-4 h-px bg-zinc-100 last:hidden dark:bg-zinc-800"></div>
                {/each}

                {#if pendientes.length === 0 && !cargando}
                    <p class="py-6 text-center text-sm text-zinc-400 dark:text-zinc-500">¡Todo al día! 🎉</p>
                {:else if pendientes.length === 0 && cargando}
                    <p class="py-6 text-center text-sm text-zinc-400 dark:text-zinc-500">Cargando...</p>
                {/if}
            </div>

            <!-- Footer: total pendiente -->
            {#if pendientes.length > 0}
                <div class="flex items-center justify-between border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
                    <p class="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Total pendiente</p>
                    <p class="font-mono text-sm font-bold text-zinc-900 dark:text-white">
                        {fmt(pendientes.reduce((s: number, v: ItemPendiente) => s + v.monto, 0))}
                    </p>
                </div>
            {/if}

        </div>

    {/if}

</div>

<style>
    .scrollbar-thin::-webkit-scrollbar        { width: 3px; }
    .scrollbar-thin::-webkit-scrollbar-track  { background: transparent; }
    .scrollbar-thin::-webkit-scrollbar-thumb  { background: #d4d4d8; border-radius: 99px; }
    :global(.dark) .scrollbar-thin::-webkit-scrollbar-thumb { background: #52525b; }
</style>