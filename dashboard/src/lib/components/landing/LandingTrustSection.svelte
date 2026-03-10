<script lang="ts">
	import { base } from '$app/paths';
	import {
		COMPLIANCE_FOUNDATION_BADGES,
		EXECUTIVE_CONFIDENCE_POINTS
	} from '$lib/landing/heroContent';

	let {
		onTrackCta,
		enterprisePathHref,
		requestValidationBriefingHref,
		onePagerHref,
		globalComplianceWorkbookHref = `${base}/resources/global-finops-compliance-workbook.md`
	}: {
		onTrackCta: (
			value:
				| 'enterprise_review'
				| 'request_validation_briefing'
				| 'download_executive_one_pager'
				| 'download_global_compliance_workbook'
		) => void;
		enterprisePathHref: string;
		requestValidationBriefingHref: string;
		onePagerHref: string;
		globalComplianceWorkbookHref?: string;
	} = $props();
</script>

<section
	id="trust"
	class="container mx-auto px-6 pb-16 landing-section-lazy"
	data-landing-section="proof"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">Security proof and enterprise rollout</h2>
		<p class="landing-section-sub">
			Concrete control evidence, buyer-ready materials, and a clear handoff for procurement,
			security, and rollout review.
		</p>
	</div>

	<div
		class="landing-validation-cta glass-panel"
		aria-label="Security proof and enterprise rollout"
	>
		<p class="landing-proof-k">Formal evaluation lane</p>
		<p class="landing-p">
			Use the enterprise path when architecture review, rollout planning, procurement, or security
			validation needs a dedicated diligence track. Self-serve teams can keep moving in the
			workspace path above.
		</p>
		<div class="landing-lead-actions">
			<a
				href={enterprisePathHref}
				class="btn btn-primary w-fit pulse-glow"
				onclick={() => onTrackCta('enterprise_review')}
			>
				Open Enterprise Path
			</a>
			<a
				href={requestValidationBriefingHref}
				class="btn btn-secondary w-fit"
				onclick={() => onTrackCta('request_validation_briefing')}
			>
				Book Validation Briefing
			</a>
		</div>
		<p class="landing-more-resources">
			Also see:
			<a href={onePagerHref} onclick={() => onTrackCta('download_executive_one_pager')}
				>Download Executive One-Pager</a
			>
			•
			<a
				href={globalComplianceWorkbookHref}
				onclick={() => onTrackCta('download_global_compliance_workbook')}
			>
				Control and Access Checklist
			</a>
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

	<div class="landing-compliance-block">
		<p class="landing-proof-k">Control foundations</p>
		<div class="landing-trust-badges">
			{#each COMPLIANCE_FOUNDATION_BADGES as badge (badge)}
				<span class="landing-trust-badge {badge.includes('Decision history') ? 'is-featured' : ''}"
					>{badge}</span
				>
			{/each}
		</div>
	</div>
</section>
