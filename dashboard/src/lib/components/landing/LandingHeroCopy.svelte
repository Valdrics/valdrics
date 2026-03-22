<script lang="ts">
	import { ABOVE_FOLD_TRUST_RAIL } from '$lib/landing/heroContent';

	const heroTrustRail = ABOVE_FOLD_TRUST_RAIL.slice(0, 3);

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

<div class="landing-copy landing-copy--public">
	<div class="landing-kicker fade-in-up fade-delay-0">
		<span class="badge badge-accent">Spend governance</span>
		<span class="landing-kicker-text"
			>Built for finance and engineering teams that want less sprawl</span
		>
	</div>

	<h1 class="landing-title fade-in-up fade-delay-1">{heroTitle}</h1>

	<p class="landing-subtitle fade-in-up fade-delay-2">{heroSubtitle}</p>

	<div class="landing-cta fade-in-up fade-delay-3">
		<a
			href={primaryCtaHref}
			class="btn btn-primary landing-cta-primary text-base px-8 py-3"
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

	<div
		class="landing-copy-points fade-in-up fade-delay-4"
		role="list"
		aria-label="Why buyers engage"
	>
		{#each heroTrustRail as item (item.title)}
			<article class="landing-copy-point" role="listitem">
				<p class="landing-copy-point-title">{item.title}</p>
				<p class="landing-copy-point-detail">{item.detail}</p>
			</article>
		{/each}
	</div>
</div>
