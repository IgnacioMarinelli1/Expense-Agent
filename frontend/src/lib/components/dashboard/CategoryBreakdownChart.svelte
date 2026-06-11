<script lang="ts">
    import { onDestroy, onMount } from 'svelte'
    import { Chart, registerables } from 'chart.js'
    import type { DashboardCategory } from '$lib/stores/dashboard.svelte'

    Chart.register(...registerables)

    let { categories }: { categories: DashboardCategory[] } = $props()
    let canvas = $state<HTMLCanvasElement | undefined>(undefined)
    let chart: Chart | null = null

    const fmt = (value: number) => '$' + value.toLocaleString('es-AR', { maximumFractionDigits: 0 })

    function render() {
        if (!canvas) return
        chart?.destroy()
        chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: categories.map((item) => item.category),
                datasets: [{
                    data: categories.map((item) => item.amount),
                    backgroundColor: categories.map((item) => item.color),
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, usePointStyle: true } },
                    tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${fmt(Number(ctx.raw ?? 0))}` } },
                },
            },
        })
    }

    onMount(render)
    $effect(() => { if (canvas) render() })
    onDestroy(() => chart?.destroy())
</script>

<section class="rounded-lg border border-border bg-card p-4">
    <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Gastos por categoria</h2>
        <span class="text-xs text-muted-foreground">{categories.length} categorias</span>
    </div>
    {#if categories.length}
        <div class="h-[280px]">
            <canvas bind:this={canvas}></canvas>
        </div>
    {:else}
        <p class="py-12 text-center text-sm text-muted-foreground">Sin gastos para mostrar.</p>
    {/if}
</section>
