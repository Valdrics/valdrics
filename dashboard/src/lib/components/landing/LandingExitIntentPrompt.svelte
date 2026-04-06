<script lang="ts">
	import { onMount } from 'svelte';

	let {
		enabled = true,
		selfServeHref,
		resourcesHref,
		subscribeApiPath,
		onTrackCta
	}: {
		enabled?: boolean;
		selfServeHref: string;
		resourcesHref: string;
		subscribeApiPath: string;
		onTrackCta: (action: string, section: string, value: string) => void;
	} = $props();

	const DISMISS_KEY = 'valdrics.landing.exit_prompt.dismissed.v3';
	const SESSION_SEEN_KEY = 'valdrics.landing.exit_prompt.seen.v1';
	const DISMISS_SUPPRESSION_MS = 1000 * 60 * 60 * 24 * 14;
	const SUBSCRIBED_SUPPRESSION_MS = 1000 * 60 * 60 * 24 * 180;
	const DEEP_SCROLL_TRIGGER_RATIO = 0.82;
	const REARM_SCROLL_DELTA_PX = 48;

	let open = $state(false);
	let email = $state('');
	let submitting = $state(false);
	let status = $state<'idle' | 'success' | 'error'>('idle');
	let deepScrollRequiresRearm = $state(false);
	let deepScrollArmScrollTop = $state(0);
	let previousEnabled = $state<boolean | null>(null);

	$effect(() => {
		if (!enabled) {
			open = false;
		}

		if (typeof window !== 'undefined' && previousEnabled !== null && enabled && !previousEnabled) {
			deepScrollRequiresRearm = true;
			deepScrollArmScrollTop = Math.max(
				window.scrollY,
				document.documentElement.scrollTop,
				document.body.scrollTop
			);
		}

		previousEnabled = enabled;
	});

	function hasActiveSuppression(): boolean {
		if (typeof window === 'undefined') return true;
		const dismissedUntil = Number(window.localStorage.getItem(DISMISS_KEY) ?? '0');
		if (Number.isFinite(dismissedUntil) && dismissedUntil > Date.now()) return true;
		if (dismissedUntil > 0) {
			window.localStorage.removeItem(DISMISS_KEY);
		}
		return window.sessionStorage.getItem(SESSION_SEEN_KEY) === '1';
	}

	function markSeen(): void {
		if (typeof window === 'undefined') return;
		window.sessionStorage.setItem(SESSION_SEEN_KEY, '1');
	}

	function openPrompt(reason: 'desktop_exit_intent' | 'deep_scroll_prompt'): void {
		if (open || hasActiveSuppression()) return;
		open = true;
		markSeen();
		onTrackCta('cta_view', 'exit_prompt', reason);
	}

	function persistDismissal(durationMs: number): void {
		if (typeof window === 'undefined') return;
		window.localStorage.setItem(DISMISS_KEY, String(Date.now() + durationMs));
	}

	function dismiss(): void {
		open = false;
		persistDismissal(DISMISS_SUPPRESSION_MS);
	}

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (submitting || !email.trim()) return;
		submitting = true;
		status = 'idle';
		try {
			const response = await fetch(subscribeApiPath, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					email,
					referrer: 'landing_exit_prompt',
					honey: ''
				})
			});
			if (!response.ok) {
				throw new Error(`subscribe_${response.status}`);
			}
			status = 'success';
			persistDismissal(SUBSCRIBED_SUPPRESSION_MS);
			onTrackCta('cta_click', 'exit_prompt', 'newsletter_subscribe_success');
		} catch {
			status = 'error';
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		if (typeof window === 'undefined') return;
		if (hasActiveSuppression()) return;

		const supportsDesktopExitIntent = () =>
			!(
				typeof window.matchMedia === 'function' &&
				window.matchMedia('(max-width: 1023px)').matches
			);

		const handleMouseOut = (event: MouseEvent) => {
			if (!enabled) return;
			if (open || hasActiveSuppression()) return;
			if (!supportsDesktopExitIntent()) return;
			if (event.relatedTarget !== null) return;
			if (event.clientY > 10) return;
			openPrompt('desktop_exit_intent');
		};

		const handleScroll = () => {
			if (!enabled) return;
			if (open || hasActiveSuppression()) return;
			const scrollRoot = document.documentElement;
			const scrollHeight = Math.max(scrollRoot.scrollHeight, document.body.scrollHeight);
			const scrollableHeight = scrollHeight - window.innerHeight;
			if (scrollableHeight <= 0) return;
			const scrollTop = Math.max(window.scrollY, scrollRoot.scrollTop, document.body.scrollTop);
			if (deepScrollRequiresRearm) {
				if (Math.abs(scrollTop - deepScrollArmScrollTop) < REARM_SCROLL_DELTA_PX) {
					return;
				}
				deepScrollRequiresRearm = false;
			}
			if (scrollTop / scrollableHeight < DEEP_SCROLL_TRIGGER_RATIO) return;
			openPrompt('deep_scroll_prompt');
		};

		window.addEventListener('mouseout', handleMouseOut);
		window.addEventListener('scroll', handleScroll, { passive: true });
		if (enabled) {
			handleScroll();
		}
		return () => {
			window.removeEventListener('mouseout', handleMouseOut);
			window.removeEventListener('scroll', handleScroll);
		};
	});
</script>

{#if open}
	<div
		class="landing-exit-prompt"
		role="dialog"
		aria-modal="true"
		aria-labelledby="exit-prompt-title"
	>
		<button
			type="button"
			class="landing-exit-backdrop"
			aria-label="Dismiss backdrop"
			onclick={dismiss}
		></button>
		<div class="landing-exit-panel">
			<button type="button" class="landing-exit-close" onclick={dismiss} aria-label="Close prompt">
				×
			</button>
			<p class="landing-proof-k">Before you go</p>
			<h2 id="exit-prompt-title" class="landing-h3">Want a weekly spend-control brief instead?</h2>
			<p class="landing-p">
				Get concise cloud and software optimization insights, then start free when your team is
				ready.
			</p>
			<form class="landing-exit-form" onsubmit={submit}>
				<label class="landing-roi-label" for="exit-email">Work email</label>
				<input
					id="exit-email"
					type="email"
					class="input"
					placeholder="you@company.com"
					required
					maxlength="254"
					bind:value={email}
				/>
				<button type="submit" class="btn btn-primary" disabled={submitting}>
					{submitting ? 'Submitting...' : 'Send Insights'}
				</button>
			</form>
			{#if status === 'success'}
				<p class="landing-lead-status is-success" role="status">Subscribed. Check your inbox.</p>
			{:else if status === 'error'}
				<p class="landing-lead-status is-error" role="alert">
					Subscription failed. You can still use the links below.
				</p>
			{/if}
			<div class="landing-exit-actions">
				<a
					href={resourcesHref}
					class="btn btn-secondary"
					onclick={() => onTrackCta('cta_click', 'exit_prompt', 'open_resources')}
				>
					Open Resources
				</a>
				<a
					href={selfServeHref}
					class="btn btn-primary"
					onclick={() => onTrackCta('cta_click', 'exit_prompt', 'start_free')}
				>
					Start Free Workspace
				</a>
			</div>
		</div>
	</div>
{/if}

<style>
	.landing-exit-prompt {
		position: fixed;
		inset: 0;
		z-index: 90;
		display: grid;
		place-items: center;
		padding: 1rem;
	}

	.landing-exit-backdrop {
		position: absolute;
		inset: 0;
		border: 0;
		padding: 0;
		background: rgb(2 6 11 / 0.72);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
	}

	.landing-exit-panel {
		position: relative;
		z-index: 1;
		width: min(32rem, 100%);
		border-radius: var(--radius-xl);
		border: 1px solid rgb(8 126 164 / 0.16);
		padding: 1rem;
		background:
			linear-gradient(180deg, rgb(255 255 255 / 0.98), rgb(246 250 252 / 0.96)),
			radial-gradient(420px 160px at 14% 0%, rgb(8 126 164 / 0.08), transparent 72%);
		display: grid;
		gap: 0.75rem;
		color: var(--color-ink-900);
		box-shadow: 0 24px 52px rgb(15 23 42 / 0.2);
	}

	.landing-exit-close {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		width: 2rem;
		height: 2rem;
		border-radius: 9999px;
		border: 1px solid rgb(8 126 164 / 0.14);
		background: rgb(255 255 255 / 0.82);
		color: var(--color-ink-900);
		font-size: 1.35rem;
		line-height: 1;
	}

	.landing-exit-panel :global(.landing-proof-k) {
		color: var(--color-brand-700);
	}

	.landing-exit-panel :global(.landing-p),
	.landing-exit-panel :global(.landing-h3),
	.landing-exit-panel :global(.landing-roi-label) {
		color: var(--color-ink-900);
	}

	.landing-exit-close:focus-visible {
		outline: 2px solid var(--color-accent-500);
		outline-offset: 2px;
	}

	.landing-exit-form {
		display: grid;
		gap: 0.6rem;
	}

	.landing-exit-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-panel {
		border-color: rgb(255 255 255 / 0.15);
		background: rgb(6 12 18 / 0.94);
		color: var(--color-ink-100);
		box-shadow: 0 24px 52px rgb(2 8 14 / 0.34);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-close {
		border-color: rgb(255 255 255 / 0.16);
		background: rgb(255 255 255 / 0.06);
		color: var(--color-ink-100);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-panel :global(.landing-proof-k),
	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-panel :global(.landing-p),
	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-panel :global(.landing-h3),
	:global(.public-site-shell[data-public-theme='dark']) .landing-exit-panel :global(.landing-roi-label) {
		color: var(--color-ink-100);
	}
</style>
