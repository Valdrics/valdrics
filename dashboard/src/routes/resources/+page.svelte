<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import type { PublicContentEntry } from '$lib/content/publicContent.types';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';
	import {
		buildPublicEnterpriseHref,
		buildPublicSignupHref,
		resolvePublicBuyingMotion
	} from '$lib/public/publicBuyingMotion';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
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
			label: 'Start the case',
			value: 'Executive one-pager, ROI worksheet, and enterprise overview'
		},
		{
			label: 'Run the loop',
			value: 'Weekly review, GreenOps, and SaaS governance playbooks'
		},
		{
			label: 'Escalate cleanly',
			value: 'Public contacts for commercial, security, privacy, and billing questions'
		}
	] as const;

	let guidedPaths = $derived(
		data.guidedPaths as Array<{
			kicker: string;
			title: string;
			copy: string;
			entries: PublicContentEntry[];
		}>
	);
	let stageColumns = $derived(
		data.stageColumns as Array<{
			label: string;
			title: string;
			copy: string;
			entries: PublicContentEntry[];
		}>
	);
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
	title="Resources for rollout, review, and diligence"
	subtitle="Use the right asset for the job: start the internal case, tighten the weekly operating loop, or prepare for buyer review without dumping people into internal product detail."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		{#if buyingMotion === 'enterprise_first'}
			<a href={enterprisePathHref} class="btn btn-primary">Enterprise Review</a>
			<a href={startFreeHref} class="btn btn-secondary">Start Free Workspace</a>
		{:else}
			<a href={startFreeHref} class="btn btn-primary">Start Free Workspace</a>
			<a href={enterprisePathHref} class="btn btn-secondary">Enterprise Review</a>
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
		<section class="public-page__section" aria-labelledby="resources-paths-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Guided paths</p>
				<h2 id="resources-paths-title" class="public-page__section-title">
					Start with the asset that matches the real task
				</h2>
				<p class="public-page__section-subtitle">
					Most teams do not need the whole library at once. Start with the path that fits the
					current conversation.
				</p>
			</div>

			<div class="public-page__flow-grid public-page__flow-grid--3">
				{#each guidedPaths as path (path.title)}
					<article class="public-page__flow-card">
						<p class="public-page__card-kicker">{path.kicker}</p>
						<h2 class="public-page__card-title">{path.title}</h2>
						<p class="public-page__card-copy">{path.copy}</p>
						<div class="public-page__mini-list">
							{#each path.entries as entry (entry.slug)}
								<a href={`${base}/resources/${entry.slug}`} class="public-page__mini-link">
									<span>{entry.title}</span>
									<small>{entry.readingMinutes} min</small>
								</a>
							{/each}
						</div>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="resources-library-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Library</p>
				<h2 id="resources-library-title" class="public-page__section-title">
					Scan the library by decision stage
				</h2>
				<p class="public-page__section-subtitle">
					Each column below maps to a different moment: operating education, buyer evaluation, or
					final validation.
				</p>
			</div>

			<div class="public-page__stage-grid">
				{#each stageColumns as stage (stage.label)}
					<article class="public-page__stage-card">
						<p class="public-page__card-kicker">{stage.label}</p>
						<h2 class="public-page__card-title">{stage.title}</h2>
						<p class="public-page__card-copy">{stage.copy}</p>
						<div class="public-page__stack">
							{#each stage.entries as resource (resource.slug)}
								<a href={`${base}/resources/${resource.slug}`} class="public-page__list-card">
									<strong>{resource.title}</strong>
									<span>{resource.summary}</span>
								</a>
							{/each}
						</div>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="resources-contact-title">
			<div class="public-page__band">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Contact Directory</p>
					<h2 id="resources-contact-title" class="public-page__section-title">Contact Directory</h2>
					<p class="public-page__section-subtitle">
						Use the right channel for commercial, technical, security, privacy, or billing requests
						without digging through the footer.
					</p>
				</div>
				<div class="public-page__badge-cloud">
					{#each PUBLIC_EXTENDED_CONTACT_CHANNELS as channel (channel.email)}
						<a
							href={channel.href}
							class="public-page__badge"
							aria-label={`${channel.label} contact ${channel.email}`}
						>
							{channel.email}
						</a>
					{/each}
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
