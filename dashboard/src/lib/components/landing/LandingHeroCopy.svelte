<script lang="ts">
	import {
		ABOVE_FOLD_TRUST_RAIL,
		HERO_OUTCOME_CHIPS,
		HERO_PROOF_POINTS
	} from '$lib/landing/heroContent';

	const heroTrustRail = ABOVE_FOLD_TRUST_RAIL;
	const heroOutcomeChips = HERO_OUTCOME_CHIPS;
	const heroProofPoints = HERO_PROOF_POINTS;
	const heroJumpLinks = [
		{ href: '#product', label: 'Explore Product' },
		{ href: '#signal-map', label: 'See Decision Loop' },
		{ href: '#plans', label: 'Compare Plans' },
		{ href: '#trust', label: 'Review Trust' }
	] as const;

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

<div class="landing-hero-grid">
	<div class="landing-copy">
		<div class="landing-kicker fade-in-up" style="animation-delay: 0ms;">
			<span class="badge badge-accent">Governed action for cloud, SaaS, and software spend</span>
			<span class="landing-sep" aria-hidden="true">•</span>
			<span class="landing-kicker-text"
				>Detect waste. Route the owner. Approve the action. Keep the proof.</span
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

		<div class="landing-free-strip fade-in-up" style="animation-delay: 250ms;">
			<span class="landing-free-pill">Permanent Free Tier</span>
			<span
				>Start with one owner-routed workflow and expand only when rollout needs deeper controls.</span
			>
		</div>

		<nav
			class="landing-hero-jumpnav fade-in-up"
			style="animation-delay: 260ms;"
			aria-label="Browse landing sections"
		>
			{#each heroJumpLinks as link (link.href)}
				<a class="landing-hero-jumpnav-link" href={link.href}>{link.label}</a>
			{/each}
		</nav>

		<div class="landing-hero-credibility fade-in-up" style="animation-delay: 270ms;">
			<div class="landing-hero-proof-rail" role="list" aria-label="Prelaunch proof in hero">
				{#each heroTrustRail as item (item.title)}
					<p
						class="landing-hero-proof-rail-item"
						role="listitem"
						aria-label={`${item.title}. ${item.detail}`}
					>
						{item.title}
					</p>
				{/each}
			</div>
		</div>
	</div>

	<div class="landing-hero-support-grid fade-in-up" style="animation-delay: 300ms;">
		<article
			class="card landing-hero-mini-visual"
			aria-label="See the governed loop before rollout"
		>
			<h2 class="landing-h3">See the governed loop before rollout</h2>
			<p class="landing-p">
				Your first controlled workflow should reveal the owner, the attached checks, and the proof
				that survives the meeting.
			</p>
			<div class="landing-hero-flow" role="list" aria-label="Governed action loop">
				{#each heroProofPoints as point (point.title)}
					<div class="landing-hero-flow-step" role="listitem">
						<p class="landing-hero-flow-step-k">{point.title}</p>
						<p class="landing-hero-flow-step-v">{point.detail}</p>
					</div>
				{/each}
			</div>
		</article>

		<article class="card landing-hero-proof-card" aria-label="What changes after onboarding">
			<h2 class="landing-h3">What changes after onboarding</h2>
			<p class="landing-p">
				Start at $0 with one governed workflow, then expand into Growth or Pro only when Slack,
				Jira, SSO, or finance-grade controls become operational requirements.
			</p>
			<div class="landing-hero-stage-strip" role="list" aria-label="Governed action stages">
				{#each heroProofPoints as point, index (point.title)}
					<div class="landing-hero-stage-chip" role="listitem">
						<span class="landing-hero-stage-chip-step">0{index + 1}</span>
						<div class="landing-hero-stage-chip-copy">
							<p class="landing-hero-stage-chip-k">{point.title}</p>
							<p class="landing-hero-stage-chip-v">{point.detail}</p>
						</div>
					</div>
				{/each}
			</div>
			<p class="landing-hero-proof-meta">
				One named owner. One approval path. One reviewable outcome.
			</p>
			<div class="landing-trust-inline" role="list" aria-label="Hero operating outcomes">
				{#each heroOutcomeChips as item (item.label)}
					<span class="landing-trust-inline-badge" role="listitem">
						<strong>{item.label}:</strong>
						<span>{item.value}</span>
					</span>
				{/each}
			</div>
		</article>
	</div>
</div>
