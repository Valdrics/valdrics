<script lang="ts">
	import { onMount } from 'svelte';

	let {
		selfServeHref,
		resourcesHref,
		subscribeApiPath,
		onTrackCta
	}: {
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

	let open = $state(false);
	let email = $state('');
	let submitting = $state(false);
	let status = $state<'idle' | 'success' | 'error'>('idle');

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
			if (open || hasActiveSuppression()) return;
			if (!supportsDesktopExitIntent()) return;
			if (event.relatedTarget !== null) return;
			if (event.clientY > 10) return;
			openPrompt('desktop_exit_intent');
		};

		const handleScroll = () => {
			if (open || hasActiveSuppression()) return;
			const scrollRoot = document.documentElement;
			const scrollHeight = Math.max(scrollRoot.scrollHeight, document.body.scrollHeight);
			const scrollableHeight = scrollHeight - window.innerHeight;
			if (scrollableHeight <= 0) return;
			const scrollTop = Math.max(window.scrollY, scrollRoot.scrollTop, document.body.scrollTop);
			if (scrollTop / scrollableHeight < DEEP_SCROLL_TRIGGER_RATIO) return;
			openPrompt('deep_scroll_prompt');
		};

		window.addEventListener('mouseout', handleMouseOut);
		window.addEventListener('scroll', handleScroll, { passive: true });
		handleScroll();
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
