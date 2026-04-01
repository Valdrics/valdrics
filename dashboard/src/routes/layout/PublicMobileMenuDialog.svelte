<script lang="ts">
	import { onMount } from 'svelte';
	import type { PublicTheme } from '$lib/public/publicTheme';
	import {
		getFocusableElements,
		lockBodyScroll,
		resolveNextFocusTarget
	} from '$lib/landing/publicMenuA11y';
	import { PUBLIC_MOBILE_LINKS } from '$lib/landing/publicNav';

	interface Props {
		publicTheme: PublicTheme;
		themeToggleLabel: string;
		themeToggleCopy: string;
		restoreFocusTarget?: HTMLButtonElement | null;
		toAppPath: (path: string) => string;
		onToggleTheme: () => void;
		onClose: () => void;
	}

	let {
		publicTheme,
		themeToggleLabel,
		themeToggleCopy,
		restoreFocusTarget = null,
		toAppPath,
		onToggleTheme,
		onClose
	}: Props = $props();

	let publicMenuPanel = $state<HTMLDivElement | null>(null);

	onMount(() => {
		const unlockBodyScroll = lockBodyScroll(document);

		queueMicrotask(() => {
			const firstFocusable = getFocusableElements(publicMenuPanel)[0];
			firstFocusable?.focus();
		});

		const initialScrollY = window.scrollY;
		const handleKeydown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				event.preventDefault();
				onClose();
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
		const handleScroll = () => {
			if (Math.abs(window.scrollY - initialScrollY) > 48) {
				onClose();
			}
		};

		window.addEventListener('keydown', handleKeydown);
		window.addEventListener('scroll', handleScroll, { passive: true });

		return () => {
			window.removeEventListener('keydown', handleKeydown);
			window.removeEventListener('scroll', handleScroll);
			unlockBodyScroll();
			restoreFocusTarget?.focus();
		};
	});
</script>

<button
	type="button"
	class="fixed inset-0 z-40 bg-ink-950/50 backdrop-blur-[2px] lg:hidden"
	aria-label="Close navigation menu"
	onclick={onClose}
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
				aria-label={themeToggleLabel}
				aria-pressed={publicTheme === 'dark'}
				onclick={onToggleTheme}
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
				<span>{themeToggleCopy}</span>
			</button>
		</div>
		<div class="grid gap-2 text-sm text-ink-200 public-mobile-menu-links">
			<a
				href={toAppPath('/enterprise')}
				class="btn btn-primary justify-center mb-1 w-full"
				data-sveltekit-preload-data="hover"
				data-sveltekit-preload-code="hover"
				onclick={onClose}
			>
				Enterprise Review
			</a>
			<a
				href={toAppPath('/auth/login')}
				class="btn btn-secondary justify-center mb-2 w-full"
				data-sveltekit-preload-data="hover"
				data-sveltekit-preload-code="hover"
				onclick={onClose}
			>
				Start Free
			</a>
			{#each PUBLIC_MOBILE_LINKS as link (link.href)}
				<a
					href={toAppPath(link.href)}
					class="py-3 min-h-11 flex items-center hover:text-ink-100"
					data-sveltekit-preload-data="hover"
					data-sveltekit-preload-code="hover"
					onclick={onClose}
				>
					{link.label}
				</a>
			{/each}
		</div>
	</div>
</div>
