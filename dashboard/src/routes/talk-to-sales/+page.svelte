<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';

	const salesMailHref =
		'mailto:enterprise@valdrics.com?cc=sales@valdrics.com&subject=Valdrics%20Enterprise%20Briefing&body=Team%20size%3A%0ACloud%2FSaaS%20scope%3A%0ATarget%20timeline%3A';

	const heroHighlights = [
		{
			label: 'Self-serve path',
			value: 'Starter, Growth, and Pro teams that want to launch quickly'
		},
		{
			label: 'Security review',
			value: 'Walk through access, approvals, SSO/SCIM, and evidence expectations'
		},
		{
			label: 'Commercial diligence',
			value: 'Choose the right plan lane and rollout path before procurement friction builds'
		}
	] as const;
</script>

<svelte:head>
	<title>Talk to Sales | Valdrics</title>
	<meta
		name="description"
		content="Book a Valdrics enterprise briefing for cloud and software spend control, rollout planning, and procurement-ready implementation guidance."
	/>
</svelte:head>

<PublicMarketingPage
	kicker="Sales Path"
	title="Talk to Sales"
	subtitle="Whether you're starting on Starter, Growth, or Pro, or running a formal enterprise review, we help you choose the right rollout path with clear security, governance, and pricing expectations."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={salesMailHref} class="btn btn-primary">Email Sales</a>
		<a href={`${base}/enterprise`} class="btn btn-secondary">Explore Enterprise Overview</a>
		<a href={`${base}/auth/login?intent=talk_to_sales&entry=talk_to_sales`} class="btn btn-secondary">
			Start Free Instead
		</a>
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
		<section class="public-page__section" aria-labelledby="sales-paths-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Buying paths</p>
				<h2 id="sales-paths-title" class="public-page__section-title">Choose the conversation that matches your buying motion</h2>
				<p class="public-page__section-subtitle">
					Some teams need a quick plan-fit conversation. Others need a formal diligence lane.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--3">
					<article class="public-page__card public-page__card--accent public-page__card--featured">
					<p class="public-page__card-kicker">Self-Serve Path</p>
					<h2 class="public-page__card-title">Starter/Growth/Pro onboarding and rollout</h2>
					<p class="public-page__card-copy">
						Align first sources, owner routing, and action workflows so smaller teams can launch quickly
						and expand controls over time.
					</p>
				</article>

					<article class="public-page__card public-page__card--dark">
					<p class="public-page__card-kicker">Security and Controls</p>
					<h2 class="public-page__card-title">Security and governance review</h2>
					<p class="public-page__card-copy">
						Walk through SSO, SCIM, role-based approvals, retention controls, and evidence requirements
						with your security and platform stakeholders.
					</p>
				</article>

					<article class="public-page__card public-page__card--featured">
					<p class="public-page__card-kicker">Commercial Diligence</p>
					<h2 class="public-page__card-title">Commercial and procurement diligence</h2>
					<p class="public-page__card-copy">
						Review tier fit, rollout effort, and due-diligence artifacts so finance, legal, and
						procurement teams can move with confidence.
					</p>
				</article>
			</div>
		</section>

		<section class="public-page__section">
				<div class="public-page__band public-page__band--accent">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Preferred path</p>
					<h2 class="public-page__section-title">Choose your preferred path</h2>
					<p class="public-page__section-subtitle">
						Most inquiries receive a response within one business day.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={salesMailHref} class="btn btn-primary">Email Sales</a>
					<a href={`${base}/enterprise`} class="btn btn-secondary">Explore Enterprise Overview</a>
					<a href={`${base}/resources`} class="btn btn-secondary">Open Sales Resources</a>
					<a href={`${base}/auth/login?intent=talk_to_sales&entry=talk_to_sales`} class="btn btn-secondary">
						Start Free Instead
					</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
