<script lang="ts">
    import { onDestroy, onMount } from 'svelte'
    import { Chart, registerables } from 'chart.js'
    import type { DashboardEvolutionPoint } from '$lib/stores/dashboard.svelte'
    import { formatArs, currency } from '$lib/stores/currency.svelte'

    Chart.register(...registerables)

    let { evolution }: { evolution: DashboardEvolutionPoint[] } = $props()
    let canvas = $state<HTMLCanvasElement | undefined>(undefined)
    let chart: Chart | null = null

    function dayLabel(value: string) {
        return value.slice(8, 10)
    }

    function render() {
        if (!canvas) return
        chart?.destroy()
        chart = new Chart(canvas, {
            data: {
                labels: evolution.map((item) => dayLabel(item.date)),
                datasets: [
                    {
                        type: 'bar',
                        label: 'Gasto diario',
                        data: evolution.map((item) => item.amount),
                        backgroundColor: 'rgba(59, 130, 246, 0.55)',
                        borderRadius: 5,
                    },
                    {
                        type: 'line',
                        label: 'Acumulado',
                        data: evolution.map((item) => item.cumulative),
                        borderColor: '#22c55e',
                        backgroundColor: 'rgba(34, 197, 94, 0.12)',
                        tension: 0.35,
                        pointRadius: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { callback: (value) => formatArs(Number(value)) } },
                },
            },
        })
    }

    onMount(render)
    // Re-render al cambiar datos o la moneda de visualizacion.
    $effect(() => { evolution; currency.display; currency.rates; if (canvas) render() })
    onDestroy(() => chart?.destroy())
</script>

<section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Evolucion de gastos</h2>
        <span class="text-xs text-muted-foreground">Diario + acumulado</span>
    </div>
    {#if evolution.length}
        <div class="h-[280px]">
            <canvas bind:this={canvas}></canvas>
        </div>
    {:else}
        <p class="py-12 text-center text-sm text-muted-foreground">Sin movimientos en el periodo.</p>
    {/if}
</section>
