<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import type { PublicContentEntry } from '$lib/content/publicContent.types';
	import {
		buildPublicEnterpriseHref,
		buildPublicSignupHref,
		resolvePublicBuyingMotion
	} from '$lib/public/publicBuyingMotion';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let buyingMotion = $derived(resolvePublicBuyingMotion($page.url, 'enterprise_first'));
	let startFreeHref = $derived(
		buildPublicSignupHref(base, $page.url, {
			entry: 'proof',
			source: 'proof_pack'
		})
	);
	let enterprisePathHref = $derived(
		buildPublicEnterpriseHref(base, $page.url, {
			entry: 'proof',
			source: 'proof_pack'
		})
	);

	const heroHighlights = [
		{
			label: 'What it covers',
			value: 'Control model, access, approvals, deployment boundaries, and validation scope'
		},
		{
			label: 'How to use it',
			value: 'Start here for evaluation, then move to docs only when deeper review is needed'
		},
		{
			label: 'What it avoids',
			value: 'No fake customer proof and no generic compliance claims'
		}
	] as const;

	const proofSequence = [
		{
			label: '01',
			title: 'Verify the control model',
			copy: 'Start with the access, approval, and record-integrity surfaces before you ask the buyer to trust a workflow.'
		},
		{
			label: '02',
			title: 'Pressure-test the risk questions',
			copy: 'Review validation scope, operational posture, and deployment boundaries where the public site can answer clearly.'
		},
		{
			label: '03',
			title: 'Go deeper only when needed',
			copy: 'Request a deeper enterprise review when the buyer needs deployment-specific or contract-specific answers.'
		}
	] as const;

	let proofSpotlights = $derived(data.proofSpotlights as PublicContentEntry[]);
</script>

<PublicPageMeta
	title="Proof Pack"
	description="Structured proof pack for Valdrics: control integrity, governance posture, deterministic execution, and operational resilience."
	pageType="WebPage"
	pageSection="Proof Pack"
	keywords={['proof pack', 'security', 'diligence', 'controls', 'technical validation']}
/>

<PublicMarketingPage
	kicker="Proof Pack"
	title="Proof surfaces for buyer diligence"
	subtitle="Review the control model, validation scope, and trust materials in the order serious buyers usually ask for them."
>
	{#snippet heroActions()}
		{#if buyingMotion === 'enterprise_first'}
			<a href={enterprisePathHref} class="btn btn-primary">Enterprise Review</a>
			<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
				Open Technical Validation
			</a>
			<a href={startFreeHref} class="btn btn-secondary">Start Free Workspace</a>
		{:else}
			<a href={startFreeHref} class="btn btn-primary">Start Free Workspace</a>
			<a href={enterprisePathHref} class="btn btn-secondary">Enterprise Review</a>
			<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
				Open Technical Validation
			</a>
		{/if}
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
		<section class="public-page__section" aria-labelledby="proof-sequence-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Review sequence</p>
				<h2 id="proof-sequence-title" class="public-page__section-title">
					Use the proof pack in the same order buyers do
				</h2>
				<p class="public-page__section-subtitle">
					This keeps the proof pack concrete instead of dumping every review topic on one screen.
				</p>
			</div>

			<div class="public-page__flow-grid public-page__flow-grid--3">
				{#each proofSequence as step (step.label)}
					<article class="public-page__flow-card">
						<p class="public-page__card-kicker">{step.label}</p>
						<h2 class="public-page__card-title">{step.title}</h2>
						<p class="public-page__card-copy">{step.copy}</p>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="proof-categories-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Proof categories</p>
				<h2 id="proof-categories-title" class="public-page__section-title">
					Review the evidence surface by buyer question
				</h2>
				<p class="public-page__section-subtitle">
					Each card below answers one recurring question from security, finance, leadership, or
					procurement.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--2">
				{#each proofSpotlights as entry (entry.slug)}
					<article
						class={`public-page__card ${
							entry.slug === 'identity-and-approval-controls'
								? 'public-page__card--accent public-page__card--featured'
								: entry.slug === 'deployment-and-data-residency'
									? 'public-page__card--featured'
									: ''
						}`}
					>
						<p class="public-page__card-kicker">{entry.kicker}</p>
						<h2 class="public-page__card-title">{entry.title}</h2>
						<p class="public-page__card-copy">{entry.summary}</p>
						<ul class="public-page__list public-page__list--compact">
							{#each entry.sections[0]?.bullets ?? [] as bullet (bullet)}
								<li>{bullet}</li>
							{/each}
						</ul>
						<a href={`${base}/proof/${entry.slug}`} class="btn btn-secondary">Open proof page</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section">
			<div class="public-page__band public-page__band--accent">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Next validation surfaces</p>
					<h2 class="public-page__section-title">Go deeper only when the review needs it</h2>
					<p class="public-page__section-subtitle">
						Documentation, API detail, and enterprise contact stay available without overwhelming
						the first proof surface.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={enterprisePathHref} class="btn btn-primary">Enterprise Review</a>
					<a href={`${base}/docs`} class="btn btn-secondary">Documentation</a>
					<a href={`${base}/docs/api`} class="btn btn-secondary">API Reference</a>
					<a href={startFreeHref} class="btn btn-secondary">Start Free Workspace</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
