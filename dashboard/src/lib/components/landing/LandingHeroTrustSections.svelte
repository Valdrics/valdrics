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
		aboutHref,
		docsHref,
		statusHref,
		proofHref = '/proof',
		requestValidationBriefingHref,
		onePagerHref,
		onTrackCta
	}: {
		freeTierCtaHref: string;
		trustEnterpriseHref: string;
		aboutHref: string;
		docsHref: string;
		statusHref: string;
		proofHref?: string;
		requestValidationBriefingHref: string;
		onePagerHref: string;
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
					Use the pricing page for full plan details. Contact enterprise for security, procurement,
					or deployment requirements.
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

<section id="trust" class="landing-public-section" data-landing-section="trust">
	<div class="container mx-auto px-6 py-12">
		<div class="landing-public-section-head">
			<p class="landing-public-eyebrow">Trust</p>
			<h2>Review the company before you talk to us</h2>
			<p>Review the company, proof pack, and technical materials before you book a call.</p>
		</div>
		<div class="landing-public-trust-grid">
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Proof pack</p>
				<h3>Start with the materials, not the pitch</h3>
				<p>Open the proof pack, one-pager, and technical validation notes directly.</p>
				<div class="landing-public-link-list">
					<a href={proofHref} onclick={() => onTrackCta('cta_click', 'trust', 'proof_pack')}>
						Open Proof Pack
					</a>
					<a href={onePagerHref} onclick={() => onTrackCta('cta_click', 'trust', 'one_pager')}>
						Download One-Pager
					</a>
					<a href={docsHref} onclick={() => onTrackCta('cta_click', 'trust', 'docs')}>
						Technical Validation
					</a>
				</div>
			</article>
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Company</p>
				<h3>Know who is behind the product</h3>
				<p>
					Review the founder, company background, and public contact channels before procurement
					starts.
				</p>
				<div class="landing-public-link-list">
					<a href={aboutHref} onclick={() => onTrackCta('cta_click', 'trust', 'about')}
						>About / Team</a
					>
					<a href={statusHref} onclick={() => onTrackCta('cta_click', 'trust', 'status')}
						>Status Page</a
					>
				</div>
			</article>
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Enterprise review</p>
				<h3>Use enterprise review when it is needed</h3>
				<p>
					Security, privacy, residency, and procurement questions can be handled separately without
					slowing down a basic evaluation.
				</p>
				<div class="landing-public-link-list">
					<a
						href={trustEnterpriseHref}
						onclick={() => onTrackCta('cta_click', 'trust', 'enterprise')}
					>
						Enterprise Review
					</a>
					<a
						href={requestValidationBriefingHref}
						onclick={() => onTrackCta('cta_click', 'trust', 'validation_briefing')}
					>
						Request Validation Briefing
					</a>
				</div>
			</article>
		</div>
	</div>
</section>
