<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';
	import { appendPublicAttribution, buildPublicSignupHref } from '$lib/public/publicBuyingMotion';

	let startFreeHref = $derived(
		buildPublicSignupHref(base, $page.url, {
			entry: 'about',
			source: 'about_page'
		})
	);
	let pricingHref = $derived(
		appendPublicAttribution(`${base}/pricing`, $page.url, {
			entry: 'about',
			source: 'about_pricing'
		})
	);
	let docsHref = $derived(
		appendPublicAttribution(`${base}/docs`, $page.url, {
			entry: 'about',
			source: 'about_docs'
		})
	);
	let statusHref = $derived(
		appendPublicAttribution(`${base}/status`, $page.url, {
			entry: 'about',
			source: 'about_status'
		})
	);

	const reviewPoints = [
		{
			label: 'Current stage',
			value: 'Prelaunch with public pricing, docs, proof, and status surfaces live'
		},
		{
			label: 'Buying paths',
			value: 'Self-serve workspace path plus a formal enterprise diligence lane'
		},
		{
			label: 'Review stance',
			value: 'Read the docs, inspect the proof pack, and review the rollout path before onboarding'
		}
	] as const;

	const operatingFacts = [
		'Valdrics is built around owner-routed action, approvals, and reviewable proof rather than dashboard-only reporting.',
		'The public site is intentionally transparent about pricing, current prelaunch status, and the absence of public customer case studies.',
		'Early evaluators can choose between a self-serve workspace path and a formal enterprise validation lane depending on governance depth.'
	] as const;
</script>

<PublicPageMeta
	title="About Valdrics"
	description="About Valdrics: what the platform is, how evaluation works today, and which public review surfaces are available before broader rollout."
	pageType="WebPage"
	pageSection="About"
	keywords={['about valdrics', 'prelaunch', 'evaluation path', 'spend governance']}
/>

<PublicMarketingPage
	kicker="About Valdrics"
	title="A governed operating layer for spend decisions"
	subtitle="Valdrics is currently prelaunch. Buyers can review pricing, docs, proof pages, and system status before they connect a source or enter a procurement workflow."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={startFreeHref} class="btn btn-primary">Start Free Workspace</a>
		<a href={pricingHref} class="btn btn-secondary">View Pricing</a>
		<a href={docsHref} class="btn btn-secondary">Open Docs</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each reviewPoints as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		<section class="public-page__section" aria-labelledby="about-what-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">What Valdrics is</p>
				<h2 id="about-what-title" class="public-page__section-title">
					Designed for teams that need control after detection
				</h2>
				<p class="public-page__section-subtitle">
					Valdrics is not positioned as another cost dashboard. The platform is built to move a
					spend issue from signal, to owner, to approval, to recorded proof across cloud, SaaS, and
					software environments.
				</p>
			</div>
			<div class="public-page__grid public-page__grid--3">
				{#each operatingFacts as fact (fact)}
					<article class="public-page__card public-page__card--dark">
						<p class="public-page__card-copy">{fact}</p>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="about-review-title">
			<div class="public-page__band public-page__band--dark">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Current review surface</p>
					<h2 id="about-review-title" class="public-page__section-title">
						What buyers can review today
					</h2>
					<p class="public-page__section-subtitle">
						Public proof is intentionally prelaunch-safe: no customer logos or outcome claims that
						cannot be defended yet. Instead, Valdrics exposes pricing, docs, proof materials, and a
						live status surface before broader rollout.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={docsHref} class="btn btn-secondary">Open Docs</a>
					<a href={statusHref} class="btn btn-secondary">View Status</a>
					<a href={`${base}/proof`} class="btn btn-secondary">Open Proof Pack</a>
				</div>
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="about-contact-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Contact</p>
				<h2 id="about-contact-title" class="public-page__section-title">Public contact surface</h2>
				<p class="public-page__section-subtitle">
					Commercial, technical, security, licensing, and legal review channels are available
					publicly.
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
		</section>
	{/snippet}
</PublicMarketingPage>
