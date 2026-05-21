<script lang="ts">
    import '../app.css'
    import { page } from '$app/stores'

    const navItems = [
        { href: '/',          label: 'Chat',      icon: '💬' },
        { href: '/gastos',    label: 'Gastos',    icon: '📋' },
        { href: '/dashboard', label: 'Dashboard', icon: '📊' },
    ]
</script>

<div class="min-h-screen flex flex-col">

    <!-- Header -->
    <header class="border-b px-6 py-4 flex items-center justify-between"
            style="background: hsl(var(--card))">
        <div class="flex items-center gap-2">
            <span class="text-xl">🐑</span>
            <span class="font-semibold text-lg">Al Día</span>
            <span class="text-xs px-2 py-0.5 rounded-full"
                  style="background: hsl(var(--secondary)); color: hsl(var(--muted-foreground))">
        beta
      </span>
        </div>
        <span class="text-sm" style="color: hsl(var(--muted-foreground))">
      Mayo 2026
    </span>
    </header>

    <!-- Contenido principal -->
    <main class="flex-1 overflow-hidden">
        <slot />
    </main>

    <!-- Navegación inferior (mobile-first) -->
    <nav class="border-t flex"
         style="background: hsl(var(--card))">
        {#each navItems as item}
            <a href={item.href}
               class="flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors"
               style="color: {$page.url.pathname === item.href
           ? 'hsl(var(--primary))'
           : 'hsl(var(--muted-foreground))'}">
                <span class="text-lg">{item.icon}</span>
                {item.label}
            </a>
        {/each}
    </nav>

</div>