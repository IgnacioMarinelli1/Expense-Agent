<script lang="ts">
    const resumen = [
        { label: 'Gastado',   valor: '$27.700' },
        { label: 'Pendiente', valor: '$45.200' },
        { label: 'Pagos',     valor: '2 / 5'  },
    ]
</script>

<div style="
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
">
    <h1 style="font-size: 1.1rem; font-weight: 600; margin: 0;">Resumen Mayo 2026</h1>

    <!-- Tarjetas -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;">
        {#each resumen as item}
            <div style="
        border-radius: 0.75rem;
        padding: 0.875rem;
        border: 1px solid var(--border);
        background: var(--card);
      ">
                <p style="font-size: 0.7rem; color: var(--muted-foreground); margin: 0 0 0.25rem;">{item.label}</p>
                <p style="font-weight: 600; font-size: 0.875rem; margin: 0;">{item.valor}</p>
            </div>
        {/each}
    </div>

    <!-- Placeholder gráfico -->
    <div style="
    border-radius: 0.75rem;
    border: 1px solid var(--border);
    background: var(--card);
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 0.5rem;
  ">
        <span style="font-size: 2rem;">📊</span>
        <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 0;">Gráfico por categoría</p>
        <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0;">Disponible en Sprint 3</p>
    </div>

    <div style="
    border-radius: 0.75rem;
    border: 1px solid var(--border);
    background: var(--card);
    height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 0.5rem;
  ">
        <span style="font-size: 2rem;">📅</span>
        <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 0;">Calendario de vencimientos</p>
        <p style="font-size: 0.75rem; color: var(--muted-foreground); margin: 0;">Disponible en Sprint 3</p>
    </div>
</div>