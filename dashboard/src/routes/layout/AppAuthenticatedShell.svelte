<script lang="ts">
	import '../../authenticated.app.css';
	import { browser } from '$app/environment';
	import { invalidate } from '$app/navigation';
	import { base } from '$app/paths';
	import type { Snippet } from 'svelte';
	import { uiState } from '$lib/stores/ui.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import ErrorBoundary from '$lib/components/ErrorBoundary.svelte';

	type NavItem = { href: string; label: string; icon: string };
	type CommandPaletteProps = {
		isOpen?: boolean;
		actions?: NavItem[];
		role?: string;
		platformOperator?: boolean;
	};

	interface Props {
		user: {
			email?: string | null;
		};
		role: string;
		platformOperator: boolean;
		subscription?: {
			tier?: string | null;
		} | null;
		primaryNavItems: NavItem[];
		secondaryNavItems: NavItem[];
		activeSecondaryNavItems: NavItem[];
		persona: string;
		toAppPath: (path: string) => string;
		isActive: (href: string) => boolean;
		children: Snippet;
	}

	let {
		user,
		role,
		platformOperator,
		subscription,
		primaryNavItems,
		secondaryNavItems,
		activeSecondaryNavItems,
		persona,
		toAppPath,
		isActive,
		children
	}: Props = $props();

	const NAV_SHOW_ALL_KEY = 'valdrics.nav.show_all.v1';
	type LiveJobStore = {
		activeJobsCount: number;
		init: () => Promise<void> | void;
		disconnect: () => void;
	};
	let showAllNav = $state(false);
	let navPreferenceLoaded = $state(false);
	let prefersReducedMotion = $state(false);
	let liveJobStore = $state<LiveJobStore | null>(null);
	let activeJobsCount = $derived(liveJobStore?.activeJobsCount ?? 0);
	const loadCommandPalette = createLazyComponent<CommandPaletteProps>(
		() => import('$lib/components/CommandPalette.svelte')
	);

	$effect(() => {
		if (!browser) return;
		const handleKeydown = (event: KeyboardEvent) => {
			if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
				event.preventDefault();
				uiState.isCommandPaletteOpen = !uiState.isCommandPaletteOpen;
			}
		};
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});

	$effect(() => {
		if (!browser || navPreferenceLoaded) return;
		const raw = window.localStorage.getItem(NAV_SHOW_ALL_KEY);
		if (raw === null) {
			showAllNav = false;
		} else {
			showAllNav = raw === '1' || raw.toLowerCase() === 'true';
		}
		navPreferenceLoaded = true;
	});

	$effect(() => {
		if (!browser || !navPreferenceLoaded) return;
		window.localStorage.setItem(NAV_SHOW_ALL_KEY, showAllNav ? '1' : '0');
	});

	$effect(() => {
		if (!browser) return;
		if (typeof window.matchMedia !== 'function') {
			prefersReducedMotion = false;
			return;
		}
		const media = window.matchMedia('(prefers-reduced-motion: reduce)');
		const update = () => {
			prefersReducedMotion = media.matches;
		};
		update();
		if (typeof media.addEventListener === 'function') {
			media.addEventListener('change', update);
			return () => media.removeEventListener('change', update);
		}
		media.addListener(update);
		return () => media.removeListener(update);
	});

	$effect(() => {
		if (!browser) return;
		let cancelled = false;
		let unsubscribe: (() => void) | undefined;

		void import('$lib/supabase.browser').then(({ createSupabaseBrowserClient }) => {
			if (cancelled) return;
			const supabase = createSupabaseBrowserClient();
			const {
				data: { subscription }
			} = supabase.auth.onAuthStateChange((event) => {
				if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
					invalidate('supabase:auth');
				}
			});
			unsubscribe = () => subscription.unsubscribe();
		});

		return () => {
			cancelled = true;
			unsubscribe?.();
		};
	});

	$effect(() => {
		if (!browser) return;
		let cancelled = false;
		let disconnect: (() => void) | undefined;

		void import('$lib/stores/jobs.svelte').then(({ jobStore }) => {
			if (cancelled) {
				jobStore.disconnect();
				return;
			}
			liveJobStore = jobStore;
			disconnect = () => jobStore.disconnect();
			void jobStore.init();
		});

		return () => {
			cancelled = true;
			liveJobStore = null;
			disconnect?.();
		};
	});
</script>

<svelte:head>
	<link rel="stylesheet" href={`${base}/authenticated-shell.css`} />
</svelte:head>

<aside id="sidebar" class="sidebar" class:sidebar-collapsed={!uiState.isSidebarOpen}>
	<div class="flex items-center gap-3 px-5 py-5 border-b border-ink-800">
		<CloudLogo provider="valdrics" size={32} />
		<span class="text-lg font-semibold text-gradient">Valdrics</span>
	</div>

	<nav class="flex-1 py-4 min-h-0 overflow-y-auto">
		{#each primaryNavItems as item (item.href)}
			<a
				href={toAppPath(item.href)}
				class="nav-item"
				class:active={isActive(item.href)}
				aria-current={isActive(item.href) ? 'page' : undefined}
				data-sveltekit-preload-data="hover"
				data-sveltekit-preload-code="hover"
			>
				<span class="text-lg">{item.icon}</span>
				<span>{item.label}</span>
			</a>
		{/each}

		{#if secondaryNavItems.length > 0}
			<div class="px-5 pt-3 pb-2">
				<button
					type="button"
					class="btn btn-ghost w-full justify-start text-xs text-ink-400"
					onclick={() => (showAllNav = !showAllNav)}
					aria-expanded={showAllNav}
					aria-controls="sidebar-more-nav"
					title="Your sidebar is filtered by persona. Toggle to show or hide additional pages."
				>
					<span class="capitalize">
						{showAllNav
							? `Hide extras (back to ${persona} view)`
							: `Show all (${secondaryNavItems.length})`}
					</span>
				</button>
			</div>
			{#if !showAllNav && activeSecondaryNavItems.length > 0}
				<div class="px-5 pb-2">
					<p class="text-xs text-ink-500 mb-2">
						You are viewing a page outside your persona navigation.
					</p>
					{#each activeSecondaryNavItems as item (item.href)}
						<a
							href={toAppPath(item.href)}
							class="nav-item"
							class:active={isActive(item.href)}
							aria-current={isActive(item.href) ? 'page' : undefined}
							data-sveltekit-preload-data="hover"
							data-sveltekit-preload-code="hover"
						>
							<span class="text-lg">{item.icon}</span>
							<span>{item.label}</span>
						</a>
					{/each}
				</div>
			{/if}
			{#if showAllNav}
				<div id="sidebar-more-nav" class="pb-3">
					{#each secondaryNavItems as item (item.href)}
						<a
							href={toAppPath(item.href)}
							class="nav-item"
							class:active={isActive(item.href)}
							aria-current={isActive(item.href) ? 'page' : undefined}
							data-sveltekit-preload-data="hover"
							data-sveltekit-preload-code="hover"
						>
							<span class="text-lg">{item.icon}</span>
							<span>{item.label}</span>
						</a>
					{/each}
				</div>
			{/if}
		{/if}
	</nav>

	<div class="border-t border-ink-800 p-4">
		<div class="flex items-center gap-3 mb-3">
			<div
				class="w-8 h-8 rounded-full bg-accent-500/20 flex items-center justify-center text-accent-400 text-sm font-medium"
			>
				{user.email?.charAt(0).toUpperCase()}
			</div>
			<div class="flex-1 min-w-0">
				<p class="text-sm font-medium truncate">{user.email}</p>
				<p class="text-xs text-ink-500 capitalize">{subscription?.tier || 'Free'} Plan</p>
			</div>
		</div>
		<form method="POST" action={toAppPath('/auth/logout')}>
			<button type="submit" class="btn btn-ghost w-full text-left justify-start">
				<span>↩️</span>
				<span>Sign Out</span>
			</button>
		</form>
	</div>
</aside>

<main id="main" tabindex="-1" class="main-content" class:!ml-0={!uiState.isSidebarOpen}>
	<header class="sticky top-0 z-40 bg-ink-900/80 backdrop-blur border-b border-ink-800">
		<div class="flex items-center justify-between px-6 py-3">
			<button
				type="button"
				class="btn btn-ghost p-2"
				onclick={() => uiState.toggleSidebar()}
				aria-label="Toggle sidebar"
				aria-controls="sidebar"
				aria-expanded={uiState.isSidebarOpen}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<line x1="3" y1="12" x2="21" y2="12"></line>
					<line x1="3" y1="6" x2="21" y2="6"></line>
					<line x1="3" y1="18" x2="21" y2="18"></line>
				</svg>
			</button>

			<div class="flex items-center gap-3">
				<button
					type="button"
					class="hidden md:flex items-center gap-2 text-xs text-ink-500 mr-4 hover:text-ink-300 transition-colors"
					onclick={() => (uiState.isCommandPaletteOpen = true)}
					aria-label="Open command palette"
				>
					<kbd class="px-1.5 py-0.5 rounded border border-ink-700 bg-ink-800">⌘</kbd>
					<kbd class="px-1.5 py-0.5 rounded border border-ink-700 bg-ink-800">K</kbd>
				</button>
				{#if activeJobsCount > 0}
					<div
						class="flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 mr-2"
					>
						<span class="relative flex h-2 w-2">
							<span
								class="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75"
							></span>
							<span class="relative inline-flex rounded-full h-2 w-2 bg-accent-500"></span>
						</span>
						<span class="text-xs font-bold uppercase tracking-wider text-accent-400">
							{activeJobsCount} Active {activeJobsCount === 1 ? 'Job' : 'Jobs'}
						</span>
					</div>
				{/if}
				<span class="badge badge-accent">Beta</span>
			</div>
		</div>
	</header>

	<div class="p-6" class:authenticated-shell-enter={!prefersReducedMotion}>
		<ErrorBoundary>
			{@render children()}
		</ErrorBoundary>
	</div>
</main>

{#if uiState.isCommandPaletteOpen}
	{#await loadCommandPalette() then { default: CommandPalette }}
		<CommandPalette
			actions={[...primaryNavItems, ...secondaryNavItems]}
			{role}
			{platformOperator}
			bind:isOpen={
				() => uiState.isCommandPaletteOpen, (value) => (uiState.isCommandPaletteOpen = value)
			}
		/>
	{/await}
{/if}

<style>
	.authenticated-shell-enter {
		animation: authenticatedShellEnter 400ms var(--ease-out) 200ms both;
	}

	@keyframes authenticatedShellEnter {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
