<script lang="ts">
	import '../../public.app.css';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';
	import { tick } from 'svelte';
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import {
		getFocusableElements,
		lockBodyScroll,
		resolveNextFocusTarget
	} from '$lib/landing/publicMenuA11y';
	import {
		PUBLIC_CONTACT_CHANNELS,
		PUBLIC_FOOTER_BADGES,
		PUBLIC_FOOTER_CAPTION,
		PUBLIC_FOOTER_LINKS,
		PUBLIC_FOOTER_SUBTITLE,
		PUBLIC_MOBILE_LINKS,
		PUBLIC_PRIMARY_LINKS,
		PUBLIC_RESOURCES_DROPDOWN_LINKS
	} from '$lib/landing/publicNav';
	import {
		persistPublicTheme,
		resolveInitialPublicTheme,
		togglePublicTheme as nextPublicTheme,
		type PublicTheme
	} from '$lib/public/publicTheme';

	type PublicTone = 'default' | 'landing';

	interface Props {
		currentYear: number;
		toAppPath: (path: string) => string;
		publicTone: PublicTone;
		children: Snippet;
	}

	let { currentYear, toAppPath, publicTone, children }: Props = $props();

	let publicMenuOpen = $state(false);
	let publicMenuPanel = $state<HTMLDivElement | null>(null);
	let publicMenuButton = $state<HTMLButtonElement | null>(null);
	let publicMenuRestoreFocus = $state<HTMLElement | null>(null);
	let publicResourcesMenuOpen = $state(false);
	let publicResourcesPanel = $state<HTMLDivElement | null>(null);
	let publicResourcesButton = $state<HTMLButtonElement | null>(null);
	let publicTheme = $state<PublicTheme>('light');
	let publicThemeLoaded = $state(false);

	const themeToggleLabel = (theme: PublicTheme) =>
		theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
	const themeToggleCopy = (theme: PublicTheme) => (theme === 'dark' ? 'Light mode' : 'Dark mode');

	$effect(() => {
		if (!browser || publicThemeLoaded) return;
		publicTheme = resolveInitialPublicTheme({
			storage: window.localStorage,
			matchMedia:
				typeof window.matchMedia === 'function' ? window.matchMedia.bind(window) : undefined
		});
		publicThemeLoaded = true;
	});

	$effect(() => {
		if (!browser || !publicThemeLoaded) return;
		persistPublicTheme(window.localStorage, publicTheme);
		document.documentElement.dataset.publicTheme = publicTheme;
		document.documentElement.style.colorScheme = publicTheme;
		return () => {
			delete document.documentElement.dataset.publicTheme;
			document.documentElement.style.removeProperty('color-scheme');
		};
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

	function togglePublicTheme(): void {
		publicTheme = nextPublicTheme(publicTheme);
	}
</script>

<svelte:head>
	<link rel="stylesheet" href={`${base}/public-site-shell.css`} />
</svelte:head>

<div class="public-site-shell" data-public-tone={publicTone} data-public-theme={publicTheme}>
	<header class="public-site-header">
		<nav class="container public-top-nav mx-auto flex items-center justify-between gap-4 px-6 py-4">
			<a
				href={toAppPath('/')}
				class="public-brand flex items-center gap-2"
				aria-label="Valdrics home"
				data-sveltekit-preload-data="hover"
				data-sveltekit-preload-code="hover"
			>
				<CloudLogo provider="valdrics" size={40} emphasizeMark={true} />
				<img
					src={`${base}/valdrics_wordmark.svg`}
					alt=""
					class="public-brand-wordmark hidden sm:block"
					width="155"
					height="45"
					loading="eager"
					decoding="async"
					fetchpriority="high"
				/>
			</a>

			<div class="public-nav-primary items-center gap-5 text-sm">
				{#each PUBLIC_PRIMARY_LINKS as link (link.href)}
					{#if link.href === '/resources'}
						<div class="public-nav-dropdown">
							<button
								type="button"
								class="public-nav-dropdown-trigger public-nav-link"
								bind:this={publicResourcesButton}
								aria-haspopup="menu"
								aria-expanded={publicResourcesMenuOpen}
								aria-controls="public-resources-menu"
								onclick={togglePublicResourcesMenu}
							>
								<span>{link.label}</span>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="14"
									height="14"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class:rotate-180={publicResourcesMenuOpen}
								>
									<polyline points="6 9 12 15 18 9"></polyline>
								</svg>
							</button>
							{#if publicResourcesMenuOpen}
								<div
									id="public-resources-menu"
									class="public-nav-dropdown-panel"
									role="menu"
									aria-label="Resources"
									bind:this={publicResourcesPanel}
								>
									{#each PUBLIC_RESOURCES_DROPDOWN_LINKS as resourceLink (resourceLink.href)}
										<a
											href={toAppPath(resourceLink.href)}
											role="menuitem"
											class="public-nav-dropdown-item"
											data-sveltekit-preload-data="hover"
											data-sveltekit-preload-code="hover"
											onclick={closePublicResourcesMenu}
										>
											{resourceLink.label}
										</a>
									{/each}
								</div>
							{/if}
						</div>
					{:else}
						<a
							href={toAppPath(link.href)}
							class="public-nav-link"
							data-sveltekit-preload-data="hover"
							data-sveltekit-preload-code="hover"
						>
							{link.label}
						</a>
					{/if}
				{/each}
			</div>

			<div class="public-nav-secondary items-center gap-2">
				<button
					type="button"
					class="public-theme-toggle"
					aria-label={themeToggleLabel(publicTheme)}
					aria-pressed={publicTheme === 'dark'}
					title={themeToggleLabel(publicTheme)}
					onclick={togglePublicTheme}
				>
					<span class="public-theme-toggle__icon" aria-hidden="true">
						{#if publicTheme === 'dark'}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="16"
								height="16"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<circle cx="12" cy="12" r="4"></circle>
								<path d="M12 2v2"></path>
								<path d="M12 20v2"></path>
								<path d="m4.93 4.93 1.41 1.41"></path>
								<path d="m17.66 17.66 1.41 1.41"></path>
								<path d="M2 12h2"></path>
								<path d="M20 12h2"></path>
								<path d="m6.34 17.66-1.41 1.41"></path>
								<path d="m19.07 4.93-1.41 1.41"></path>
							</svg>
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="16"
								height="16"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
							</svg>
						{/if}
					</span>
					<span>{themeToggleCopy(publicTheme)}</span>
				</button>
				<a
					href={toAppPath('/enterprise')}
					class="btn btn-secondary text-sm px-4 py-2"
					data-sveltekit-preload-data="hover"
					data-sveltekit-preload-code="hover"
				>
					Enterprise Review
				</a>
				<a
					href={toAppPath('/auth/login')}
					class="btn btn-primary text-sm px-4 py-2"
					data-sveltekit-preload-data="hover"
					data-sveltekit-preload-code="hover"
				>
					Start Free
				</a>
			</div>

			<div class="public-nav-mobile flex items-center gap-2">
				<button
					type="button"
					class="public-theme-toggle public-theme-toggle--icon-only"
					aria-label={themeToggleLabel(publicTheme)}
					aria-pressed={publicTheme === 'dark'}
					title={themeToggleLabel(publicTheme)}
					onclick={togglePublicTheme}
				>
					<span class="public-theme-toggle__icon" aria-hidden="true">
						{#if publicTheme === 'dark'}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="16"
								height="16"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<circle cx="12" cy="12" r="4"></circle>
								<path d="M12 2v2"></path>
								<path d="M12 20v2"></path>
								<path d="m4.93 4.93 1.41 1.41"></path>
								<path d="m17.66 17.66 1.41 1.41"></path>
								<path d="M2 12h2"></path>
								<path d="M20 12h2"></path>
								<path d="m6.34 17.66-1.41 1.41"></path>
								<path d="m19.07 4.93-1.41 1.41"></path>
							</svg>
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="16"
								height="16"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
							</svg>
						{/if}
					</span>
					<span class="sr-only">{themeToggleCopy(publicTheme)}</span>
				</button>
				<a
					href={toAppPath('/auth/login')}
					class="btn btn-primary public-nav-mobile-cta"
					data-sveltekit-preload-data="hover"
					data-sveltekit-preload-code="hover"
				>
					Start Free
				</a>
				<button
					type="button"
					class="btn btn-ghost p-2 public-nav-menu-toggle"
					bind:this={publicMenuButton}
					aria-label="Toggle menu"
					aria-expanded={publicMenuOpen}
					aria-controls="public-mobile-menu"
					aria-haspopup="dialog"
					onclick={togglePublicMenu}
				>
					<span class="public-nav-menu-label" aria-hidden="true">Menu</span>
					{#if publicMenuOpen}
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
							<line x1="18" y1="6" x2="6" y2="18"></line>
							<line x1="6" y1="6" x2="18" y2="18"></line>
						</svg>
					{:else}
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
					{/if}
				</button>
			</div>
		</nav>
		{#if publicMenuOpen}
			<button
				type="button"
				class="fixed inset-0 z-40 bg-ink-950/50 backdrop-blur-[2px] lg:hidden"
				aria-label="Close navigation menu"
				onclick={closePublicMenu}
			></button>
			<div
				id="public-mobile-menu"
				bind:this={publicMenuPanel}
				class="public-mobile-menu-panel relative z-50 lg:hidden"
				role="dialog"
				aria-modal="true"
				aria-labelledby="public-mobile-menu-title"
			>
				<div class="container mx-auto px-6 py-4 public-mobile-menu-shell">
					<h2 id="public-mobile-menu-title" class="sr-only">Public navigation menu</h2>
					<div class="public-mobile-menu-copy">
						<p class="public-mobile-menu-kicker">Explore Valdrics</p>
						<p class="public-mobile-menu-intro">
							Start in a workspace, review pricing, or contact enterprise when formal security and
							procurement review is required.
						</p>
						<button
							type="button"
							class="public-theme-toggle public-theme-toggle--menu"
							aria-label={themeToggleLabel(publicTheme)}
							aria-pressed={publicTheme === 'dark'}
							onclick={togglePublicTheme}
						>
							<span class="public-theme-toggle__icon" aria-hidden="true">
								{#if publicTheme === 'dark'}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="16"
										height="16"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<circle cx="12" cy="12" r="4"></circle>
										<path d="M12 2v2"></path>
										<path d="M12 20v2"></path>
										<path d="m4.93 4.93 1.41 1.41"></path>
										<path d="m17.66 17.66 1.41 1.41"></path>
										<path d="M2 12h2"></path>
										<path d="M20 12h2"></path>
										<path d="m6.34 17.66-1.41 1.41"></path>
										<path d="m19.07 4.93-1.41 1.41"></path>
									</svg>
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="16"
										height="16"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
									</svg>
								{/if}
							</span>
							<span>{themeToggleCopy(publicTheme)}</span>
						</button>
					</div>
					<div class="grid gap-2 text-sm text-ink-200 public-mobile-menu-links">
						<a
							href={toAppPath('/enterprise')}
							class="btn btn-primary justify-center mb-1 w-full"
							data-sveltekit-preload-data="hover"
							data-sveltekit-preload-code="hover"
							onclick={closePublicMenu}
						>
							Enterprise Review
						</a>
						<a
							href={toAppPath('/auth/login')}
							class="btn btn-secondary justify-center mb-2 w-full"
							data-sveltekit-preload-data="hover"
							data-sveltekit-preload-code="hover"
							onclick={closePublicMenu}
						>
							Start Free
						</a>
						{#each PUBLIC_MOBILE_LINKS as link (link.href)}
							<a
								href={toAppPath(link.href)}
								class="py-3 min-h-11 flex items-center hover:text-ink-100"
								data-sveltekit-preload-data="hover"
								data-sveltekit-preload-code="hover"
								onclick={closePublicMenu}
							>
								{link.label}
							</a>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</header>

	<main id="main" tabindex="-1" class="page-enter public-site-main">
		{@render children()}
	</main>

	<footer class="public-site-footer">
		<div class="container mx-auto px-6 py-10">
			<div class="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
				<div class="space-y-2">
					<p class="public-footer-brand text-sm font-semibold">Valdrics</p>
					<p class="public-footer-subtitle max-w-xl">{PUBLIC_FOOTER_SUBTITLE}</p>
				</div>

				<nav
					class="public-footer-nav grid grid-cols-2 gap-x-6 gap-y-2 md:grid-cols-4"
					aria-label="Footer"
				>
					{#each PUBLIC_FOOTER_LINKS as link (link.href)}
						{#if link.external}
							<a
								href={link.href}
								target="_blank"
								rel="noopener noreferrer"
								class="public-footer-link"
							>
								{link.label}
							</a>
						{:else}
							<a
								href={toAppPath(link.href)}
								class="public-footer-link"
								data-sveltekit-preload-data="hover"
								data-sveltekit-preload-code="hover"
							>
								{link.label}
							</a>
						{/if}
					{/each}
				</nav>
			</div>

			<div class="mt-6 flex flex-wrap items-center gap-2" aria-label="Technology badges">
				{#each PUBLIC_FOOTER_BADGES as badge (badge)}
					<span
						class={`badge ${badge === 'Owner-routed actions' ? 'badge-success' : 'badge-default'}`}
					>
						{badge}
					</span>
				{/each}
			</div>

			<p class="public-footer-caption mt-4">{PUBLIC_FOOTER_CAPTION}</p>

			<div class="mt-5 space-y-2" aria-label="Public contact channels">
				<p class="public-footer-contact-label">Contact Channels</p>
				<div class="flex flex-wrap gap-2">
					{#each PUBLIC_CONTACT_CHANNELS as channel (channel.email)}
						<a
							href={channel.href}
							class="badge badge-default public-footer-contact"
							aria-label={`${channel.label} contact ${channel.email}`}
						>
							{channel.label}: {channel.email}
						</a>
					{/each}
				</div>
			</div>
			<p class="public-footer-copyright mt-6">© {currentYear} Valdrics. All rights reserved.</p>
		</div>
	</footer>
</div>
