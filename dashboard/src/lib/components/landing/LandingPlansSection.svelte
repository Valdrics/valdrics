<script lang="ts">
	import { base } from '$app/paths';

	const landingPlanPreview = [
		{
			name: 'Free',
			price: '$0',
			summary: 'Prove one owner-routed workflow without procurement overhead.',
			cta: 'Start Free Workspace',
			href: null
		},
		{
			name: 'Growth',
			price: '$149',
			summary:
				'Best fit for cross-functional teams that need shared cost ownership and collaboration.',
			cta: 'See Growth on Pricing',
			href: `${base}/pricing`
		},
		{
			name: 'Pro',
			price: '$299',
			summary:
				'Finance-grade controls, exports, and workflow depth without jumping straight into enterprise sales.',
			cta: 'Review Pro Details',
			href: `${base}/pricing`
		}
	] as const;

	let {
		freeTierCtaHref,
		trustEnterpriseHref,
		onTrackCta
	}: {
		freeTierCtaHref: string;
		trustEnterpriseHref: string;
		onTrackCta: (action: string, section: string, value: string) => void;
	} = $props();
</script>

<section id="plans" class="landing-public-section" data-landing-section="plans">
	<div class="container mx-auto px-6 py-12">
		<div class="landing-public-section-head">
			<p class="landing-public-eyebrow">Pricing</p>
			<h2>Pricing that matches rollout stage</h2>
			<p>
				Start small, prove the workflow, and only move up when the team needs more governance depth.
			</p>
		</div>
		<div class="landing-public-plan-grid">
			{#each landingPlanPreview as plan (plan.name)}
				<article class="landing-public-surface landing-public-plan-card">
					<p class="landing-public-proof-label">{plan.name}</p>
					<div class="landing-public-plan-price">{plan.price}</div>
					<p>{plan.summary}</p>
					{#if plan.href}
						<a
							href={plan.href}
							class="btn btn-secondary"
							onclick={() => onTrackCta('cta_click', 'plans', plan.name.toLowerCase())}
						>
							{plan.cta}
						</a>
					{:else}
						<a
							href={freeTierCtaHref}
							class="btn btn-primary"
							onclick={() => onTrackCta('cta_click', 'plans', 'free')}
						>
							{plan.cta}
						</a>
					{/if}
				</article>
			{/each}
		</div>
		<div class="landing-public-band landing-public-band--compact">
			<div>
				<p class="landing-public-eyebrow">Full pricing</p>
				<h3>Compare the full plan details before you commit</h3>
				<p>
					Use the pricing page for the full plan breakdown. Use enterprise review only when
					security, procurement, or deployment requirements need a separate path.
				</p>
			</div>
			<div class="landing-public-band-actions">
				<a
					href={`${base}/pricing`}
					class="btn btn-secondary"
					onclick={() => onTrackCta('cta_click', 'plans', 'view_pricing')}
				>
					See Detailed Pricing
				</a>
				<a
					href={trustEnterpriseHref}
					class="btn btn-secondary"
					onclick={() => onTrackCta('cta_click', 'plans', 'enterprise_review')}
				>
					Enterprise Review
				</a>
			</div>
		</div>
	</div>
</section>
