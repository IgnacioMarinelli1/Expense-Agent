<script lang="ts">
    import { AlertTriangle, CheckCircle2 } from '@lucide/svelte'
    import type { DashboardAlert } from '$lib/stores/dashboard.svelte'

    let { alerts }: { alerts: DashboardAlert[] } = $props()
</script>

<section class="rounded-lg border border-border bg-card p-4">
    <h2 class="mb-3 text-sm font-semibold">Alertas</h2>
    <div class="flex flex-col gap-2">
        {#if alerts.length}
            {#each alerts as alert}
                <div class="flex items-start gap-2 rounded-md px-3 py-2 text-sm {alert.level === 'danger' ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200' : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200'}">
                    <AlertTriangle class="mt-0.5 size-4 shrink-0" />
                    <span>{alert.message}</span>
                </div>
            {/each}
        {:else}
            <div class="flex items-center gap-2 rounded-md bg-emerald-100 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
                <CheckCircle2 class="size-4" />
                Todo dentro de los limites configurados.
            </div>
        {/if}
    </div>
</section>
