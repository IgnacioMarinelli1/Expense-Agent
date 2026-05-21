<script lang="ts">
    // Datos de ejemplo — van a venir del backend en Sprint 2
    const gastos = [
        { id: 1, tipo: 'Luz',       monto: 18500, fecha: '15/05', pagado: true,  categoria: 'luz'       },
        { id: 2, tipo: 'Gas',       monto: 9200,  fecha: '20/05', pagado: true,  categoria: 'gas'       },
        { id: 3, tipo: 'ABL',       monto: 5400,  fecha: '30/05', pagado: false, categoria: 'impuesto'  },
        { id: 4, tipo: 'Expensas',  monto: 32000, fecha: '01/06', pagado: false, categoria: 'expensas'  },
        { id: 5, tipo: 'Internet',  monto: 7800,  fecha: '10/06', pagado: false, categoria: 'telefonia' },
    ]

    const colores: Record<string, string> = {
        luz:       'var(--cat-luz)',
        gas:       'var(--cat-gas)',
        agua:      'var(--cat-agua)',
        impuesto:  'var(--cat-impuesto)',
        expensas:  'var(--cat-expensas)',
        telefonia: 'var(--cat-telefonia)',
    }

    $: pendientes = gastos.filter(g => !g.pagado)
    $: pagados    = gastos.filter(g =>  g.pagado)
    $: totalMes   = gastos.reduce((acc, g) => acc + g.monto, 0)
</script>

<div class="p-4 flex flex-col gap-4 overflow-y-auto" style="max-height: calc(100vh - 120px)">

    <!-- Resumen rápido -->
    <div class="rounded-xl p-4 flex justify-between"
         style="background: hsl(var(--primary)); color: hsl(var(--primary-foreground))">
        <div>
            <p class="text-xs opacity-80">Total del mes</p>
            <p class="text-2xl font-semibold">${totalMes.toLocaleString('es-AR')}</p>
        </div>
        <div class="text-right">
            <p class="text-xs opacity-80">Pendientes</p>
            <p class="text-2xl font-semibold">{pendientes.length}</p>
        </div>
    </div>

    <!-- Pendientes -->
    {#if pendientes.length > 0}
        <section>
            <h2 class="text-sm font-medium mb-2" style="color: hsl(var(--muted-foreground))">
                Pendientes
            </h2>
            <div class="flex flex-col gap-2">
                {#each pendientes as gasto}
                    <div class="rounded-xl p-4 flex items-center justify-between border"
                         style="background: hsl(var(--card))">
                        <div class="flex items-center gap-3">
                            <div class="w-2 h-8 rounded-full"
                                 style="background: hsl({colores[gasto.categoria]})">
                            </div>
                            <div>
                                <p class="font-medium text-sm">{gasto.tipo}</p>
                                <p class="text-xs" style="color: hsl(var(--muted-foreground))">
                                    Vence {gasto.fecha}
                                </p>
                            </div>
                        </div>
                        <p class="font-semibold">${gasto.monto.toLocaleString('es-AR')}</p>
                    </div>
                {/each}
            </div>
        </section>
    {/if}

    <!-- Pagados -->
    <section>
        <h2 class="text-sm font-medium mb-2" style="color: hsl(var(--muted-foreground))">
            Pagados este mes
        </h2>
        <div class="flex flex-col gap-2">
            {#each pagados as gasto}
                <div class="rounded-xl p-4 flex items-center justify-between border opacity-60"
                     style="background: hsl(var(--card))">
                    <div class="flex items-center gap-3">
                        <div class="w-2 h-8 rounded-full"
                             style="background: hsl({colores[gasto.categoria]})">
                        </div>
                        <div>
                            <p class="font-medium text-sm">{gasto.tipo}</p>
                            <p class="text-xs" style="color: hsl(var(--muted-foreground))">
                                Pagado {gasto.fecha} ✓
                            </p>
                        </div>
                    </div>
                    <p class="font-semibold">${gasto.monto.toLocaleString('es-AR')}</p>
                </div>
            {/each}
        </div>
    </section>

</div>