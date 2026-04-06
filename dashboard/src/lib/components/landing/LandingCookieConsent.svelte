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
		border: 1px solid rgb(255 255 255 / 0.18);
		padding: 0.9rem 0.95rem;
		background: rgb(5 10 16 / 0.96);
		backdrop-filter: blur(10px);
		-webkit-backdrop-filter: blur(10px);
		display: grid;
		gap: 0.6rem;
	}

	.landing-cookie-banner__close {
		position: absolute;
		top: 0.45rem;
		right: 0.45rem;
		width: 1.8rem;
		height: 1.8rem;
		border-radius: 9999px;
		border: 1px solid rgb(255 255 255 / 0.14);
		background: rgb(255 255 255 / 0.05);
		color: var(--color-ink-100);
		font-size: 1.1rem;
		line-height: 1;
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
</style>
