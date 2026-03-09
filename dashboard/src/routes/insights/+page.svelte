<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { listPublicContent } from '$lib/content/publicContent';

	const insights = listPublicContent('insights');

	const heroHighlights = [
		{
			label: 'Operators',
			value: 'Guides for engineering, finance, platform, and leadership teams'
		},
		{
			label: 'Format',
			value: 'Short, practical content built around real decision loops'
		},
		{
			label: 'Best next step',
			value: 'Use Insights when the buyer needs education before live product evaluation'
		}
	] as const;
</script>

<PublicPageMeta
	title="Insights"
	description="Valdrics insights and operating playbooks for cloud, SaaS, ITAM/license, GreenOps, and finance-led spend control execution."
	pageType="CollectionPage"
	pageSection="Insights"
	keywords={['insights', 'playbooks', 'waste review', 'greenops', 'finops']}
/>

<PublicMarketingPage
	kicker="Insights"
	title="Insights"
	subtitle="Operator-focused guides for engineering, finance, and leadership teams building governed spend execution across cloud and software."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={`${base}/resources`} class="btn btn-primary">Open Resources</a>
		<a href={`${base}/auth/login?intent=insights_signup`} class="btn btn-secondary">Start Free</a>
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
		<section class="public-page__section" aria-labelledby="insights-library-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Library</p>
				<h2 id="insights-library-title" class="public-page__section-title">Start with the operating question your buyer is asking</h2>
				<p class="public-page__section-subtitle">
					These guides translate Valdrics into weekly review, GreenOps, and procurement language.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--3">
				{#each insights as insight (insight.slug)}
					<article
						class={`public-page__card ${
							insight.slug === 'why-detection-without-ownership-fails'
								? 'public-page__card--accent public-page__card--featured'
								: insight.slug === 'from-alert-to-approved-action'
									? 'public-page__card--dark'
									: 'public-page__card--featured'
						}`}
					>
						<p class="public-page__card-kicker">{insight.audiences.join(' + ')}</p>
						<h2 class="public-page__card-title">{insight.title}</h2>
						<p class="public-page__card-copy">{insight.summary}</p>
						<div class="public-page__actions-row">
							<a href={`${base}/insights/${insight.slug}`} class="btn btn-secondary">Open Insight</a>
						</div>
					</article>
				{/each}
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
