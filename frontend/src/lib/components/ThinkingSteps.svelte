<script lang="ts">
    import type { TraceStep } from '$lib/stores/expenses'
    import { Check, Loader, X } from '@lucide/svelte'

    let { traces = [], loading = false }: { traces?: TraceStep[]; loading?: boolean } = $props()

    let collapsed = $state(false)

    $effect(() => {
        if (loading) {
            collapsed = false
        }
    })

    $effect(() => {
        if (!loading && traces.length > 0 && traces.every(t => t.status !== 'running')) {
            const timer = setTimeout(() => { collapsed = true }, 1500)
            return () => clearTimeout(timer)
        }
    })
</script>

{#if traces.length > 0}
    <div class="thinking-wrapper">
        <button
            class="thinking-toggle"
            onclick={() => (collapsed = !collapsed)}
            type="button"
        >
            <span class="toggle-icon">{collapsed ? '▸' : '▾'}</span>
            {#if traces.some(t => t.status === 'running')}
                <span class="toggle-label running">Razonando...</span>
            {:else if traces.some(t => t.status === 'error')}
                <span class="toggle-label error">Error en el análisis</span>
            {:else}
                <span class="toggle-label done">{traces.length} {traces.length === 1 ? 'paso' : 'pasos'} completados</span>
            {/if}
        </button>

        {#if !collapsed}
            <div class="trace-list">
                {#each traces as trace (trace.agent + trace.status)}
                    <div class="trace-row" class:running={trace.status === 'running'} class:done={trace.status === 'done'} class:error={trace.status === 'error'}>
                        <span class="trace-icon">
                            {#if trace.status === 'running'}
                                <Loader class="spin" size={13} />
                            {:else if trace.status === 'done'}
                                <Check size={13} />
                            {:else}
                                <X size={13} />
                            {/if}
                        </span>
                        <span class="trace-label">{trace.label}</span>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
{/if}

<style>
    .thinking-wrapper {
        margin-bottom: 0.6rem;
        border: 1px solid color-mix(in srgb, currentColor 10%, transparent);
        border-radius: 10px;
        overflow: hidden;
        font-size: 0.8rem;
    }

    .thinking-toggle {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        width: 100%;
        padding: 0.45rem 0.75rem;
        background: color-mix(in srgb, currentColor 5%, transparent);
        border: none;
        cursor: pointer;
        text-align: left;
        color: inherit;
    }

    .thinking-toggle:hover {
        background: color-mix(in srgb, currentColor 8%, transparent);
    }

    .toggle-icon {
        font-size: 0.65rem;
        opacity: 0.5;
    }

    .toggle-label {
        font-weight: 500;
        opacity: 0.7;
    }

    .toggle-label.running {
        opacity: 1;
        color: color-mix(in srgb, currentColor 80%, #6366f1);
    }

    .toggle-label.error {
        opacity: 1;
        color: hsl(var(--destructive));
    }

    .trace-list {
        padding: 0.4rem 0.75rem 0.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        border-top: 1px solid color-mix(in srgb, currentColor 8%, transparent);
    }

    .trace-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        opacity: 0.55;
        transition: opacity 0.2s;
    }

    .trace-row.running {
        opacity: 1;
    }

    .trace-row.done {
        opacity: 0.6;
    }

    .trace-row.error {
        opacity: 1;
        color: hsl(var(--destructive));
    }

    .trace-icon {
        display: flex;
        align-items: center;
        flex-shrink: 0;
    }

    .trace-label {
        font-size: 0.78rem;
    }

    :global(.thinking-wrapper .spin) {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
</style>
