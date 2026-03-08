<script lang="ts">
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import { PUBLIC_EXTENDED_CONTACT_CHANNELS } from '$lib/landing/publicNav';

	type ResourceEntry = {
		category: string;
		title: string;
		summary: string;
		href: string;
		ctaLabel: string;
	};

	const resources: readonly ResourceEntry[] = [
		{
			category: 'Enterprise',
			title: 'Enterprise Governance Overview',
			summary:
				'Review Valdrics enterprise control architecture, procurement-ready diligence path, and rollout model in one destination.',
			href: `${base}/enterprise`,
			ctaLabel: 'Open Enterprise Page'
		},
		{
			category: 'Playbook',
			title: 'Cloud Waste Review Checklist',
			summary:
				'Run a weekly 30-minute review that aligns finance and engineering on top waste risks and owners.',
			href: `${base}/docs`,
			ctaLabel: 'Open Resource'
		},
		{
			category: 'Guide',
			title: 'GreenOps Decision Framework',
			summary:
				'Balance cost, reliability, and carbon impact with decision rules that teams can execute safely.',
			href: `${base}/greenops`,
			ctaLabel: 'Open Resource'
		},
		{
			category: 'Template',
			title: 'SaaS and License Governance Starter Pack',
			summary:
				'Use role-based approval and owner-routing templates for software renewals and license optimization.',
			href: `${base}/docs/technical-validation`,
			ctaLabel: 'Open Resource'
		},
		{
			category: 'Collateral',
			title: 'Executive One-Pager (Download)',
			summary:
				'Share a concise procurement and rollout brief with finance, engineering, and leadership stakeholders.',
			href: `${base}/resources/valdrics-enterprise-one-pager.md`,
			ctaLabel: 'Download One-Pager'
		},
		{
			category: 'Template',
			title: 'ROI Assumptions Worksheet (CSV)',
			summary:
				'Model TCO assumptions and controllable spend opportunity before procurement and budget review.',
			href: `${base}/resources/valdrics-roi-assumptions.csv`,
			ctaLabel: 'Download Worksheet'
		}
	];

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

<svelte:head>
	<title>Resources | Valdrics</title>
	<meta
		name="description"
		content="Valdrics resources: practical playbooks, templates, and guides for cloud, SaaS, license, and GreenOps cost control."
	/>
</svelte:head>

<PublicMarketingPage
	kicker="Resource Hub"
	title="Resources"
	subtitle="Practical guidance for teams that want to reduce cloud and software waste without slowing delivery."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href={`${base}/auth/login?intent=resource_signup&entry=resources`} class="btn btn-primary">
			Start Free
		</a>
		<a href={`${base}/talk-to-sales?entry=resources&source=resource_hub`} class="btn btn-secondary">
			Talk to Sales
		</a>
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
				<h2 id="resources-library-title" class="public-page__section-title">Use the right asset for the buying moment</h2>
				<p class="public-page__section-subtitle">
					Each asset is tuned for a specific stage: self-serve evaluation, internal alignment, or
					formal diligence.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--3">
				{#each resources as resource (resource.title)}
						<article
							class={`public-page__card ${
								resource.title === 'Enterprise Governance Overview'
									? 'public-page__card--accent public-page__card--featured'
									: resource.title === 'GreenOps Decision Framework'
										? 'public-page__card--dark'
										: resource.title === 'Executive One-Pager (Download)'
											? 'public-page__card--featured'
											: ''
							}`}
						>
						<p class="public-page__card-kicker">{resource.category}</p>
						<h2 class="public-page__card-title">{resource.title}</h2>
						<p class="public-page__card-copy">{resource.summary}</p>
						<div class="public-page__actions-row">
							<a href={resource.href} class="btn btn-secondary">{resource.ctaLabel}</a>
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
