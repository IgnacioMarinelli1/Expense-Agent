<script lang="ts">
    // Placeholder — los gráficos reales van en Sprint 3
    const resumen = [
        { label: 'Gastado',   valor: '$73.400', color: 'var(--primary)'    },
        { label: 'Pendiente', valor: '$45.200', color: 'var(--cat-luz)'    },
        { label: 'Este mes',  valor: '5 pagos', color: 'var(--cat-expensas)'},
    ]
</script>

<div class="p-4 flex flex-col gap-4 overflow-y-auto" style="max-height: calc(100vh - 120px)">

    <h1 class="text-lg font-semibold">Resumen Mayo 2026</h1>

    <!-- Tarjetas de resumen -->
    <div class="grid grid-cols-3 gap-3">
        {#each resumen as item}
            <div class="rounded-xl p-3 flex flex-col gap-1 border"
                 style="background: hsl(var(--card))">
                <p class="text-xs" style="color: hsl(var(--muted-foreground))">{item.label}</p>
                <p class="font-semibold text-sm">{item.valor}</p>
            </div>
        {/each}
    </div>

    <!-- Placeholder del gráfico -->
    <div class="rounded-xl border flex items-center justify-center"
         style="background: hsl(var(--card)); height: 200px">
        <div class="text-center" style="color: hsl(var(--muted-foreground))">
            <p class="text-3xl mb-2">📊</p>
            <p class="text-sm">Gráfico por categoría</p>
            <p class="text-xs">Sprint 3</p>
        </div>
    </div>

    <div class="rounded-xl border flex items-center justify-center"
         style="background: hsl(var(--card)); height: 160px">
        <div class="text-center" style="color: hsl(var(--muted-foreground))">
            <p class="text-3xl mb-2">📅</p>
            <p class="text-sm">Calendario de vencimientos</p>
            <p class="text-xs">Sprint 3</p>
        </div>
    </div>

</div>