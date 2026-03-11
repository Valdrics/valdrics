<script lang="ts">
	import { base } from '$app/paths';
	import {
		FREE_TIER_HIGHLIGHTS,
		FREE_TIER_LIMIT_NOTE,
		IMPLEMENTATION_COST_FACTS,
		PLAN_COMPARE_CARDS,
		PLANS_PRICING_EXPLANATION
	} from '$lib/landing/heroContent';
	import { DEFAULT_PRICING_PLANS } from '$lib/pricing/publicPlans';

	let {
		buildFreeTierCtaHref,
		buildPlanCtaHref,
		onTrackCta
	}: {
		buildFreeTierCtaHref: () => string;
		buildPlanCtaHref: (planId: string) => string;
		onTrackCta: (action: string, section: string, value: string) => void;
	} = $props();

	const freePlan = DEFAULT_PRICING_PLANS.find((plan) => plan.id === 'free');

	if (!freePlan?.story) {
		throw new Error('Landing plans section requires a free-plan public story.');
	}

	const freePlanStory = freePlan.story;
	const enterprisePathHref = `${base}/enterprise`;
</script>

<section
	id="plans"
	class="container mx-auto px-6 pb-16 landing-section-lazy"
	data-landing-section="plans"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">Choose the plan that fits your control depth</h2>
		<p class="landing-section-sub">{PLANS_PRICING_EXPLANATION}</p>
	</div>

	<div class="landing-plan-choices">
		<div class="landing-plans-grid">
			{#each PLAN_COMPARE_CARDS as plan (plan.id)}
				<article
					class={`glass-panel landing-plan-card ${plan.popular ? 'is-featured' : ''}`}
					data-plan-id={plan.id}
				>
					<p class="landing-proof-k">{plan.badge}</p>
					<h3 class="landing-h3">{plan.name}</h3>
					<p class="landing-plan-price">{plan.price}</p>
					<p class="landing-plan-price-note">{plan.priceNote}</p>
					<p class="landing-p">{plan.summary}</p>
					<ul class="landing-plan-features">
						{#each plan.features as feature (feature)}
							<li>{feature}</li>
						{/each}
					</ul>
					<dl class="landing-plan-context" aria-label={`${plan.name} plan fit and upgrade path`}>
						<div class="landing-plan-context__row">
							<dt class="landing-plan-context__label">Best for</dt>
							<dd class="landing-plan-context__value">{plan.bestFor}</dd>
						</div>
						<div class="landing-plan-context__row">
							<dt class="landing-plan-context__label">Why teams upgrade</dt>
							<dd class="landing-plan-context__value">{plan.whyUpgrade}</dd>
						</div>
					</dl>
					<a
						href={buildPlanCtaHref(plan.id)}
						class={`btn ${plan.popular ? 'btn-primary landing-plan-primary-cta' : 'btn-secondary landing-plan-secondary-cta'}`}
						onclick={() => onTrackCta('cta_click', 'plans', `start_plan_${plan.id}`)}
					>
						{`Start with ${plan.name}`}
					</a>
				</article>
			{/each}
		</div>

		<div class="landing-free-tier-card glass-panel">
			<div class="landing-free-tier-head">
				<div>
					<p class="landing-free-tier-badge">{freePlanStory.badge}</p>
					<p class="landing-proof-k">Self-serve path</p>
					<h3 class="landing-h3">{freePlanStory.headline}</h3>
					<p class="landing-p">{freePlanStory.summary}</p>
				</div>
				<div class="landing-free-tier-price">
					<p class="landing-free-tier-price-k">Entry Price</p>
					<p class="landing-free-tier-price-v">$0</p>
				</div>
			</div>
			<ul class="landing-plan-features">
				{#each FREE_TIER_HIGHLIGHTS as feature (feature)}
					<li>{feature}</li>
				{/each}
			</ul>
			<dl class="landing-plan-context" aria-label="Free plan fit and upgrade path">
				<div class="landing-plan-context__row">
					<dt class="landing-plan-context__label">Best for</dt>
					<dd class="landing-plan-context__value">{freePlanStory.bestFor}</dd>
				</div>
				<div class="landing-plan-context__row">
					<dt class="landing-plan-context__label">Why teams upgrade</dt>
					<dd class="landing-plan-context__value">{freePlanStory.whyUpgrade}</dd>
				</div>
			</dl>
			<p class="landing-free-tier-limit">{FREE_TIER_LIMIT_NOTE}</p>
			<div class="landing-free-tier-cta">
				<a
					href={buildFreeTierCtaHref()}
					class="btn btn-primary landing-free-tier-primary-cta"
					onclick={() => onTrackCta('cta_click', 'plans', 'start_plan_free')}
				>
					Start on Free Tier
				</a>
				<span class="landing-free-tier-note"
					>Upgrade when team rollout or deeper governance becomes necessary.</span
				>
			</div>
		</div>
	</div>
	<section class="landing-rollout-section glass-panel" aria-labelledby="rollout-tco-title">
		<p class="landing-proof-k">Rollout and buying path</p>
		<h3 id="rollout-tco-title" class="landing-h3">
			Know the team footprint before signup or procurement
		</h3>
		<p class="landing-p">
			Start with one controlled workflow in a workspace. Use the enterprise path only when audit,
			procurement, or rollout governance needs a formal diligence lane.
		</p>

		<div class="landing-rollout-grid">
			<article class="landing-rollout-block">
				<p class="landing-proof-k">Setup path</p>
				<ol class="landing-onboard-steps">
					<li>Connect cloud and software sources.</li>
					<li>Assign owners and approval responsibilities.</li>
					<li>Run your first owner-led remediation cycle.</li>
				</ol>
			</article>

			<article class="landing-rollout-block">
				<p class="landing-proof-k">Implementation facts</p>
				<ul class="landing-plan-features">
					{#each IMPLEMENTATION_COST_FACTS as detail (detail)}
						<li>{detail}</li>
					{/each}
				</ul>
			</article>
		</div>

		<div class="landing-rollout-actions">
			<a
				href={`${base}/pricing`}
				class="landing-cta-link"
				onclick={() => onTrackCta('cta_click', 'plans', 'view_full_pricing')}
			>
				View full pricing
			</a>
			<a
				href={enterprisePathHref}
				class="btn btn-secondary"
				onclick={() => onTrackCta('cta_click', 'plans', 'enterprise_review')}
			>
				Open Enterprise Path
			</a>
		</div>
	</section>
</section>
