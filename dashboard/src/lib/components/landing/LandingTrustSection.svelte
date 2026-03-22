<script lang="ts">
	import { base } from '$app/paths';
	import {
		COMPLIANCE_FOUNDATION_BADGES,
		EXECUTIVE_CONFIDENCE_POINTS
	} from '$lib/landing/heroContent';

	let {
		onTrackCta,
		enterprisePathHref,
		aboutHref,
		docsHref,
		statusHref,
		proofHref = '/proof',
		requestValidationBriefingHref,
		onePagerHref,
		globalComplianceWorkbookHref = `${base}/resources/global-finops-compliance-workbook.md`
	}: {
		onTrackCta: (
			value:
				| 'about_review'
				| 'docs_review'
				| 'status_review'
				| 'proof_review'
				| 'enterprise_review'
				| 'request_validation_briefing'
				| 'download_executive_one_pager'
				| 'download_global_compliance_workbook'
				| 'deployment_residency_review'
		) => void;
		enterprisePathHref: string;
		aboutHref: string;
		docsHref: string;
		statusHref: string;
		proofHref?: string;
		requestValidationBriefingHref: string;
		onePagerHref: string;
		globalComplianceWorkbookHref?: string;
	} = $props();

	const deploymentResidencyHref = `${base}/proof/deployment-and-data-residency`;
	const executiveConfidence = EXECUTIVE_CONFIDENCE_POINTS.slice(0, 3);
</script>

<section
	id="trust"
	class="container mx-auto px-6 pb-16 landing-section-lazy"
	data-landing-section="proof"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">Proof, review surfaces, and rollout clarity</h2>
		<p class="landing-section-sub">
			Public proof should reduce uncertainty without inventing customer evidence. Valdrics exposes
			buyer-safe materials for security, rollout, procurement, and executive review.
		</p>
	</div>

	<div class="landing-proof-state-grid">
		<article class="glass-panel landing-proof-state-card">
			<p class="landing-proof-k">Proof pack</p>
			<h3 class="landing-h3">Start with materials you can inspect without a sales call</h3>
			<p class="landing-p">
				Review access posture, approval controls, decision-history integrity, and the current
				validation scope before broader diligence starts.
			</p>
			<div class="landing-proof-state-links">
				<a href={proofHref} class="landing-cta-link" onclick={() => onTrackCta('proof_review')}>
					Open Proof Pack
				</a>
				<a
					href={onePagerHref}
					class="landing-cta-link"
					onclick={() => onTrackCta('download_executive_one_pager')}
				>
					Download Executive One-Pager
				</a>
			</div>
		</article>

		<article class="glass-panel landing-proof-state-card">
			<p class="landing-proof-k">Security and access review</p>
			<h3 class="landing-h3">Review how control, access, and evidence fit together</h3>
			<p class="landing-p">
				The public docs and proof pages explain the first diligence lane without pretending a
				generic marketing claim replaces environment-specific review.
			</p>
			<div class="landing-proof-state-links">
				<a href={docsHref} class="landing-cta-link" onclick={() => onTrackCta('docs_review')}>
					Open Docs
				</a>
				<a
					href={globalComplianceWorkbookHref}
					class="landing-cta-link"
					onclick={() => onTrackCta('download_global_compliance_workbook')}
				>
					Control and Access Checklist
				</a>
			</div>
		</article>

		<article class="glass-panel landing-proof-state-card">
			<p class="landing-proof-k">Deployment and data residency review</p>
			<h3 class="landing-h3">Answer region and residency questions factually</h3>
			<p class="landing-p">
				Use the deployment-residency review note when buyers ask where public materials stop and
				enterprise evaluation begins.
			</p>
			<div class="landing-proof-state-links">
				<a
					href={deploymentResidencyHref}
					class="landing-cta-link"
					onclick={() => onTrackCta('deployment_residency_review')}
				>
					Open Deployment Review
				</a>
				<a href={statusHref} class="landing-cta-link" onclick={() => onTrackCta('status_review')}>
					View Status
				</a>
			</div>
		</article>

		<article class="glass-panel landing-proof-state-card">
			<p class="landing-proof-k">Enterprise validation lane</p>
			<h3 class="landing-h3">Use the formal path only when diligence actually needs it</h3>
			<p class="landing-p">
				Self-serve teams can start in the workspace path. Procurement, architecture review, and
				security review can move into a dedicated enterprise lane without restarting the
				conversation.
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
		</article>
	</div>

	<div class="landing-evidence-grid">
		{#each executiveConfidence as point (point.title)}
			<article class="glass-panel landing-evidence-card">
				<p class="landing-proof-k">{point.kicker}</p>
				<h3 class="landing-h3">{point.title}</h3>
				<p class="landing-p">{point.detail}</p>
			</article>
		{/each}
	</div>

	<div class="landing-proof-footnote glass-panel">
		<div>
			<p class="landing-proof-k">Company and review surface</p>
			<h3 class="landing-h3">Verify the company and review materials directly</h3>
			<p class="landing-p">
				Valdrics does not publish customer logos or case studies yet. Public trust comes from
				transparent pricing, docs, proof materials, status visibility, and direct company review.
			</p>
		</div>
		<div class="landing-proof-state-links">
			<a href={aboutHref} class="landing-cta-link" onclick={() => onTrackCta('about_review')}>
				About / Team
			</a>
			<a href={docsHref} class="landing-cta-link" onclick={() => onTrackCta('docs_review')}>
				Open Docs
			</a>
			<a href={statusHref} class="landing-cta-link" onclick={() => onTrackCta('status_review')}>
				View Status
			</a>
		</div>
	</div>

	<div class="landing-compliance-block">
		<p class="landing-proof-k">Control foundations</p>
		<div class="landing-trust-badges">
			{#each COMPLIANCE_FOUNDATION_BADGES as badge (badge)}
				<span class="landing-trust-badge {badge.includes('Decision history') ? 'is-featured' : ''}">
					{badge}
				</span>
			{/each}
		</div>
	</div>
</section>
