<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';

	type InsightEntry = {
		title: string;
		audience: string;
		summary: string;
		ctaLabel: string;
		href: string;
	};

	const insights: readonly InsightEntry[] = [
		{
			title: 'How Engineering and Finance Run One Weekly Spend Review',
			audience: 'Engineering + FinOps',
			summary:
				'A practical operating rhythm for moving from spend signal to owner-assigned action in under one week.',
			ctaLabel: 'Open Playbook',
			href: `${base}/resources`
		},
		{
			title: 'GreenOps Decision Framework for Cost, Carbon, and Risk',
			audience: 'Platform + Sustainability',
			summary:
				'Use deterministic decision criteria to balance budget pressure with cleaner-runtime opportunities.',
			ctaLabel: 'Open GreenOps Guide',
			href: `${base}/greenops`
		},
		{
			title: 'CFO Brief: Building a Procurement-Ready TCO Narrative',
			audience: 'CFO + Procurement',
			summary:
				'Structure subscription, rollout effort, and expected recovery opportunities for executive approval.',
			ctaLabel: 'Download ROI Worksheet',
			href: `${base}/resources/valdrics-roi-assumptions.csv`
		}
	];

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

<svelte:head>
	<title>Insights | Valdrics</title>
	<meta
		name="description"
		content="Valdrics insights and operating playbooks for cloud, SaaS, ITAM/license, GreenOps, and finance-led spend control execution."
	/>
</svelte:head>

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
				{#each insights as insight (insight.title)}
					<article
						class={`public-page__card ${
							insight.title === 'How Engineering and Finance Run One Weekly Spend Review'
								? 'public-page__card--accent public-page__card--featured'
								: insight.title === 'GreenOps Decision Framework for Cost, Carbon, and Risk'
									? 'public-page__card--dark'
									: 'public-page__card--featured'
						}`}
					>
						<p class="public-page__card-kicker">{insight.audience}</p>
						<h2 class="public-page__card-title">{insight.title}</h2>
						<p class="public-page__card-copy">{insight.summary}</p>
						<div class="public-page__actions-row">
							<a href={insight.href} class="btn btn-secondary">{insight.ctaLabel}</a>
						</div>
					</article>
				{/each}
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
