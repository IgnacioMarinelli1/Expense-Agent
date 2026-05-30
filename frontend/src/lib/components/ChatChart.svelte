<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import type { ChartSpec } from "$lib/stores/expenses";
    import type { ECharts, EChartsOption } from "echarts";

    let { chart }: { chart: ChartSpec } = $props();

    let container: HTMLDivElement;
    let instance: ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;

    function sanitizeOption(value: unknown): unknown {
        if (typeof value === "function") return undefined;
        if (typeof value === "string") {
            const trimmed = value.trim().toLowerCase();
            if (
                trimmed.startsWith("function") ||
                trimmed.startsWith("javascript:") ||
                trimmed.startsWith("data:text/html") ||
                trimmed.startsWith("=>")
            ) {
                return "";
            }
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(sanitizeOption);
        }
        if (value && typeof value === "object") {
            return Object.fromEntries(
                Object.entries(value as Record<string, unknown>)
                    .map(([key, item]) => [key, sanitizeOption(item)])
                    .filter(([, item]) => item !== undefined),
            );
        }
        return value;
    }

    onMount(async () => {
        const echarts = await import("echarts");
        await import("echarts-gl");
        instance = echarts.init(container);
        instance.setOption(sanitizeOption(chart.option) as EChartsOption, true);
        resizeObserver = new ResizeObserver(() => instance?.resize());
        resizeObserver.observe(container);
    });

    $effect(() => {
        if (instance) {
            import("echarts").then((echarts) => {
                instance?.setOption(sanitizeOption(chart.option) as EChartsOption, true);
                instance?.resize();
            });
        }
    });

    onDestroy(() => {
        resizeObserver?.disconnect();
        instance?.dispose();
        instance = null;
    });
</script>

<section class="chart-shell" aria-label={chart.title}>
    <div class="chart-header">
        <div>
            <h3>{chart.title}</h3>
            {#if chart.subtitle}
                <p>{chart.subtitle}</p>
            {/if}
        </div>
        <span>{chart.mode.toUpperCase()}</span>
    </div>
    <div bind:this={container} class="chart-canvas"></div>
    {#if chart.insights?.length}
        <ul class="chart-insights">
            {#each chart.insights as insight}
                <li>{insight}</li>
            {/each}
        </ul>
    {/if}
</section>

<style>
    .chart-shell {
        margin: 0.85rem 0 1.1rem;
        padding: 0.15rem 0 0.35rem;
        border-top: 1px solid color-mix(in srgb, currentColor 10%, transparent);
        border-bottom: 1px solid color-mix(in srgb, currentColor 7%, transparent);
    }

    .chart-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.65rem 0 0.2rem;
    }

    .chart-header h3 {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 650;
        line-height: 1.25;
    }

    .chart-header p {
        margin: 0.2rem 0 0;
        font-size: 0.72rem;
        color: color-mix(in srgb, currentColor 62%, transparent);
    }

    .chart-header span {
        padding: 0.1rem 0;
        font-size: 0.64rem;
        font-weight: 700;
        color: color-mix(in srgb, currentColor 45%, transparent);
    }

    .chart-canvas {
        width: 100%;
        height: clamp(280px, 38vh, 440px);
    }

    .chart-insights {
        margin: 0;
        padding: 0 0 0.45rem 1.1rem;
        color: color-mix(in srgb, currentColor 75%, transparent);
        font-size: 0.78rem;
        line-height: 1.45;
    }

    .chart-insights li + li {
        margin-top: 0.15rem;
    }
</style>
