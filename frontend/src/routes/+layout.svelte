<script lang="ts">
	import "../app.css";
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import {
		Wallet,
		MessageCircle,
		ReceiptText,
		LayoutDashboard,
		Sun,
		Moon,
	} from "@lucide/svelte";
	import { currency, toggleCurrency, ensureRates } from "$lib/stores/currency.svelte";

	const { children } = $props();

	const usdRateLabel = $derived(
		currency.usdRate ? `1 USD ≈ $${Math.round(currency.usdRate).toLocaleString("es-AR")}` : "Cotización blue",
	);

	const navItems = [
		{ href: "/", label: "Chat", icon: MessageCircle },
		{ href: "/expenses", label: "Expenses", icon: ReceiptText },
		{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
	];

	let activeIndex = $derived(Math.max(0, navItems.findIndex(item => $page.url.pathname === item.href)));
	let dark = $state(false);

	function applyTheme() {
		document.documentElement.classList.toggle("dark", dark);
	}

	function toggleTheme() {
		dark = !dark;
		applyTheme();
		localStorage.setItem("theme", dark ? "dark" : "light");
	}

	const currentMonthLabel = (() => {
		const label = new Date().toLocaleDateString("es-AR", { month: "long", year: "numeric" });
		return label.charAt(0).toUpperCase() + label.slice(1);
	})();

	onMount(() => {
		const stored = localStorage.getItem("theme");
		dark = stored
			? stored === "dark"
			: window.matchMedia("(prefers-color-scheme: dark)").matches;
		applyTheme();
		ensureRates();
	});
</script>

<div
	class="flex min-h-[100dvh] w-full items-center justify-center bg-zinc-900 sm:p-8"
>
	<div
		class="flex h-[100dvh] w-full flex-col overflow-hidden bg-background text-foreground transition-colors duration-300 sm:h-[80vh] sm:max-w-[105rem] sm:rounded-2xl sm:border sm:border-border sm:shadow-[0_0_40px_rgba(0,0,0,0.3)]"
	>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card/80 px-5 py-3 backdrop-blur"
		>
			<div class="flex items-center gap-2">
				<span
					class="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground"
				>
					<Wallet class="size-4" />
				</span>
				<span class="text-base font-semibold tracking-tight"
					>Al Día</span
				>
				<span
					class="rounded-full bg-secondary px-2 py-0.5 text-[0.65rem] font-medium text-muted-foreground"
					>beta</span
				>
			</div>

			<div class="flex items-center gap-3">
				<span class="text-xs text-muted-foreground">{currentMonthLabel}</span>
				<button
					onclick={toggleCurrency}
					aria-label="Cambiar moneda"
					title={usdRateLabel}
					class="flex h-8 items-center gap-1 rounded-md border border-border px-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:scale-95"
				>
					<span class={currency.display === "ARS" ? "text-foreground" : ""}>ARS</span>
					<span class="text-border">/</span>
					<span class={currency.display === "USD" ? "text-foreground" : ""}>USD</span>
				</button>
				<button
					onclick={toggleTheme}
					aria-label="Cambiar tema"
					title="Cambiar tema"
					class="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:scale-95"
				>
					{#if dark}
						<Sun class="size-4" />
					{:else}
						<Moon class="size-4" />
					{/if}
				</button>
			</div>
		</header>

		<main class="flex-1 overflow-hidden">
			{@render children()}
		</main>

		<nav
			class="sticky bottom-0 relative flex border-t border-border bg-card/80 backdrop-blur"
		>
			<div
				class="absolute top-0 h-0.5 transition-all duration-300 ease-in-out"
				style="width: {100 / navItems.length}%; left: {(activeIndex * 100) / navItems.length}%;"
			>
				<div class="mx-4 h-full rounded-full bg-primary"></div>
			</div>

			{#each navItems as item}
				{@const activo = $page.url.pathname === item.href}
				{@const Icon = item.icon}
				<a
					href={item.href}
					class="relative flex flex-1 flex-col items-center gap-1 py-2.5 text-xs font-medium transition-colors {activo
						? 'text-primary'
						: 'text-muted-foreground hover:text-foreground'}"
					aria-current={activo ? "page" : undefined}
				>
					<Icon class="size-5" />
					{item.label}
				</a>
			{/each}
		</nav>
	</div>
</div>