<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import {
		appendPublicAttribution,
		buildPublicSalesHref,
		buildPublicSignupHref
	} from '$lib/public/publicBuyingMotion';

	let enterpriseIntakeHref = $derived(
		buildPublicSalesHref(base, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_lane',
			intent: 'enterprise_briefing'
		})
	);
	let enterpriseStartFreeHref = $derived(
		buildPublicSignupHref(base, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_workspace_preview'
		})
	);
	let enterprisePricingHref = $derived(
		appendPublicAttribution(`${base}/pricing`, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_pricing'
		})
	);
	let enterpriseProofHref = $derived(
		appendPublicAttribution(`${base}/proof`, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_proof'
		})
	);
	let enterprisePrivacyHref = $derived(
		appendPublicAttribution(`${base}/privacy`, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_privacy'
		})
	);
	let enterpriseTermsHref = $derived(
		appendPublicAttribution(`${base}/terms`, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_terms'
		})
	);
	let enterpriseStatusHref = $derived(
		appendPublicAttribution(`${base}/status`, $page.url, {
			entry: 'enterprise',
			source: 'enterprise_status'
		})
	);

	const enterpriseMailHref =
		'mailto:enterprise@valdrics.com?cc=sales@valdrics.com&subject=Valdrics%20Enterprise%20Evaluation&body=Organization%20name%3A%0AStakeholders%3A%0ACloud%2FSaaS%20scope%3A%0ATarget%20timeline%3A';

	const heroHighlights = [
		{ label: 'Best fit', value: 'Teams with formal security, privacy, or procurement review' },
		{
			label: 'Review path',
			value: 'Pricing, proof, and enterprise contact are available in one place'
		},
		{
			label: 'Public materials',
			value: 'Proof pack, privacy, terms, and live status available upfront'
		}
	] as const;

	let reviewCards = $derived([
		{
			title: 'Security and access review',
			detail:
				'Open the control, access, and validation materials security reviewers usually ask for first.',
			ctaLabel: 'Open Proof Pack',
			href: enterpriseProofHref
		},
		{
			title: 'Privacy and deployment review',
			detail:
				'Keep privacy, DPA, and deployment questions on one clear path instead of scattered follow-up threads.',
			ctaLabel: 'Review Privacy Posture',
			href: enterprisePrivacyHref
		},
		{
			title: 'Commercial and legal review',
			detail:
				'Give buyers a direct route to pricing context, legal terms, and commercial follow-up when they need it.',
			ctaLabel: 'Review Terms',
			href: enterpriseTermsHref
		}
	]);

	let buyingPaths = $derived([
		{
			kicker: 'Start quickly',
			title: 'Start with pricing and workspace access',
			detail:
				'Use this path when the team can evaluate the product directly without a separate review track.',
			ctaLabel: 'View Pricing',
			href: enterprisePricingHref
		},
		{
			kicker: 'Need a formal review',
			title: 'Request an enterprise briefing',
			detail:
				'Use this path when procurement, privacy, deployment, or legal requirements need a dedicated review process.',
			ctaLabel: 'Request Enterprise Briefing',
			href: enterpriseIntakeHref
		}
	]);

	let diligenceLinks = $derived([
		{ label: 'Executive One-Pager', href: `${base}/resources/valdrics-enterprise-one-pager.md` },
		{
			label: 'Compliance Checklist',
			href: `${base}/resources/global-finops-compliance-workbook.md`
		},
		{ label: 'Technical Validation', href: `${base}/docs/technical-validation` },
		{ label: 'System Status', href: enterpriseStatusHref }
	]);
</script>

<PublicPageMeta
	title="Enterprise Governance"
	description="Evaluate Valdrics for enterprise rollout with clear paths for security review, privacy questions, procurement, and commercial follow-up."
	pageType="WebPage"
	pageSection="Enterprise Governance"
	keywords={['enterprise', 'procurement', 'security review', 'privacy', 'governance']}
/>

<PublicMarketingPage
	kicker="Enterprise"
	title="Enterprise review that stays clear"
	subtitle="Valdrics keeps enterprise review simple: open the right materials quickly, let teams start directly when they can, and offer a formal briefing when rollout requirements expand."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={enterpriseIntakeHref} class="btn btn-primary">Request Enterprise Briefing</a>
		<a href={enterpriseStartFreeHref} class="btn btn-secondary">Start Free Workspace</a>
		<a href={enterprisePricingHref} class="btn btn-secondary">View Pricing</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each heroHighlights as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		<section class="public-page__section" aria-labelledby="enterprise-review-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Review essentials</p>
				<h2 id="enterprise-review-title" class="public-page__section-title">
					Give legal, security, and procurement teams a coherent next step
				</h2>
				<p class="public-page__section-subtitle">
					Open the right review surface quickly instead of sending buyers through scattered pages
					and follow-up emails.
				</p>
			</div>
			<div class="public-page__grid public-page__grid--3">
				{#each reviewCards as track (track.title)}
					<article class="public-page__card">
						<h3 class="public-page__card-title">{track.title}</h3>
						<p class="public-page__card-copy">{track.detail}</p>
						<a href={track.href} class="btn btn-secondary">{track.ctaLabel}</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="enterprise-paths-title">
			<div class="public-page__band public-page__band--accent">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Choose the right path</p>
					<h2 id="enterprise-paths-title" class="public-page__section-title">
						Choose the path that matches the buying process
					</h2>
					<p class="public-page__section-subtitle">
						Some teams can start with pricing and product access. Others need a formal review before
						rollout.
					</p>
				</div>
				<div class="public-page__grid public-page__grid--2">
					{#each buyingPaths as path (path.title)}
						<article class="public-page__card">
							<p class="public-page__card-kicker">{path.kicker}</p>
							<h3 class="public-page__card-title">{path.title}</h3>
							<p class="public-page__card-copy">{path.detail}</p>
							<a href={path.href} class="btn btn-secondary">{path.ctaLabel}</a>
						</article>
					{/each}
				</div>
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="enterprise-assets-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Diligence materials</p>
				<h2 id="enterprise-assets-title" class="public-page__section-title">
					Open the first materials buyers usually ask for
				</h2>
			</div>
			<div class="public-page__grid public-page__grid--2">
				{#each diligenceLinks as item (item.label)}
					<a class="public-page__card public-page__card--featured" href={item.href}>
						<h3 class="public-page__card-title">{item.label}</h3>
						<p class="public-page__card-copy">Open the relevant review artifact directly.</p>
					</a>
				{/each}
			</div>
			<p class="public-page__inline-note">
				Prefer direct email? <a href={enterpriseMailHref}>enterprise@valdrics.com</a>
			</p>
		</section>
	{/snippet}
</PublicMarketingPage>
