<script lang="ts" module>
    export type ExpenseFormValue = {
        type: string
        category: string
        amount: number
        date: string         // dd/mm
        due_date?: string    // dd/mm
        paid: boolean
        notes?: string
    }

    export type ExpenseFormSeed = Partial<ExpenseFormValue> & { id?: string }

    export const CATEGORIES = [
        { value: 'luz',          label: 'Luz' },
        { value: 'gas',          label: 'Gas' },
        { value: 'agua',         label: 'Agua' },
        { value: 'impuesto',     label: 'Impuestos' },
        { value: 'expensas',     label: 'Expensas' },
        { value: 'telefonia',    label: 'Telefonía / Internet' },
        { value: 'subscription', label: 'Suscripción' },
        { value: 'comida',       label: 'Comida' },
        { value: 'transporte',   label: 'Transporte' },
        { value: 'salud',        label: 'Salud' },
        { value: 'otros',        label: 'Otros' },
    ] as const
</script>

<script lang="ts">
    import { X, Loader2 } from '@lucide/svelte'

    type Mode = 'create' | 'edit'

    let {
        open = $bindable(false),
        mode = 'create' as Mode,
        seed = {} as ExpenseFormSeed,
        onSubmit,
    }: {
        open?: boolean
        mode?: Mode
        seed?: ExpenseFormSeed
        onSubmit: (value: ExpenseFormValue) => Promise<void> | void
    } = $props()

    function todayDDMM() {
        const d = new Date()
        return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
    }

    let type      = $state('')
    let category  = $state('otros')
    let amount    = $state<number | ''>('')
    let date      = $state(todayDDMM())
    let due_date  = $state('')
    let paid      = $state(false)
    let notes     = $state('')
    let submitting = $state(false)
    let errorMsg   = $state('')

    // Reset/preload whenever the modal opens
    $effect(() => {
        if (open) {
            type      = seed.type ?? ''
            category  = seed.category ?? 'otros'
            amount    = (seed.amount as number | undefined) ?? ''
            date      = seed.date ?? todayDDMM()
            due_date  = seed.due_date ?? ''
            paid      = seed.paid ?? false
            notes     = seed.notes ?? ''
            errorMsg  = ''
        }
    })

    function close() {
        if (submitting) return
        open = false
    }

    async function handleSubmit(e: Event) {
        e.preventDefault()
        errorMsg = ''
        if (!type.trim()) {
            errorMsg = 'Indicá una descripción (ej. "Luz - Edesur").'
            return
        }
        const numericAmount = typeof amount === 'number' ? amount : parseFloat(String(amount))
        if (!numericAmount || numericAmount <= 0) {
            errorMsg = 'El monto debe ser mayor a 0.'
            return
        }
        submitting = true
        try {
            await onSubmit({
                type: type.trim(),
                category,
                amount: numericAmount,
                date: date.trim() || todayDDMM(),
                due_date: due_date.trim() || undefined,
                paid,
                notes: notes.trim() || undefined,
            })
            open = false
        } catch (err) {
            errorMsg = err instanceof Error ? err.message : 'No se pudo guardar el gasto.'
        } finally {
            submitting = false
        }
    }
</script>

{#if open}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
        onclick={close}
        role="presentation"
    ></div>

    <!-- Modal -->
    <div
        class="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-lg rounded-t-2xl border border-border bg-card p-5 shadow-lg sm:bottom-auto sm:top-1/2 sm:rounded-2xl sm:-translate-y-1/2"
        role="dialog"
        aria-modal="true"
        aria-labelledby="expense-form-title"
    >
        <div class="mb-4 flex items-start justify-between">
            <div>
                <h2 id="expense-form-title" class="text-base font-semibold">
                    {mode === 'edit' ? 'Editar gasto' : 'Agregar gasto'}
                </h2>
                <p class="mt-0.5 text-xs text-muted-foreground">
                    {mode === 'edit' ? 'Modificá los datos del gasto.' : 'Cargá un gasto manualmente.'}
                </p>
            </div>
            <button
                type="button"
                onclick={close}
                aria-label="Cerrar"
                class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
                <X class="size-4" />
            </button>
        </div>

        <form onsubmit={handleSubmit} class="flex flex-col gap-3">
            <label class="flex flex-col gap-1">
                <span class="text-xs font-medium text-muted-foreground">Descripción</span>
                <input
                    type="text"
                    bind:value={type}
                    placeholder="Ej. Luz - Edesur"
                    class="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                    required
                />
            </label>

            <div class="grid grid-cols-2 gap-3">
                <label class="flex flex-col gap-1">
                    <span class="text-xs font-medium text-muted-foreground">Monto (ARS)</span>
                    <input
                        type="number"
                        step="0.01"
                        min="0"
                        bind:value={amount}
                        placeholder="0"
                        class="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                        required
                    />
                </label>

                <label class="flex flex-col gap-1">
                    <span class="text-xs font-medium text-muted-foreground">Categoría</span>
                    <select
                        bind:value={category}
                        class="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                    >
                        {#each CATEGORIES as opt}
                            <option value={opt.value}>{opt.label}</option>
                        {/each}
                    </select>
                </label>
            </div>

            <div class="grid grid-cols-2 gap-3">
                <label class="flex flex-col gap-1">
                    <span class="text-xs font-medium text-muted-foreground">Fecha (dd/mm)</span>
                    <input
                        type="text"
                        bind:value={date}
                        placeholder="dd/mm"
                        pattern="[0-9]{2}/[0-9]{2}"
                        class="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                    />
                </label>

                <label class="flex flex-col gap-1">
                    <span class="text-xs font-medium text-muted-foreground">Vencimiento (dd/mm)</span>
                    <input
                        type="text"
                        bind:value={due_date}
                        placeholder="opcional"
                        pattern="[0-9]{2}/[0-9]{2}"
                        class="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                    />
                </label>
            </div>

            <label class="flex flex-col gap-1">
                <span class="text-xs font-medium text-muted-foreground">Notas (opcional)</span>
                <textarea
                    bind:value={notes}
                    rows={2}
                    placeholder="Detalles adicionales..."
                    class="resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/40"
                ></textarea>
            </label>

            <label class="flex items-center gap-2 rounded-md border border-border bg-secondary/50 px-3 py-2">
                <input type="checkbox" bind:checked={paid} class="size-4" />
                <span class="text-sm">Ya pagado</span>
            </label>

            {#if errorMsg}
                <p class="text-xs text-destructive">{errorMsg}</p>
            {/if}

            <div class="mt-2 flex gap-2">
                <button
                    type="button"
                    onclick={close}
                    disabled={submitting}
                    class="flex-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
                >
                    Cancelar
                </button>
                <button
                    type="submit"
                    disabled={submitting}
                    class="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 active:scale-95 disabled:opacity-50 disabled:active:scale-100"
                >
                    {#if submitting}
                        <Loader2 class="size-4 animate-spin" />
                    {/if}
                    {mode === 'edit' ? 'Guardar' : 'Agregar'}
                </button>
            </div>
        </form>
    </div>
{/if}
