<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import {
		PUBLIC_DEPLOYMENT_RESIDENCY_FACTS,
		PUBLIC_TEAM_MEMBERS
	} from '$lib/content/publicCompany';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';
	import { appendPublicAttribution, buildPublicSignupHref } from '$lib/public/publicBuyingMotion';

	let startFreeHref = $derived(
		buildPublicSignupHref(base, $page.url, {
			entry: 'about',
			source: 'about_page'
		})
	);
	let proofHref = $derived(
		appendPublicAttribution(`${base}/proof`, $page.url, {
			entry: 'about',
			source: 'about_proof'
		})
	);
	let docsHref = $derived(
		appendPublicAttribution(`${base}/docs`, $page.url, {
			entry: 'about',
			source: 'about_docs'
		})
	);
	let enterpriseHref = $derived(
		appendPublicAttribution(`${base}/enterprise`, $page.url, {
			entry: 'about',
			source: 'about_enterprise'
		})
	);
	let salesHref = $derived(
		appendPublicAttribution(`${base}/talk-to-sales`, $page.url, {
			entry: 'about',
			source: 'about_sales'
		})
	);

	const founder = PUBLIC_TEAM_MEMBERS[0];
	const deploymentFact = PUBLIC_DEPLOYMENT_RESIDENCY_FACTS[0];
	const coreContacts = PUBLIC_EXTENDED_CONTACT_CHANNELS.filter((channel) =>
		['Enterprise', 'Sales', 'Security', 'Legal', 'Privacy'].includes(channel.label)
	);

	const heroSummaryItems = [
		{ label: 'Company stage', value: 'Founder-led and publicly reviewable' },
		{
			label: 'Public review',
			value: 'Proof, docs, and enterprise diligence available upfront'
		},
		{ label: 'Evaluation style', value: 'Proof pack first, enterprise lane when needed' }
	] as const;

	const originCards = [
		{
			title: 'Why this company exists',
			detail:
				'Most teams can already see spend problems. The harder part is turning the alert into one accountable action path with approvals and proof.'
		},
		{
			title: 'What the public site should do',
			detail:
				'The public site should help buyers understand the company, the workflow, the pricing posture, and the review path without dumping internal product details on every page.'
		}
	] as const;

	let reviewLinks = $derived([
		{
			label: 'Proof Pack',
			href: proofHref,
			note: 'Security posture, controls, and validation scope.'
		},
		{
			label: 'Docs',
			href: docsHref,
			note: 'Technical validation, onboarding, and rollout guidance.'
		},
		{
			label: 'Enterprise Path',
			href: enterpriseHref,
			note: 'Formal review lane for procurement, residency, and rollout governance.'
		}
	]);
</script>

<PublicPageMeta
	title="About Valdrics"
	description="Meet the team behind Valdrics and review the proof, documentation, and enterprise evaluation surfaces."
	pageType="WebPage"
	pageSection="About"
	keywords={['about valdrics', 'founder', 'company', 'proof pack', 'security review']}
/>

<PublicMarketingPage
	kicker="About Valdrics"
	title="Meet the team behind Valdrics"
	subtitle="Valdrics is building a calmer operating layer for spend governance. Buyers should be able to see who we are, what we believe, and how to evaluate the product before any sales loop starts."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={startFreeHref} class="btn btn-primary">Start Free Workspace</a>
		<a href={proofHref} class="btn btn-secondary">Open Proof Pack</a>
		<a href={salesHref} class="btn btn-secondary">Talk to Sales</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each heroSummaryItems as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		<section class="public-page__section" aria-labelledby="about-origin-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Company</p>
				<h2 id="about-origin-title" class="public-page__section-title">Why Valdrics exists</h2>
			</div>
			<div class="public-page__grid public-page__grid--2">
				{#each originCards as card (card.title)}
					<article class="public-page__card">
						<h3 class="public-page__card-title">{card.title}</h3>
						<p class="public-page__card-copy">{card.detail}</p>
					</article>
				{/each}
				{#if founder}
					<article class="public-page__card public-page__card--featured">
						<p class="public-page__card-kicker">Founder</p>
						<h3 class="public-page__card-title">{founder.name}</h3>
						<p class="public-page__inline-note"><strong>{founder.role}</strong></p>
						<p class="public-page__card-copy">{founder.shortBio}</p>
					</article>
				{/if}
			</div>
			<p class="public-page__inline-note">
				Valdrics supports buyer evaluations across multiple regions. Deployment, residency, and
				procurement requirements that vary by region move through the enterprise review path.
			</p>
		</section>

		<section class="public-page__section" aria-labelledby="about-review-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Review path</p>
				<h2 id="about-review-title" class="public-page__section-title">
					How buyers can evaluate Valdrics before rollout
				</h2>
			</div>
			<div class="public-page__grid public-page__grid--3">
				{#each reviewLinks as link (link.label)}
					<article class="public-page__card">
						<h3 class="public-page__card-title">{link.label}</h3>
						<p class="public-page__card-copy">{link.note}</p>
						<a href={link.href} class="btn btn-secondary">Open {link.label}</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="about-contact-title">
			<div class="public-page__grid public-page__grid--2">
				<article class="public-page__card">
					<p class="public-page__eyebrow">Deployment stance</p>
					<h2 id="about-contact-title" class="public-page__section-title">
						Deployment claims stay factual
					</h2>
					<p class="public-page__card-copy">{deploymentFact?.answer}</p>
					<div class="public-page__actions-row">
						<a href={enterpriseHref} class="btn btn-secondary">Open Enterprise Path</a>
						<a href={docsHref} class="btn btn-secondary">Open Docs</a>
					</div>
				</article>
				<article class="public-page__card">
					<p class="public-page__eyebrow">Contact</p>
					<h2 class="public-page__section-title">Public contact surface</h2>
					<div class="public-page__badge-cloud">
						{#each coreContacts as channel (channel.email)}
							<a
								href={channel.href}
								class="public-page__badge"
								aria-label={`${channel.label} contact ${channel.email}`}
							>
								{channel.label}: {channel.email}
							</a>
						{/each}
					</div>
				</article>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
