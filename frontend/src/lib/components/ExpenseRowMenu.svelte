<script lang="ts">
    import { MoreVertical, Pencil, Trash2 } from '@lucide/svelte'

    let {
        onEdit,
        onDelete,
    }: {
        onEdit: () => void
        onDelete: () => void
    } = $props()

    let open = $state(false)
    let menuEl: HTMLDivElement | undefined = $state()

    function toggle(e: MouseEvent) {
        e.stopPropagation()
        open = !open
    }

    function close() {
        open = false
    }

    function handleEdit(e: MouseEvent) {
        e.stopPropagation()
        close()
        onEdit()
    }

    function handleDelete(e: MouseEvent) {
        e.stopPropagation()
        close()
        onDelete()
    }

    // Close on outside click / Escape
    $effect(() => {
        if (!open) return

        function onDocClick(e: MouseEvent) {
            if (menuEl && !menuEl.contains(e.target as Node)) close()
        }
        function onKey(e: KeyboardEvent) {
            if (e.key === 'Escape') close()
        }
        document.addEventListener('click', onDocClick)
        document.addEventListener('keydown', onKey)
        return () => {
            document.removeEventListener('click', onDocClick)
            document.removeEventListener('keydown', onKey)
        }
    })
</script>

<div class="relative" bind:this={menuEl}>
    <button
        type="button"
        onclick={toggle}
        aria-label="Más opciones"
        aria-haspopup="menu"
        aria-expanded={open}
        class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:scale-95"
    >
        <MoreVertical class="size-4" />
    </button>

    {#if open}
        <div
            role="menu"
            class="absolute right-0 top-9 z-30 w-36 overflow-hidden rounded-md border border-border bg-popover py-1 text-popover-foreground shadow-md"
        >
            <button
                type="button"
                role="menuitem"
                onclick={handleEdit}
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-muted"
            >
                <Pencil class="size-3.5" /> Editar
            </button>
            <button
                type="button"
                role="menuitem"
                onclick={handleDelete}
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-destructive transition-colors hover:bg-destructive/10"
            >
                <Trash2 class="size-3.5" /> Eliminar
            </button>
        </div>
    {/if}
</div>
