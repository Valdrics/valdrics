<script lang="ts">
	import { base } from '$app/paths';

	let {
		visible,
		onAccept,
		onReject,
		onClose
	}: {
		visible: boolean;
		onAccept: () => void;
		onReject: () => void;
		onClose: () => void;
	} = $props();
</script>

{#if visible}
	<div
		class="landing-cookie-banner"
		role="dialog"
		aria-modal="false"
		aria-labelledby="cookie-consent-title"
	>
		<button
			type="button"
			class="landing-cookie-banner__close"
			aria-label="Close cookie notice"
			onclick={onClose}
		>
			×
		</button>
		<p id="cookie-consent-title" class="landing-proof-k">Cookie preferences</p>
		<p class="landing-p">
			Valdrics uses local storage for analytics and experiment telemetry on this public page. You
			can accept or decline analytics tracking.
		</p>
		<div class="landing-cookie-banner__actions">
			<button type="button" class="btn btn-secondary" onclick={onReject}>Decline analytics</button>
			<button type="button" class="btn btn-primary" onclick={onAccept}>Accept analytics</button>
		</div>
		<p class="landing-cookie-banner__legal">
			Review <a href={`${base}/privacy`}>Privacy</a> and <a href={`${base}/terms`}>Terms</a>.
		</p>
	</div>
{/if}

<style>
	.landing-cookie-banner {
		position: fixed;
		right: max(0.9rem, env(safe-area-inset-right));
		bottom: max(1rem, env(safe-area-inset-bottom));
		z-index: 95;
		width: min(26rem, calc(100vw - 1.4rem));
		border-radius: var(--radius-xl);
		border: 1px solid rgb(8 126 164 / 0.16);
		padding: 0.9rem 0.95rem;
		background:
			linear-gradient(180deg, rgb(255 255 255 / 0.97), rgb(246 250 252 / 0.95)),
			radial-gradient(360px 140px at 12% 0%, rgb(8 126 164 / 0.08), transparent 72%);
		backdrop-filter: blur(10px);
		-webkit-backdrop-filter: blur(10px);
		display: grid;
		gap: 0.6rem;
		color: var(--color-ink-900);
		box-shadow: 0 18px 42px rgb(15 23 42 / 0.16);
	}

	.landing-cookie-banner__close {
		position: absolute;
		top: 0.45rem;
		right: 0.45rem;
		width: 1.8rem;
		height: 1.8rem;
		border-radius: 9999px;
		border: 1px solid rgb(8 126 164 / 0.14);
		background: rgb(255 255 255 / 0.78);
		color: var(--color-ink-900);
		font-size: 1.1rem;
		line-height: 1;
	}

	.landing-cookie-banner :global(.landing-proof-k) {
		color: var(--color-brand-700);
	}

	.landing-cookie-banner :global(.landing-p) {
		color: var(--color-ink-800);
	}

	.landing-cookie-banner__close:focus-visible {
		outline: 2px solid var(--color-accent-500);
		outline-offset: 2px;
	}

	.landing-cookie-banner__actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.45rem;
	}

	.landing-cookie-banner__legal {
		margin: 0;
		font-size: 0.82rem;
		line-height: 1.5;
		color: var(--color-ink-300);
	}

	.landing-cookie-banner__legal a {
		color: var(--color-accent-300);
		text-decoration: underline;
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner {
		border-color: rgb(255 255 255 / 0.18);
		background: rgb(5 10 16 / 0.96);
		color: var(--color-ink-100);
		box-shadow: 0 22px 48px rgb(2 8 14 / 0.34);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner__close {
		border-color: rgb(255 255 255 / 0.14);
		background: rgb(255 255 255 / 0.05);
		color: var(--color-ink-100);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner :global(.landing-proof-k) {
		color: var(--color-ink-100);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner :global(.landing-p) {
		color: var(--color-ink-100);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner__legal {
		color: var(--color-ink-300);
	}

	:global(.public-site-shell[data-public-theme='dark']) .landing-cookie-banner__legal a {
		color: var(--color-accent-300);
	}
</style>
