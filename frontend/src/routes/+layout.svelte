<script lang="ts">
	import '../app.css'
	import { page } from '$app/stores'

	const navItems = [
		{ href: '/',          label: 'Chat',      icon: '💬' },
		{ href: '/gastos',    label: 'Gastos',    icon: '📋' },
		{ href: '/dashboard', label: 'Dashboard', icon: '📊' },
	]
</script>

<div style="min-height: 100vh; display: flex; flex-direction: column;">

	<header style="
    border-bottom: 1px solid var(--border);
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--card);
  ">
		<div style="display: flex; align-items: center; gap: 0.5rem;">
			<span style="font-size: 1.25rem;">💸</span>
			<span style="font-weight: 600; font-size: 1.1rem;">Al Día</span>
			<span style="
        font-size: 0.7rem;
        padding: 0.1rem 0.5rem;
        border-radius: 99px;
        background: var(--secondary);
        color: var(--muted-foreground);
      ">beta</span>
		</div>
		<span style="font-size: 0.8rem; color: var(--muted-foreground);">Mayo 2026</span>
	</header>

	<main style="flex: 1; overflow: hidden;">
		<slot />
	</main>

	<nav style="border-top: 1px solid var(--border); display: flex; background: var(--card);">
		{#each navItems as item}
			{@const activo = $page.url.pathname === item.href}
			<a href={item.href} class="nav-link" class:activo>
				<span style="font-size: 1.2rem;">{item.icon}</span>
				{item.label}
			</a>
		{/each}
	</nav>

</div>

<style>
	.nav-link {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
		padding: 0.75rem 0;
		font-size: 0.75rem;
		text-decoration: none;
		color: var(--muted-foreground);
		font-weight: 400;
	}

	.nav-link.activo {
		color: var(--primary);
		font-weight: 600;
	}
</style>