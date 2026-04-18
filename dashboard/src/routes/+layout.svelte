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
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';
	import { uiState } from '$lib/stores/ui.svelte';
	import type { Toast } from '$lib/stores/ui.svelte';
	import { base } from '$app/paths';
	import { canAccessAdminHealth } from '$lib/entitlements';
	import { allowedNavHrefs, normalizePersona } from '$lib/persona';
	import { createLazyComponent } from '$lib/lazyComponent';
	import PublicSiteShell from './layout/PublicSiteShell.svelte';
	import AppAuthenticatedShell from './layout/AppAuthenticatedShell.svelte';

	type ToastComponentProps = { toast: Toast };
	type PublicTone = 'default' | 'landing';
	type NavItem = { href: string; label: string; icon: string };
	type SubscriptionSummary = {
		tier?: string | null;
		status?: string | null;
	} | null;
	const loadToastComponent = createLazyComponent<ToastComponentProps>(
		() => import('$lib/components/Toast.svelte')
	);
	let { data, children } = $props();

	const currentYear = new Date().getFullYear();

	const allNavItems: NavItem[] = [
		{ href: '/dashboard', label: 'Dashboard', icon: '📊' },
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

	let persona = $derived(normalizePersona(data.profile?.persona));
	let role = $derived(String(data.profile?.role ?? 'member'));
	let platformOperator = $derived(Boolean(data.profile?.platform_operator));

	let visibleNavItems = $derived(
		allNavItems.filter((item) => {
			if (item.href !== '/admin/health') return true;
			return canAccessAdminHealth(role, platformOperator);
		})
	);
	let allowlist = $derived(allowedNavHrefs(persona, role, { platformOperator }));
	let primaryNavItems = $derived(visibleNavItems.filter((item) => allowlist.has(item.href)));
	let secondaryNavItems = $derived(visibleNavItems.filter((item) => !allowlist.has(item.href)));
	let activeSecondaryNavItems = $derived(secondaryNavItems.filter((item) => isActive(item.href)));

	function toAppPath(path: string): string {
		const normalizedPath = path.startsWith('/') ? path : `/${path}`;
		const normalizedBase = base === '/' ? '' : base;
		return `${normalizedBase}${normalizedPath}`;
	}

	function resolvePublicTone(pathname: string): PublicTone {
		return pathname === toAppPath('/') ? 'landing' : 'default';
	}

	let publicTone = $derived(resolvePublicTone($page.url.pathname));
	let canonicalHref = $derived(new URL($page.url.pathname, $page.url.origin).toString());
	let shouldNoIndex = $derived(
		!!data.user ||
			$page.url.pathname === toAppPath('/auth') ||
			$page.url.pathname.startsWith(`${toAppPath('/auth')}/`)
	);

	function isActive(href: string): boolean {
		const resolvedHref = toAppPath(href);
		if (resolvedHref === toAppPath('/')) {
			return $page.url.pathname === resolvedHref;
		}
		return $page.url.pathname.startsWith(resolvedHref);
	}
</script>

<svelte:head>
	<link rel="canonical" href={canonicalHref} />
	<meta name="robots" content={shouldNoIndex ? 'noindex,nofollow' : 'index,follow'} />
</svelte:head>

<div class="layout-root">
	<a href="#main" class="skip-link">Skip to content</a>
	<noscript>
		<div class="noscript-banner" data-noscript-banner>
			<div class="noscript-banner__copy">
				<strong>JavaScript is disabled.</strong>
				<span>
					Public pages remain readable, but sign-in, live telemetry, and dashboard actions require
					JavaScript.
				</span>
			</div>
			<nav class="noscript-banner__links" aria-label="No JavaScript fallback links">
				<a href={toAppPath('/pricing')}>Pricing</a>
				<a href={toAppPath('/resources')}>Resources</a>
				<a href={toAppPath('/docs')}>Docs</a>
				<a href={toAppPath('/status')}>Status</a>
			</nav>
		</div>
	</noscript>
	{#if data.user}
		<AppAuthenticatedShell
			user={data.user}
			subscription={data.subscription}
			{primaryNavItems}
			{secondaryNavItems}
			{activeSecondaryNavItems}
			{persona}
			{role}
			{platformOperator}
			{toAppPath}
			{isActive}
		>
			{@render children()}
		</AppAuthenticatedShell>
	{:else}
		<PublicSiteShell {currentYear} {toAppPath} {publicTone}>
			{@render children()}
		</PublicSiteShell>
	{/if}
</div>

{#if uiState.toasts.length > 0}
	<div class="layout-toast-region">
		{#await loadToastComponent() then { default: ToastComponent }}
			<div class="layout-toast-stack">
				{#each uiState.toasts as toast (toast.id)}
					<ToastComponent {toast} />
				{/each}
			</div>
		{/await}
	</div>
{/if}
