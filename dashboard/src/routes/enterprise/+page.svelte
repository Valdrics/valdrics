<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import './enterprise-page.css';

	const enterpriseIntakeHref = `${base}/talk-to-sales?intent=enterprise_briefing&entry=enterprise`;
	const enterpriseMailHref =
		'mailto:enterprise@valdrics.com?cc=sales@valdrics.com&subject=Valdrics%20Enterprise%20Evaluation&body=Organization%20name%3A%0AStakeholders%3A%0ACloud%2FSaaS%20scope%3A%0ATarget%20timeline%3A';

	const governancePillars = [
		{
			title: 'Control Architecture',
			detail:
				'Map policy intent to owner-routed remediation, approval gates, and deterministic evidence exports.'
		},
		{
			title: 'Security Posture',
			detail:
				'Validate SCIM, deployment controls, role boundaries, audit trails, and evidence handling against internal security review criteria.'
		},
		{
			title: 'Commercial Readiness',
			detail:
				'Align procurement, legal, and finance stakeholders around rollout scope, responsibilities, and support model.'
		},
		{
			title: 'Operational Reliability',
			detail:
				'Confirm observability, rollback readiness, and failure-mode controls before production governance cutover.'
		}
	] as const;
</script>

<PublicPageMeta
	title="Enterprise Governance"
	description="Evaluate Valdrics enterprise governance readiness for cloud and software spend control, including security review, procurement diligence, and rollout operating model."
	pageType="WebPage"
	pageSection="Enterprise Governance"
	keywords={['enterprise', 'procurement', 'security review', 'governance', 'scim']}
/>

<div class="enterprise-shell">
	<div class="enterprise-bg-glow enterprise-bg-glow-a" aria-hidden="true"></div>
	<div class="enterprise-bg-glow enterprise-bg-glow-b" aria-hidden="true"></div>
	<div class="enterprise-bg-grid" aria-hidden="true"></div>
	<div class="enterprise-bg-aurora" aria-hidden="true"></div>
	<div class="enterprise-signal-field" aria-hidden="true">
		<div class="enterprise-signal-core">
			<CloudLogo provider="valdrics" size={176} />
		</div>
		<span class="enterprise-signal-ring enterprise-signal-ring-a"></span>
		<span class="enterprise-signal-ring enterprise-signal-ring-b"></span>
		<span class="enterprise-signal-ring enterprise-signal-ring-c"></span>
		<span class="enterprise-signal-line enterprise-signal-line-a"></span>
		<span class="enterprise-signal-line enterprise-signal-line-b"></span>
		<span class="enterprise-signal-line enterprise-signal-line-c"></span>
		<span class="enterprise-signal-node enterprise-signal-node-a"></span>
		<span class="enterprise-signal-node enterprise-signal-node-b"></span>
		<span class="enterprise-signal-node enterprise-signal-node-c"></span>
		<span class="enterprise-signal-node enterprise-signal-node-d"></span>
		<span class="enterprise-signal-node enterprise-signal-node-e"></span>
	</div>
	<div class="enterprise-logo-orbit enterprise-logo-orbit-a" aria-hidden="true">
		<CloudLogo provider="valdrics" size={104} />
	</div>
	<div class="enterprise-logo-orbit enterprise-logo-orbit-b" aria-hidden="true">
		<CloudLogo provider="valdrics" size={92} />
	</div>
	<div class="enterprise-logo-orbit enterprise-logo-orbit-c" aria-hidden="true">
		<CloudLogo provider="valdrics" size={80} />
	</div>

	<section class="enterprise-hero glass-panel">
		<p class="enterprise-kicker">Enterprise Governance Lane</p>
		<h1>Control cloud and software economics with procurement-grade confidence</h1>
		<p class="enterprise-hero-sub">
			Valdrics supports two buying paths: rapid self-serve activation for Starter, Growth, and Pro,
			and a formal enterprise diligence lane for security, risk, procurement, and executive review.
		</p>
		<div class="enterprise-hero-cta">
			<a href={enterpriseIntakeHref} class="btn btn-primary pulse-glow"
				>Request Enterprise Briefing</a
			>
			<a href={`${base}/talk-to-sales`} class="btn btn-secondary">Talk to Sales</a>
			<a href={`${base}/auth/login?intent=enterprise_preview`} class="btn btn-secondary"
				>Start Free Workspace</a
			>
		</div>
		<p class="enterprise-cta-note">
			Validation briefing is ungated. No login required. Prefer direct email?
			<a href={enterpriseMailHref}>enterprise@valdrics.com</a>
		</p>
		<div class="enterprise-metric-grid" aria-label="Enterprise readiness highlights">
			<article class="enterprise-metric-card">
				<p class="enterprise-metric-k">Validation Scope</p>
				<p class="enterprise-metric-v">Security + Finance + Platform</p>
			</article>
			<article class="enterprise-metric-card">
				<p class="enterprise-metric-k">Operating Model</p>
				<p class="enterprise-metric-v">Owner-routed controls with approvals</p>
			</article>
			<article class="enterprise-metric-card">
				<p class="enterprise-metric-k">Evidence Surface</p>
				<p class="enterprise-metric-v">Audit-ready exports and control traces</p>
			</article>
		</div>
	</section>

	<section class="enterprise-section">
		<div class="enterprise-section-head">
			<p class="enterprise-kicker">Control Stack</p>
			<h2>Enterprise-critical control pillars</h2>
		</div>
		<div class="enterprise-pillar-grid">
			{#each governancePillars as pillar (pillar.title)}
				<article class="enterprise-pillar-card glass-panel">
					<h3>{pillar.title}</h3>
					<p>{pillar.detail}</p>
				</article>
			{/each}
		</div>
	</section>

	<section class="enterprise-section enterprise-track-grid">
		<article class="glass-panel enterprise-track-card">
			<p class="enterprise-kicker">Self-Serve Track</p>
			<h3>Starter, Growth, and Pro teams</h3>
			<ul>
				<li>Launch quickly with plan-based controls and guided onboarding.</li>
				<li>Run ROI and remediation loops directly in your workspace.</li>
				<li>Expand governance depth as teams and spend surface grow.</li>
			</ul>
			<a href={`${base}/pricing`} class="btn btn-secondary">View Plans</a>
		</article>
		<article class="glass-panel enterprise-track-card enterprise-track-card-featured">
			<p class="enterprise-kicker">Enterprise Track</p>
			<h3>Formal diligence and procurement workflows</h3>
			<ul>
				<li>Coordinate security, legal, procurement, and finance sign-off.</li>
				<li>
					Review governance artifacts, SCIM, and deployment controls before full production
					activation.
				</li>
				<li>Operate a staged rollout with explicit control checkpoints.</li>
			</ul>
			<a href={enterpriseIntakeHref} class="btn btn-primary">Open Enterprise Intake</a>
		</article>
	</section>

	<section class="enterprise-section glass-panel enterprise-proof-card">
		<div class="enterprise-proof-copy">
			<p class="enterprise-kicker">Procurement Readiness Pack</p>
			<h2>Use externally framed diligence artifacts</h2>
			<p>
				Package your internal review quickly with buyer-facing artifacts covering governance
				controls, access posture, rollout risk, and commercial readiness assumptions.
			</p>
		</div>
		<div class="enterprise-proof-actions">
			<a href={`${base}/resources/valdrics-enterprise-one-pager.md`} class="btn btn-secondary">
				Download Executive One-Pager
			</a>
			<a href={`${base}/resources/global-finops-compliance-workbook.md`} class="btn btn-secondary">
				Download Compliance Checklist
			</a>
			<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
				Open Technical Validation
			</a>
		</div>
	</section>
</div>
