<script lang="ts">
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';

	import type { PageData } from './$types';
	import type { StatusTone } from './statusPage';

	let { data }: { data: PageData } = $props();

	const toneClassByValue: Record<StatusTone, string> = {
		success: 'status-pill status-pill--success',
		warning: 'status-pill status-pill--warning',
		danger: 'status-pill status-pill--danger',
		neutral: 'status-pill status-pill--neutral'
	};

	function formatCheckedAt(timestamp: string): string {
		return new Intl.DateTimeFormat('en-US', {
			dateStyle: 'medium',
			timeStyle: 'short'
		}).format(new Date(timestamp));
	}
</script>

<svelte:head>
	<title>Status | Valdrics</title>
	<meta
		name="description"
		content="Current service status for Valdrics core platform dependencies and automated health checks."
	/>
</svelte:head>

<PublicMarketingPage
	kicker="Status"
	title="Current platform status"
	subtitle="Public health summary for core Valdrics services and dependencies."
	heroVariant="narrow"
>
	{#snippet heroMeta()}
		<article class="public-page__meta-item">
			<strong>Overall status</strong>
			<span>{data.summaryLabel}</span>
		</article>
		<article class="public-page__meta-item">
			<strong>Last checked</strong>
			<span>{formatCheckedAt(data.checkedAt)}</span>
		</article>
		<article class="public-page__meta-item">
			<strong>Source</strong>
			<span>{data.source === 'live' ? 'Automated /health summary' : 'Fallback summary'}</span>
		</article>
	{/snippet}

	{#snippet children()}
		{#if data.source !== 'live'}
			<section class="public-page__section" aria-labelledby="status-notice-title">
				<article class="public-page__card public-page__card--accent status-notice">
					<p class="public-page__card-kicker">Health summary notice</p>
					<h2 id="status-notice-title" class="public-page__card-title">Automated checks are unavailable</h2>
					<p class="public-page__card-copy">{data.summaryDetail}</p>
				</article>
			</section>
		{/if}

		<section class="public-page__section" aria-labelledby="status-services-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Service checks</p>
				<h2 id="status-services-title" class="public-page__section-title">Live dependency summary</h2>
				<p class="public-page__section-subtitle">
					Each card reflects the latest automated health payload. This page reports operational state, not
					planned maintenance calendars.
				</p>
			</div>

			<div class="public-page__grid public-page__grid--3 status-grid">
				{#each data.components as component (component.name)}
					<article class="public-page__card status-card">
						<div class="status-card__head">
							<h3 class="public-page__card-title">{component.name}</h3>
							<span class={toneClassByValue[component.tone]}>{component.statusLabel}</span>
						</div>
						<p class="public-page__card-copy">{component.detail}</p>
					</article>
				{/each}
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>

<style>
	.status-grid {
		align-items: stretch;
	}

	.status-card {
		min-height: 100%;
	}

	.status-card__head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.8rem;
	}

	.status-pill {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 1.9rem;
		padding: 0.3rem 0.7rem;
		border-radius: 999px;
		font-size: 0.77rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		white-space: nowrap;
	}

	.status-pill--success {
		background: rgb(34 197 94 / 0.14);
		color: rgb(21 128 61);
	}

	.status-pill--warning {
		background: rgb(245 158 11 / 0.16);
		color: rgb(180 83 9);
	}

	.status-pill--danger {
		background: rgb(239 68 68 / 0.14);
		color: rgb(185 28 28);
	}

	.status-pill--neutral {
		background: rgb(148 163 184 / 0.16);
		color: rgb(71 85 105);
	}

	@media (max-width: 900px) {
		.status-card__head {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
