<!--
  Root Layout - Premium SaaS Design (2026)

  Features:
  - Collapsible sidebar navigation
  - Clean header with user menu
  - Motion-enhanced page transitions
  - Responsive design
-->

<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import '../app.css';
	import { createSupabaseBrowserClient } from '$lib/supabase';
	import { invalidate } from '$app/navigation';
	import { page } from '$app/stores';
	import { tick } from 'svelte';
	import { uiState } from '$lib/stores/ui.svelte';
	import ToastComponent from '$lib/components/Toast.svelte';
	import { base } from '$app/paths';
	import { browser } from '$app/environment';
	import { jobStore } from '$lib/stores/jobs.svelte';
	import { allowedNavHrefs, isAdminRole, normalizePersona } from '$lib/persona';
	import {
		getFocusableElements,
		lockBodyScroll,
		resolveNextFocusTarget
	} from '$lib/landing/publicMenuA11y';
	import AppAuthenticatedShell from './layout/AppAuthenticatedShell.svelte';
	import PublicSiteShell from './layout/PublicSiteShell.svelte';

	let { data, children } = $props();

	$effect(() => {
		if (!browser) return;
		const handleKeydown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
				e.preventDefault();
				uiState.isCommandPaletteOpen = !uiState.isCommandPaletteOpen;
			}
		};
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});

	const currentYear = new Date().getFullYear();

	type NavItem = { href: string; label: string; icon: string };

	const allNavItems: NavItem[] = [
		{ href: '/', label: 'Dashboard', icon: '📊' },
		{ href: '/ops', label: 'Ops Center', icon: '🛠️' },
		{ href: '/onboarding', label: 'Onboarding', icon: '🧭' },
		{ href: '/roi-planner', label: 'ROI Planner', icon: '📈' },
		{ href: '/audit', label: 'Audit Logs', icon: '🧾' },
		{ href: '/connections', label: 'Connections', icon: '☁️' },
		{ href: '/greenops', label: 'GreenOps', icon: '🌱' },
		{ href: '/llm', label: 'LLM Usage', icon: '🤖' },
		{ href: '/billing', label: 'Billing', icon: '💳' },
		{ href: '/leaderboards', label: 'Leaderboards', icon: '🏆' },
		{ href: '/savings', label: 'Savings Proof', icon: '💰' },
		{ href: '/settings', label: 'Settings', icon: '⚙️' },
		{ href: '/admin/health', label: 'Admin Health', icon: '🩺' }
	];

	const NAV_SHOW_ALL_KEY = 'valdrics.nav.show_all.v1';
	let showAllNav = $state(false);
	let navPreferenceLoaded = $state(false);
	let prefersReducedMotion = $state(false);
	let publicMenuOpen = $state(false);
	let publicMenuPanel = $state<HTMLDivElement | null>(null);
	let publicMenuButton = $state<HTMLButtonElement | null>(null);
	let publicMenuRestoreFocus = $state<HTMLElement | null>(null);
	let publicResourcesMenuOpen = $state(false);
	let publicResourcesPanel = $state<HTMLDivElement | null>(null);
	let publicResourcesButton = $state<HTMLButtonElement | null>(null);

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

	let persona = $derived(normalizePersona(data.profile?.persona));
	let role = $derived(String(data.profile?.role ?? 'member'));

	$effect(() => {
		if (!browser) return;
		if (navPreferenceLoaded) return;
		const raw = window.localStorage.getItem(NAV_SHOW_ALL_KEY);
		if (raw === null) {
			showAllNav = false;
		} else {
			showAllNav = raw === '1' || raw.toLowerCase() === 'true';
		}
		navPreferenceLoaded = true;
	});

	$effect(() => {
		if (!browser) return;
		if (!navPreferenceLoaded) return;
		window.localStorage.setItem(NAV_SHOW_ALL_KEY, showAllNav ? '1' : '0');
	});

	let visibleNavItems = $derived(
		(() => {
			if (isAdminRole(role)) return allNavItems;
			return allNavItems.filter((item) => item.href !== '/admin/health');
		})()
	);
	let allowlist = $derived(allowedNavHrefs(persona, role));
	let primaryNavItems = $derived(visibleNavItems.filter((item) => allowlist.has(item.href)));
	let secondaryNavItems = $derived(visibleNavItems.filter((item) => !allowlist.has(item.href)));
	let activeSecondaryNavItems = $derived(secondaryNavItems.filter((item) => isActive(item.href)));

	function toAppPath(path: string): string {
		const normalizedPath = path.startsWith('/') ? path : `/${path}`;
		const normalizedBase = base === '/' ? '' : base;
		return `${normalizedBase}${normalizedPath}`;
	}

	let canonicalHref = $derived(new URL($page.url.pathname, $page.url.origin).toString());
	let shouldNoIndex = $derived(
		!!data.user ||
			$page.url.pathname === toAppPath('/auth') ||
			$page.url.pathname.startsWith(`${toAppPath('/auth')}/`)
	);

	function isActive(href: string): boolean {
		const resolvedHref = toAppPath(href);
		if (resolvedHref === toAppPath('/')) {
			return $page.url.pathname === (base || '/');
		}
		return $page.url.pathname.startsWith(resolvedHref);
	}

	$effect(() => {
		if (!browser || !data.user) return;
		const supabase = createSupabaseBrowserClient();
		const {
			data: { subscription }
		} = supabase.auth.onAuthStateChange((event) => {
			if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
				invalidate('supabase:auth');
			}
		});
		return () => subscription.unsubscribe();
	});

	$effect(() => {
		if (browser && data.user) {
			jobStore.init();
		} else if (browser && !data.user) {
			jobStore.disconnect();
		}
	});

	$effect(() => {
		$page.url.pathname;
		publicMenuOpen = false;
		publicResourcesMenuOpen = false;
	});

	$effect(() => {
		if (!browser || !publicMenuOpen) return;

		publicMenuRestoreFocus =
			document.activeElement instanceof HTMLElement ? document.activeElement : null;
		const unlockBodyScroll = lockBodyScroll(document);

		void tick().then(() => {
			const firstFocusable = getFocusableElements(publicMenuPanel)[0];
			firstFocusable?.focus();
		});

		const handleKeydown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				event.preventDefault();
				publicMenuOpen = false;
				return;
			}
			if (event.key !== 'Tab') return;
			const direction = event.shiftKey ? 'backward' : 'forward';
			const activeElement =
				document.activeElement instanceof HTMLElement ? document.activeElement : null;
			const nextTarget = resolveNextFocusTarget(publicMenuPanel, activeElement, direction);
			if (!nextTarget) return;
			event.preventDefault();
			nextTarget.focus();
		};
		const initialScrollY = window.scrollY;
		const handleScroll = () => {
			if (Math.abs(window.scrollY - initialScrollY) > 48) {
				publicMenuOpen = false;
			}
		};
		window.addEventListener('keydown', handleKeydown);
		window.addEventListener('scroll', handleScroll, { passive: true });

		return () => {
			window.removeEventListener('keydown', handleKeydown);
			window.removeEventListener('scroll', handleScroll);
			unlockBodyScroll();
			if (publicMenuRestoreFocus) {
				publicMenuRestoreFocus.focus();
			} else {
				publicMenuButton?.focus();
			}
			publicMenuRestoreFocus = null;
		};
	});

	$effect(() => {
		if (!browser || !publicResourcesMenuOpen) return;

		const handlePointerDown = (event: PointerEvent) => {
			const target = event.target;
			if (!(target instanceof Node)) return;
			if (publicResourcesPanel?.contains(target)) return;
			if (publicResourcesButton?.contains(target)) return;
			publicResourcesMenuOpen = false;
		};

		const handleKeydown = (event: KeyboardEvent) => {
			if (event.key !== 'Escape') return;
			event.preventDefault();
			publicResourcesMenuOpen = false;
			publicResourcesButton?.focus();
		};

		document.addEventListener('pointerdown', handlePointerDown);
		window.addEventListener('keydown', handleKeydown);
		return () => {
			document.removeEventListener('pointerdown', handlePointerDown);
			window.removeEventListener('keydown', handleKeydown);
		};
	});

	function togglePublicMenu(): void {
		publicMenuOpen = !publicMenuOpen;
	}

	function closePublicMenu(): void {
		publicMenuOpen = false;
	}

	function togglePublicResourcesMenu(): void {
		publicResourcesMenuOpen = !publicResourcesMenuOpen;
	}

	function closePublicResourcesMenu(): void {
		publicResourcesMenuOpen = false;
	}
</script>

<svelte:head>
	<link rel="canonical" href={canonicalHref} />
	<meta name="robots" content={shouldNoIndex ? 'noindex,nofollow' : 'index,follow'} />
</svelte:head>

<div class="min-h-screen bg-ink-950 text-ink-100">
	<a href="#main" class="skip-link">Skip to content</a>
	{#if data.user}
		<AppAuthenticatedShell
			user={data.user}
			subscription={data.subscription}
			{primaryNavItems}
			{secondaryNavItems}
			{activeSecondaryNavItems}
			bind:showAllNav
			{persona}
			{prefersReducedMotion}
			{toAppPath}
			{isActive}
		>
			{@render children()}
		</AppAuthenticatedShell>
	{:else}
		<PublicSiteShell
			{currentYear}
			{toAppPath}
			bind:publicMenuOpen
			bind:publicMenuPanel
			bind:publicMenuButton
			bind:publicResourcesMenuOpen
			bind:publicResourcesPanel
			bind:publicResourcesButton
			{togglePublicMenu}
			{closePublicMenu}
			{togglePublicResourcesMenu}
			{closePublicResourcesMenu}
		>
			{@render children()}
		</PublicSiteShell>
	{/if}
</div>

{#if uiState.toasts.length > 0}
	<div
		class="fixed inset-x-0 bottom-4 z-[100] px-4 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:px-0 sm:max-w-md"
	>
		<div class="flex flex-col gap-3 sm:min-w-[320px]">
			{#each uiState.toasts as toast (toast.id)}
				<ToastComponent {toast} />
			{/each}
		</div>
	</div>
{/if}
