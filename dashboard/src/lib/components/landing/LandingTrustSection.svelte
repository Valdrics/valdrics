<script lang="ts">
	import {
		COMPLIANCE_FOUNDATION_BADGES,
		CUSTOMER_PROOF_STORIES,
		CUSTOMER_QUOTES,
		EXECUTIVE_CONFIDENCE_POINTS,
		TRUST_BENCHMARK_OUTCOMES,
		TRUST_ECOSYSTEM_BADGES
	} from '$lib/landing/heroContent';

	let {
		onTrackCta,
		requestValidationBriefingHref,
		onePagerHref
	}: {
		onTrackCta: (value: 'request_validation_briefing' | 'download_executive_one_pager') => void;
		requestValidationBriefingHref: string;
		onePagerHref: string;
	} = $props();
</script>

<section id="trust" class="container mx-auto px-6 pb-16 landing-section-lazy" data-landing-section="proof">
	<div class="landing-section-head">
		<h2 class="landing-h2">Proof framework for reducing spend waste</h2>
		<p class="landing-section-sub">
			Buyers need outcomes, not claims. Valdrics is built to show clear before-and-after results.
		</p>
	</div>

	<div class="landing-evidence-grid">
		{#each EXECUTIVE_CONFIDENCE_POINTS as point (point.title)}
			<article class="glass-panel landing-evidence-card">
				<p class="landing-proof-k">{point.kicker}</p>
				<h3 class="landing-h3">{point.title}</h3>
				<p class="landing-p">{point.detail}</p>
			</article>
		{/each}
	</div>

	<div class="landing-trust-ecosystem">
		<p class="landing-proof-k">Platform Coverage</p>
		<div class="landing-trust-badges">
			{#each TRUST_ECOSYSTEM_BADGES as badge (badge)}
				<span class="landing-trust-badge">{badge}</span>
			{/each}
		</div>
	</div>

	<div class="landing-story-grid">
		{#each CUSTOMER_PROOF_STORIES as story (story.title)}
			<article class="glass-panel landing-story-card">
				<p class="landing-proof-k">{story.title}</p>
				<p class="landing-story-label">Before</p>
				<p class="landing-p">{story.before}</p>
				<p class="landing-story-label">After</p>
				<p class="landing-p">{story.after}</p>
				<p class="landing-trust-benchmark-k">{story.impact}</p>
			</article>
		{/each}
	</div>

	<div class="landing-trust-benchmarks">
		{#each TRUST_BENCHMARK_OUTCOMES as outcome (outcome.title)}
			<article class="glass-panel landing-trust-benchmark">
				<p class="landing-proof-k">Outcome Pattern</p>
				<h3 class="landing-h3">{outcome.title}</h3>
				<p class="landing-p">{outcome.detail}</p>
				<p class="landing-trust-benchmark-k">{outcome.benchmark}</p>
			</article>
		{/each}
	</div>

	<div class="landing-testimonial-grid">
		{#each CUSTOMER_QUOTES as quote (quote.quote)}
			<blockquote class="glass-panel landing-testimonial-card">
				<p class="landing-testimonial-quote">"{quote.quote}"</p>
				<cite class="landing-testimonial-cite">{quote.attribution}</cite>
			</blockquote>
		{/each}
	</div>

	<div class="landing-compliance-block">
		<p class="landing-proof-k">Security and compliance essentials</p>
		<div class="landing-trust-badges">
			{#each COMPLIANCE_FOUNDATION_BADGES as badge (badge)}
				<span class="landing-trust-badge">{badge}</span>
			{/each}
		</div>
	</div>
	<div class="landing-validation-cta glass-panel">
		<p class="landing-proof-k">Executive Readiness Kit</p>
		<p class="landing-p">
			Get the materials buyers ask for: rollout model, governance checklist, and one-page business
			case.
		</p>
		<div class="landing-lead-actions">
			<a
				href={requestValidationBriefingHref}
				class="btn btn-secondary w-fit"
				onclick={() => onTrackCta('request_validation_briefing')}
			>
				Book Executive Briefing
			</a>
			<a
				href={onePagerHref}
				class="btn btn-secondary w-fit"
				onclick={() => onTrackCta('download_executive_one_pager')}
			>
				Download Executive One-Pager
			</a>
		</div>
	</div>
	<p class="landing-trust-note">
		Use the briefing and one-pager to align engineering, finance, and security before kickoff.
	</p>
</section>
