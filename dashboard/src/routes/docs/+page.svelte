<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import type { PublicContentEntry } from '$lib/content/publicContent.types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const heroHighlights = [
		{
			label: 'Start fast',
			value: 'Quick start and first-provider guidance without a long setup maze'
		},
		{
			label: 'Validate safely',
			value: 'Technical validation and proof surfaces for serious buyers'
		},
		{
			label: 'Integrate cleanly',
			value: 'API docs, decision-record guidance, and repository runbooks in one path'
		}
	] as const;

	const docPaths = [
		{
			kicker: 'Start here',
			title: 'Quick Start a Valdrics Workspace',
			copy: 'The fastest path from an empty workspace to a first working Valdrics setup.',
			href: `${base}/docs/quick-start-workspace`
		},
		{
			kicker: 'Validate',
			title: 'Technical Validation',
			copy: 'Capability and architecture material for teams doing technical review.',
			href: `${base}/docs/technical-validation`
		},
		{
			kicker: 'Integrate',
			title: 'API Reference',
			copy: 'Endpoint groups and request examples for product and platform integrations.',
			href: `${base}/docs/api`
		}
	] as const;

	let operatingGuides = $derived(data.operatingGuides as PublicContentEntry[]);
</script>

<PublicPageMeta
	title="Documentation"
	description="Valdrics documentation for setup, dashboard workflows, API usage, and operational guidance."
	pageType="CollectionPage"
	pageSection="Documentation"
	keywords={['documentation', 'api', 'technical validation', 'setup', 'governance']}
/>

<PublicMarketingPage
	kicker="Documentation"
	title="Documentation for setup, validation, and API review"
	subtitle="Move from quick start to technical review without bouncing between marketing pages, docs, and repository notes."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={`${base}/docs/api`} class="btn btn-primary">Open API Docs</a>
		<a href={`${base}/docs/technical-validation`} class="btn btn-secondary">
			Open Technical Validation
		</a>
		<a href={`${base}/pricing`} class="btn btn-secondary">View Pricing</a>
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
		<section class="public-page__section" aria-labelledby="docs-paths-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Start paths</p>
				<h2 id="docs-paths-title" class="public-page__section-title">
					Pick the first documentation surface that matches the question
				</h2>
				<p class="public-page__section-subtitle">
					Start with the most relevant guide instead of forcing every reader through the full docs
					tree.
				</p>
			</div>

			<div class="public-page__flow-grid public-page__flow-grid--3">
				{#each docPaths as path (path.title)}
					<article class="public-page__flow-card">
						<p class="public-page__card-kicker">{path.kicker}</p>
						<h2 class="public-page__card-title">{path.title}</h2>
						<p class="public-page__card-copy">{path.copy}</p>
						<a href={path.href} class="btn btn-secondary">
							{path.kicker === 'Integrate' ? 'Open API Docs' : 'Open guide'}
						</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="docs-sections-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Core guides</p>
				<h2 id="docs-sections-title" class="public-page__section-title">
					Use the core guides for the operating loop
				</h2>
				<p class="public-page__section-subtitle">
					These are the guides most teams need after quick start: first connection, owner routing,
					and decision record handling.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--2">
				{#each operatingGuides as entry (entry.slug)}
					<article class="public-page__card">
						<p class="public-page__card-kicker">{entry.kicker}</p>
						<h2 class="public-page__card-title">{entry.title}</h2>
						<p class="public-page__card-copy">{entry.summary}</p>
						<div class="public-page__mini-list">
							{#each entry.sections[0]?.bullets ?? [] as bullet (bullet)}
								<div class="public-page__mini-link public-page__mini-link--static">
									<span>{bullet}</span>
								</div>
							{/each}
						</div>
						<a href={`${base}/docs/${entry.slug}`} class="btn btn-secondary">Open guide</a>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section">
			<div class="public-page__band">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Repository docs</p>
					<h2 class="public-page__section-title">Repository docs and adjacent surfaces</h2>
					<p class="public-page__section-subtitle">
						Use GitHub for full runbooks and implementation notes. Use `proof` and `resources` for
						evaluation and rollout conversations.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a
						href="https://github.com/Valdrics/valdrics/tree/main/docs"
						target="_blank"
						rel="noopener noreferrer"
						class="btn btn-secondary"
					>
						Browse GitHub Docs
					</a>
					<a href={`${base}/proof`} class="btn btn-secondary">Open Proof Pack</a>
					<a href={`${base}/resources`} class="btn btn-secondary">Open Resources</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
