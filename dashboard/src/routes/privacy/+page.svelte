<script lang="ts">
	import { base } from '$app/paths';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
</script>

<PublicPageMeta
	title="Privacy Policy"
	description="Valdrics privacy policy covering processing scope, retention, security controls, and data subject rights for cloud and software spend governance workflows."
	pageType="WebPage"
	pageSection="Privacy"
	keywords={['privacy policy', 'data retention', 'data subject rights', 'security controls']}
/>

<article class="mx-auto max-w-4xl px-6 py-12 space-y-8">
	<header class="space-y-3">
		<h1 class="text-3xl font-semibold text-ink-100">Privacy Policy</h1>
		<p class="text-sm text-ink-400">Last updated: March 1, 2026</p>
		<p class="text-sm text-ink-300">
			This policy explains how Valdrics collects, processes, stores, and protects personal and
			organization data when you use our cloud and software spend governance platform.
		</p>
	</header>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">1. Data We Collect</h2>
		<ul class="list-disc pl-5 text-sm text-ink-300 space-y-2">
			<li>Account identity data such as name, work email, and role.</li>
			<li>Tenant metadata such as workspace identifiers, plan, and ownership mappings.</li>
			<li>
				Usage, telemetry, and governance events required to provide anomaly detection, approvals,
				and audit trails.
			</li>
			<li>
				Optional marketing lead information submitted through public forms (for example, newsletter
				signup).
			</li>
		</ul>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">2. Why We Process Data</h2>
		<ul class="list-disc pl-5 text-sm text-ink-300 space-y-2">
			<li>Deliver platform functionality, including routing, approvals, and reporting.</li>
			<li>Secure the service, detect abuse, and maintain operational reliability.</li>
			<li>Provide customer support, incident response, and service communications.</li>
			<li>Improve product quality through bounded analytics and controlled experimentation.</li>
		</ul>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">3. Legal Bases (GDPR)</h2>
		<p class="text-sm text-ink-300">
			Where GDPR applies, Valdrics processes data under one or more of: contract performance,
			legitimate interests, legal obligations, and consent (for optional analytics/marketing where
			required).
		</p>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">4. Data Retention</h2>
		<p class="text-sm text-ink-300">
			We retain customer data only as long as needed for contractual service delivery, security
			requirements, and legal obligations. Operational logs and telemetry are retained according to
			documented service retention schedules and deleted or anonymized when no longer required.
		</p>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">5. Sharing and Sub-processors</h2>
		<p class="text-sm text-ink-300">
			We use vetted infrastructure and service providers to operate the platform. Sub-processors are
			bound by contractual confidentiality and security obligations. We do not sell customer
			personal data.
		</p>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">6. Security Controls</h2>
		<ul class="list-disc pl-5 text-sm text-ink-300 space-y-2">
			<li>Encryption in transit and encryption at rest for managed data stores.</li>
			<li>Tenant isolation controls and role-scoped access.</li>
			<li>Audit logging, approval lineage, and incident response procedures.</li>
			<li>Security monitoring and access review processes.</li>
		</ul>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">7. Data Subject Rights</h2>
		<p class="text-sm text-ink-300">
			Subject to applicable law, you may request access, correction, deletion, restriction,
			portability, or objection to processing. Enterprise customers may also request Data Processing
			Addendum (DPA) documentation and support for rights requests through designated workspace
			administrators.
		</p>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">8. Cookies and Local Storage</h2>
		<p class="text-sm text-ink-300">
			Our public landing experience uses optional analytics and experiment telemetry in local
			storage. Visitors can accept or decline analytics tracking through the cookie preferences
			prompt.
		</p>
	</section>

	<section class="space-y-3">
		<h2 class="text-xl font-semibold">9. Contact</h2>
		<p class="text-sm text-ink-300">
			For privacy, DPA, or deletion requests, contact <a
				class="underline"
				href="mailto:privacy@valdrics.com">privacy@valdrics.com</a
			>. General support requests can go to
			<a class="underline" href="mailto:support@valdrics.com">support@valdrics.com</a>. For
			security-related disclosure or incident coordination, contact
			<a class="underline" href="mailto:security@valdrics.com">security@valdrics.com</a>.
		</p>
	</section>

	<section class="space-y-3 rounded-3xl border border-white/10 bg-white/5 p-6">
		<h2 class="text-xl font-semibold">10. Enterprise Privacy Review Path</h2>
		<p class="text-sm text-ink-300">
			Public privacy materials are meant to answer the first diligence questions without inventing a
			universal deployment or processor answer. DPA requests, sub-processor review, and
			residency-specific questions move into the enterprise/legal lane when a buyer needs scoped
			answers.
		</p>
		<ul class="list-disc pl-5 text-sm text-ink-300 space-y-2">
			<li>DPA and privacy review requests route through privacy and legal contacts.</li>
			<li>Residency-specific and deployment-specific questions route through enterprise review.</li>
			<li>Security disclosure and incident coordination stay on the security contact path.</li>
		</ul>
		<div class="flex flex-wrap gap-3 pt-2">
			<a class="btn btn-secondary" href={`${base}/proof/deployment-and-data-residency`}>
				Deployment and Residency Proof
			</a>
			<a class="btn btn-secondary" href={`${base}/enterprise`}> Enterprise Review Path </a>
			<a class="btn btn-secondary" href={`${base}/talk-to-sales`}> Talk to Sales </a>
		</div>
	</section>
</article>
