<script lang="ts">
    const gastos = [
        { id: 1, tipo: 'Luz',      monto: 18500, fecha: '15/05', pagado: true,  categoria: 'luz'       },
        { id: 2, tipo: 'Gas',      monto: 9200,  fecha: '20/05', pagado: true,  categoria: 'gas'       },
        { id: 3, tipo: 'ABL',      monto: 5400,  fecha: '30/05', pagado: false, categoria: 'impuesto'  },
        { id: 4, tipo: 'Expensas', monto: 32000, fecha: '01/06', pagado: false, categoria: 'expensas'  },
        { id: 5, tipo: 'Internet', monto: 7800,  fecha: '10/06', pagado: false, categoria: 'telefonia' },
    ]

    const colores: Record<string, string> = {
        luz:       'var(--cat-luz)',
        gas:       'var(--cat-gas)',
        agua:      'var(--cat-agua)',
        impuesto:  'var(--cat-impuesto)',
        expensas:  'var(--cat-expensas)',
        telefonia: 'var(--cat-telefonia)',
    }

    const pendientes = gastos.filter(g => !g.pagado)
    const pagados    = gastos.filter(g =>  g.pagado)
    const totalMes   = gastos.reduce((acc, g) => acc + g.monto, 0)
</script>

<div style="
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
">
    <!-- Resumen -->
    <div style="
    border-radius: 1rem;
    padding: 1.25rem;
    display: flex;
    justify-content: space-between;
    background: var(--primary);
    color: var(--primary-foreground);
  ">
        <div>
            <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Total del mes</p>
            <p style="font-size: 1.5rem; font-weight: 600; margin: 0;">
                ${totalMes.toLocaleString('es-AR')}
            </p>
        </div>
        <div style="text-align: right;">
            <p style="font-size: 0.75rem; opacity: 0.8; margin: 0 0 0.25rem;">Pendientes</p>
            <p style="font-size: 1.5rem; font-weight: 600; margin: 0;">{pendientes.length}</p>
        </div>
    </div>

    <!-- Pendientes -->
    {#if pendientes.length > 0}
        <section>
            <h2 style="font-size: 0.8rem; color: var(--muted-foreground); margin: 0 0 0.5rem;">
                Pendientes
            </h2>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                {#each pendientes as gasto}
                    <div style="
            border-radius: 0.75rem;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid var(--border);
            background: var(--card);
          ">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <div style="
                width: 4px; height: 2.5rem;
                border-radius: 99px;
                background: {colores[gasto.categoria]};
              "></div>
                            <div>
                                <p style="font-weight: 500; font-size: 0.875rem; margin: 0;">{gasto.tipo}</p>
                                <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0.2rem 0 0;">
                                    Vence {gasto.fecha}
                                </p>
                            </div>
                        </div>
                        <p style="font-weight: 600; margin: 0;">${gasto.monto.toLocaleString('es-AR')}</p>
                    </div>
                {/each}
            </div>
        </section>
    {/if}

    <!-- Pagados -->
    <section>
        <h2 style="font-size: 0.8rem; color: var(--muted-foreground); margin: 0 0 0.5rem;">
            Pagados este mes
        </h2>
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            {#each pagados as gasto}
                <div style="
          border-radius: 0.75rem;
          padding: 1rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border: 1px solid var(--border);
          background: var(--card);
          opacity: 0.6;
        ">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <div style="
              width: 4px; height: 2.5rem;
              border-radius: 99px;
              background: {colores[gasto.categoria]};
            "></div>
                        <div>
                            <p style="font-weight: 500; font-size: 0.875rem; margin: 0;">{gasto.tipo}</p>
                            <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0.2rem 0 0;">
                                Pagado {gasto.fecha} ✓
                            </p>
                        </div>
                    </div>
                    <p style="font-weight: 600; margin: 0;">${gasto.monto.toLocaleString('es-AR')}</p>
                </div>
            {/each}
        </div>
    </section>
</div>