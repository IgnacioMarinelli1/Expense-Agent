<script lang="ts">
    import { onMount } from 'svelte'
    import { api } from '$lib/api/client'
    import { Receipt, Clock, ListChecks, PieChart, CalendarDays } from '@lucide/svelte'

    let total = $state(0)
    let paid = $state(0)
    let pending = $state(0)
    let payments_count = $state(0)
    let pending_count = $state(0)
    let loading = $state(true)
    let error = $state('')

    const currentMonth = new Date().toISOString().slice(0, 7) // YYYY-MM
    const monthLabel = new Date().toLocaleString('es-AR', { month: 'long', year: 'numeric' })

    onMount(async () => {
        try {
            const res = await api.getSummary(currentMonth)
            total = res.total
            paid = res.paid
            pending = res.pending
            payments_count = res.payments_count
            pending_count = res.pending_count
        } catch (e) {
            error = 'No se pudo cargar el resumen.'
        } finally {
            loading = false
        }
    })

    function fmt(n: number) {
        return '$' + n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    }
</script>

<div class="flex max-h-[calc(100vh-120px)] flex-col gap-4 overflow-y-auto p-4">
    <h1 class="text-lg font-semibold capitalize">
        Resumen {monthLabel}
    </h1>

    {#if loading}
        <div class="py-8 text-center text-sm text-muted-foreground">
            Cargando resumen...
        </div>
    {:else if error}
        <div class="py-8 text-center text-sm text-destructive">
            {error}
        </div>
    {:else}
        <!-- Tarjetas -->
        <div class="grid grid-cols-3 gap-3">
            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-muted-foreground">
                    <Receipt class="size-3.5" />
                    <p class="text-[0.7rem]">Gastado</p>
                </div>
                <p class="text-sm font-semibold">{fmt(paid)}</p>
            </div>
            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-muted-foreground">
                    <Clock class="size-3.5" />
                    <p class="text-[0.7rem]">Pendiente</p>
                </div>
                <p class="text-sm font-semibold">{fmt(pending)}</p>
            </div>
            <div class="rounded-xl border border-border bg-card p-3.5 shadow-sm transition-colors hover:border-foreground/20">
                <div class="mb-1 flex items-center gap-1 text-muted-foreground">
                    <ListChecks class="size-3.5" />
                    <p class="text-[0.7rem]">Pagos</p>
                </div>
                <p class="text-sm font-semibold">{payments_count} / {payments_count + pending_count}</p>
            </div>
        </div>

        <!-- Total -->
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
                        {total > 0 ? Math.round(paid / total * 100) : 0}%
                    </p>
                </div>
            </div>
        {/if}
    {/if}

    <!-- Placeholders Sprint 3 -->
    <div
        class="flex h-[200px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card text-muted-foreground"
    >
        <PieChart class="size-8" />
        <p class="text-sm">Gráfico por categoría</p>
        <p class="text-xs">Disponible en Sprint 3</p>
    </div>

    <div
        class="flex h-[160px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-card text-muted-foreground"
    >
        <CalendarDays class="size-8" />
        <p class="text-sm">Calendario de vencimientos</p>
        <p class="text-xs">Disponible en Sprint 3</p>
    </div>
</div>
