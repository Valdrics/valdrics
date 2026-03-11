<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';
	import { listPublicContent } from '$lib/content/publicContent';
	import {
		buildPublicEnterpriseHref,
		buildPublicSignupHref,
		resolvePublicBuyingMotion
	} from '$lib/public/publicBuyingMotion';

	const resources = listPublicContent('resources');
	let buyingMotion = $derived(resolvePublicBuyingMotion($page.url, 'self_serve_first'));
	let startFreeHref = $derived(
		buildPublicSignupHref(base, $page.url, {
			entry: 'resources',
			source: 'resource_hub'
		})
	);
	let enterprisePathHref = $derived(
		buildPublicEnterpriseHref(base, $page.url, {
			entry: 'resources',
			source: 'resource_hub'
		})
	);

	const heroHighlights = [
		{
			label: 'Playbooks',
			value: 'Weekly review, GreenOps, SaaS, and procurement-ready guidance'
		},
		{
			label: 'Downloads',
			value: 'Executive one-pager, ROI worksheet, and compliance checklist'
		},
		{
			label: 'Contact paths',
			value: 'Commercial, technical, security, privacy, and billing channels'
		}
	] as const;
</script>

<PublicPageMeta
	title="Resources"
	description="Valdrics resources: practical playbooks, templates, and guides for cloud, SaaS, license, and GreenOps cost control."
	pageType="CollectionPage"
	pageSection="Resources"
	keywords={['resources', 'downloads', 'greenops', 'saas governance', 'procurement']}
/>

<PublicMarketingPage
	kicker="Resource Hub"
	title="Resources"
	subtitle="Practical guidance for teams that want to reduce cloud and software waste without slowing delivery."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		{#if buyingMotion === 'enterprise_first'}
			<a href={enterprisePathHref} class="btn btn-primary">Open Enterprise Path</a>
			<a href={startFreeHref} class="btn btn-secondary">Start Free Workspace</a>
		{:else}
			<a href={startFreeHref} class="btn btn-primary">Start Free Workspace</a>
			<a href={enterprisePathHref} class="btn btn-secondary">See Enterprise Path</a>
		{/if}
		<a href={`${base}/insights`} class="btn btn-secondary">Open Insights</a>
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
		<section class="public-page__section" aria-labelledby="resources-library-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Library</p>
				<h2 id="resources-library-title" class="public-page__section-title">
					Use the right asset for the buying moment
				</h2>
				<p class="public-page__section-subtitle">
					Each asset is tuned for a specific stage: self-serve evaluation, team rollout alignment,
					or formal diligence.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--3">
				{#each resources as resource (resource.slug)}
					<article
						class={`public-page__card ${
							resource.slug === 'enterprise-governance-overview'
								? 'public-page__card--accent public-page__card--featured'
								: resource.slug === 'greenops-decision-framework'
									? 'public-page__card--dark'
									: resource.slug === 'executive-one-pager'
										? 'public-page__card--featured'
										: ''
						}`}
					>
						<p class="public-page__card-kicker">{resource.kicker}</p>
						<h2 class="public-page__card-title">{resource.title}</h2>
						<p class="public-page__card-copy">{resource.summary}</p>
						<div class="public-page__actions-row">
							<a href={`${base}/resources/${resource.slug}`} class="btn btn-secondary"
								>Open Resource</a
							>
						</div>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="resources-contact-title">
			<div class="public-page__band public-page__band--dark">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Contact Directory</p>
					<h2 id="resources-contact-title" class="public-page__section-title">Contact Directory</h2>
					<p class="public-page__section-subtitle">
						Use the right channel for commercial, technical, security, or compliance requests.
					</p>
				</div>
				<div class="public-page__badge-cloud">
					{#each PUBLIC_EXTENDED_CONTACT_CHANNELS as channel (channel.email)}
						<a
							href={channel.href}
							class="public-page__badge"
							aria-label={`${channel.label} contact ${channel.email}`}
						>
							{channel.label}: {channel.email}
						</a>
					{/each}
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
