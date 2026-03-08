<script lang="ts">
	import { ABOVE_FOLD_TRUST_RAIL } from '$lib/landing/heroContent';

	const heroTrustRail = ABOVE_FOLD_TRUST_RAIL;

	let {
		heroTitle,
		heroSubtitle,
		primaryCtaLabel,
		secondaryCtaLabel,
		secondaryCtaHref,
		primaryCtaHref,
		onPrimaryCta,
		onSecondaryCta
	}: {
		heroTitle: string;
		heroSubtitle: string;
		primaryCtaLabel: string;
		secondaryCtaLabel: string;
		secondaryCtaHref: string;
		primaryCtaHref: string;
		onPrimaryCta: () => void;
		onSecondaryCta: () => void;
	} = $props();
</script>

<div class="landing-copy">
	<div class="landing-kicker fade-in-up" style="animation-delay: 0ms;">
		<span class="badge badge-accent">Decision operating layer for spend control</span>
		<span class="landing-sep" aria-hidden="true">•</span>
		<span class="landing-kicker-text"
			>Route the right owner. Apply checks. Record the outcome.</span
		>
	</div>

	<h1 class="landing-title fade-in-up" style="animation-delay: 80ms;">
		{heroTitle}
	</h1>

	<p class="landing-subtitle fade-in-up" style="animation-delay: 180ms;">
		{heroSubtitle}
	</p>

	<div class="landing-cta fade-in-up" style="animation-delay: 230ms;">
		<a
			href={primaryCtaHref}
			class="btn btn-primary landing-cta-primary text-base px-8 py-3 pulse-glow"
			onclick={onPrimaryCta}
		>
			{primaryCtaLabel}
		</a>
		<a
			href={secondaryCtaHref}
			class="btn btn-secondary landing-cta-secondary text-base px-8 py-3"
			onclick={onSecondaryCta}
		>
			{secondaryCtaLabel}
		</a>
	</div>

	<div class="landing-hero-credibility fade-in-up" style="animation-delay: 270ms;">
		<div class="landing-hero-proof-rail" role="list" aria-label="Prelaunch proof in hero">
			{#each heroTrustRail as item (item.title)}
				<p class="landing-hero-proof-rail-item" role="listitem" aria-label={`${item.title}. ${item.detail}`}>
					{item.title}
				</p>
			{/each}
		</div>
	</div>
</div>
