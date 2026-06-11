<script lang="ts">
    import { onMount } from 'svelte'
    import { appState, invalidar } from '$lib/stores/appState.svelte'
    import { formatAmount, formatArs, toArs } from '$lib/stores/currency.svelte'
    import { api } from '$lib/api/client'
    import { Check, CheckCircle2, Plus } from '@lucide/svelte'
    import ExpenseForm, { type ExpenseFormSeed, type ExpenseFormValue } from '$lib/components/ExpenseForm.svelte'
    import ExpenseRowMenu from '$lib/components/ExpenseRowMenu.svelte'

    const mesActual = new Date().toISOString().slice(0, 7)

    const colors: Record<string, string> = {
        luz: 'var(--cat-luz)',
        gas: 'var(--cat-gas)',
        agua: 'var(--cat-agua)',
        impuesto: 'var(--cat-impuesto)',
        expensas: 'var(--cat-expensas)',
        telefonia: 'var(--cat-telefonia)',
        subscription: 'var(--cat-subscription)',
        comida: 'var(--cat-comida)',
        transporte: 'var(--cat-transporte)',
        salud: 'var(--cat-salud)',
        otros: 'var(--cat-otros)',
    }

    let formOpen = $state(false)
    let formMode = $state<'create' | 'edit'>('create')
    let formSeed = $state<ExpenseFormSeed>({})
    let editingId = $state<string | null>(null)

    onMount(() => {
        if (appState.gastos.length === 0) {
            invalidar(mesActual)
        }
    })

    async function marcarPagado(id: string) {
        await api.markPaid(id)
    }

    function openCreate() {
        formMode = 'create'
        formSeed = {}
        editingId = null
        formOpen = true
    }

    function openEdit(gasto: typeof appState.gastos[number]) {
        formMode = 'edit'
        editingId = gasto.id
        formSeed = {
            type: gasto.tipo,
            category: gasto.categoria,
            amount: gasto.monto,
            date: gasto.fecha,
            due_date: gasto.vencimiento,
            paid: gasto.pagado,
            notes: gasto.notas,
        }
        formOpen = true
    }

    async function handleSubmit(value: ExpenseFormValue) {
        if (formMode === 'edit' && editingId) {
            await api.updateExpense(editingId, {
                type: value.type,
                category: value.category,
                amount: value.amount,
                date: value.date,
                due_date: value.due_date ?? null,
                paid: value.paid,
                notes: value.notes ?? null,
            })
        } else {
            await api.createExpense({
                type: value.type,
                category: value.category,
                amount: value.amount,
                date: value.date,
                due_date: value.due_date,
                paid: value.paid,
                notes: value.notes,
            })
        }
    }

    async function handleDelete(gasto: typeof appState.gastos[number]) {
        const ok = window.confirm(`Eliminar "${gasto.tipo}"? Esta accion no se puede deshacer.`)
        if (!ok) return
        await api.deleteExpense(gasto.id)
    }

    const LIMITE = 10
    let showAll = $state(false)

    const gastos = $derived(appState.gastos)
    const cargando = $derived(appState.cargando)
    const error = $derived(appState.error)
    const pendientes = $derived(gastos.filter((g) => !g.pagado))
    const pagados = $derived(gastos.filter((g) => g.pagado))
    // Pendientes primero, luego pagados — mostrar hasta LIMITE total
    const todosOrdenados = $derived([...pendientes, ...pagados])
    const mostrados = $derived(showAll ? todosOrdenados : todosOrdenados.slice(0, LIMITE))
    const pendientesMostrados = $derived(mostrados.filter((g) => !g.pagado))
    const pagadosMostrados = $derived(mostrados.filter((g) => g.pagado))
    const hayMas = $derived(!showAll && todosOrdenados.length > LIMITE)
    // Sumamos en ARS base (cada gasto puede estar en otra moneda) y formateamos en la de visualizacion.
    const totalMesArs = $derived(gastos.reduce((acc: number, g) => acc + toArs(g.monto, g.moneda), 0))
</script>

<div class="relative flex h-full flex-col gap-4 overflow-y-auto p-4 pb-24">
    {#if cargando && gastos.length === 0}
        <div class="py-8 text-center text-sm text-muted-foreground">
            Cargando gastos...
        </div>
    {:else if error && gastos.length === 0}
        <div class="py-8 text-center text-sm text-destructive">
            {error}
        </div>
    {:else}
        <div class="flex items-center justify-between rounded-2xl bg-primary px-5 py-5 text-primary-foreground shadow-sm">
            <div>
                <p class="mb-1 text-xs opacity-80">Total del mes</p>
                <p class="text-2xl font-semibold">
                    {formatArs(totalMesArs)}
                </p>
            </div>
            <div class="text-right">
                <p class="mb-1 text-xs opacity-80">Pendientes</p>
                <p class="text-2xl font-semibold">{pendientes.length}</p>
            </div>
        </div>

        {#if pendientesMostrados.length > 0}
            <section>
                <h2 class="mb-2 text-xs font-medium text-muted-foreground">
                    Pendientes
                </h2>
                <div class="flex flex-col gap-2">
                    {#each pendientesMostrados as gasto (gasto.id)}
                        <div class="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 shadow-sm transition-colors hover:border-foreground/20">
                            <div class="flex min-w-0 items-center gap-3">
                                <div
                                    class="h-10 w-1 shrink-0 rounded-full"
                                    style="background: {colors[gasto.categoria] ?? colors.otros};"
                                ></div>
                                <div class="min-w-0">
                                    <p class="truncate text-sm font-medium">{gasto.tipo}</p>
                                    <p class="mt-0.5 text-xs text-muted-foreground">
                                        {#if gasto.vencimiento}
                                            Vence {gasto.vencimiento}
                                        {:else}
                                            Sin fecha de vencimiento
                                        {/if}
                                    </p>
                                </div>
                            </div>
                            <div class="flex shrink-0 items-center gap-2">
                                <p class="font-semibold">{formatAmount(gasto.monto, gasto.moneda)}</p>
                                <button
                                    type="button"
                                    onclick={() => marcarPagado(gasto.id)}
                                    class="inline-flex items-center gap-1 rounded-md border border-border bg-transparent px-2.5 py-1.5 text-xs font-medium text-foreground transition-all hover:bg-muted active:scale-95"
                                >
                                    <Check class="size-3.5" /> Pagar
                                </button>
                                <ExpenseRowMenu
                                    onEdit={() => openEdit(gasto)}
                                    onDelete={() => handleDelete(gasto)}
                                />
                            </div>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        {#if pagadosMostrados.length > 0}
            <section>
                <h2 class="mb-2 text-xs font-medium text-muted-foreground">
                    Pagados este mes
                </h2>
                <div class="flex flex-col gap-2">
                    {#each pagadosMostrados as gasto (gasto.id)}
                        <div class="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 opacity-60 shadow-sm transition-opacity hover:opacity-100">
                            <div class="flex min-w-0 items-center gap-3">
                                <div
                                    class="h-10 w-1 shrink-0 rounded-full"
                                    style="background: {colors[gasto.categoria] ?? colors.otros};"
                                ></div>
                                <div class="min-w-0">
                                    <p class="truncate text-sm font-medium">{gasto.tipo}</p>
                                    <p class="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                                        Pagado {gasto.fecha} <CheckCircle2 class="size-3" />
                                    </p>
                                </div>
                            </div>
                            <div class="flex shrink-0 items-center gap-2">
                                <p class="font-semibold">{formatAmount(gasto.monto, gasto.moneda)}</p>
                                <ExpenseRowMenu
                                    onEdit={() => openEdit(gasto)}
                                    onDelete={() => handleDelete(gasto)}
                                />
                            </div>
                        </div>
                    {/each}
                </div>
            </section>
        {/if}

        {#if hayMas}
            <button
                type="button"
                onclick={() => showAll = true}
                class="w-full rounded-xl border border-border bg-card py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
                Ver los {todosOrdenados.length - LIMITE} restantes
            </button>
        {/if}

        {#if gastos.length === 0}
            <div class="flex flex-col items-center gap-3 py-12 text-center text-sm text-muted-foreground">
                <p>No hay gastos registrados.</p>
                <button
                    type="button"
                    onclick={openCreate}
                    class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 active:scale-95"
                >
                    <Plus class="size-4" /> Agregar primer gasto
                </button>
                <p class="text-xs">O usa el chat para cargar uno con lenguaje natural.</p>
            </div>
        {/if}
    {/if}
</div>


<ExpenseForm
    bind:open={formOpen}
    mode={formMode}
    seed={formSeed}
    onSubmit={handleSubmit}
/>
