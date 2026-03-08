<script lang="ts">
	import { base } from '$app/paths';
	import { COMPLIANCE_FOUNDATION_BADGES, EXECUTIVE_CONFIDENCE_POINTS } from '$lib/landing/heroContent';

	let {
		onTrackCta,
		requestValidationBriefingHref,
		onePagerHref,
		globalComplianceWorkbookHref = `${base}/resources/global-finops-compliance-workbook.md`
	}: {
		onTrackCta: (
			value:
				| 'request_validation_briefing'
				| 'download_executive_one_pager'
				| 'download_global_compliance_workbook'
		) => void;
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
		<h2 class="landing-h2">Security and Readiness</h2>
		<p class="landing-section-sub">
			Security essentials and a clear enterprise handoff when review is required.
		</p>
	</div>

	<div class="landing-validation-cta glass-panel" aria-label="Security and Readiness">
		<p class="landing-proof-k">Need formal review?</p>
		<p class="landing-p">
			Use the enterprise path when procurement, security review, or rollout planning is part of
			the buying process.
		</p>
		<div class="landing-lead-actions">
			<a
				href={requestValidationBriefingHref}
				class="btn btn-primary w-fit pulse-glow"
				onclick={() => onTrackCta('request_validation_briefing')}
			>
				Talk to Sales
			</a>
			<a
				href={onePagerHref}
				class="btn btn-secondary w-fit"
				onclick={() => onTrackCta('download_executive_one_pager')}
			>
				Download Executive One-Pager
			</a>
		</div>
		<p class="landing-more-resources">
			Also see:
			<a href={`${base}/enterprise`}>Enterprise Governance Overview</a>
			•
			<a
				href={globalComplianceWorkbookHref}
				onclick={() => onTrackCta('download_global_compliance_workbook')}
			>
				Access Control & Compliance Checklist
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
		<p class="landing-proof-k">Security essentials</p>
		<div class="landing-trust-badges">
			{#each COMPLIANCE_FOUNDATION_BADGES as badge (badge)}
				<span
					class="landing-trust-badge {badge.includes('ISO 27001') || badge.includes('DORA')
						? 'is-featured'
						: ''}">{badge}</span
				>
			{/each}
		</div>
	</div>
</section>
