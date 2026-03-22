<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';
	import { listPublicContent, type PublicContentEntry } from '$lib/content/publicContent';
	import {
		buildPublicEnterpriseHref,
		buildPublicSignupHref,
		resolvePublicBuyingMotion
	} from '$lib/public/publicBuyingMotion';

	const resources = listPublicContent('resources');
	const resourcesBySlug = new Map(resources.map((resource) => [resource.slug, resource] as const));
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

	function mustGetResource(slug: string): PublicContentEntry {
		const resource = resourcesBySlug.get(slug);
		if (!resource) {
			throw new Error(`Unknown resource entry: ${slug}`);
		}
		return resource;
	}

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

	const guidedPaths = [
		{
			kicker: 'Internal alignment',
			title: 'Make the business case without a long deck rewrite',
			copy: 'Use concise assets when finance, leadership, or procurement needs the short version before the deeper review surfaces.',
			entries: [
				mustGetResource('executive-one-pager'),
				mustGetResource('roi-assumptions'),
				mustGetResource('enterprise-governance-overview')
			]
		},
		{
			kicker: 'Operating rhythm',
			title: 'Give the team a repeatable review loop',
			copy: 'Use these assets when you want one cost-review ritual, clearer owner routing, and a practical GreenOps conversation.',
			entries: [
				mustGetResource('cloud-waste-review-checklist'),
				mustGetResource('greenops-decision-framework'),
				mustGetResource('saas-license-governance-starter-pack')
			]
		},
		{
			kicker: 'Buyer diligence',
			title: 'Move into procurement and security without losing the thread',
			copy: 'These are the assets that help the product story survive security, procurement, and rollout conversations.',
			entries: [
				mustGetResource('enterprise-governance-overview'),
				mustGetResource('saas-license-governance-starter-pack'),
				mustGetResource('roi-assumptions')
			]
		}
	] as const;

	const stageColumns = [
		{
			label: 'Learn',
			title: 'Run the first review with less noise',
			copy: 'Operational guides for teams that need a practical first loop.',
			entries: resources.filter((resource) => resource.stage === 'learn')
		},
		{
			label: 'Evaluate',
			title: 'Prepare the buying and rollout conversation',
			copy: 'Assets for leadership, procurement, and rollout planning.',
			entries: resources.filter((resource) => resource.stage === 'evaluate')
		},
		{
			label: 'Validate',
			title: 'Pressure-test the modeled case',
			copy: 'Artifacts that support a deeper diligence or planning review.',
			entries: resources.filter((resource) => resource.stage === 'validate')
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
	title="Resources for rollout, review, and diligence"
	subtitle="Use the right asset for the job: start the internal case, tighten the weekly operating loop, or prepare for buyer review without dumping people into internal product detail."
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
							{channel.label}: {channel.email}
						</a>
					{/each}
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
