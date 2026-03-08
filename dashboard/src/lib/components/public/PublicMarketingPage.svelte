<script lang="ts">
	import type { Snippet } from 'svelte';
	import './PublicMarketingPage.css';

	interface Props {
		kicker?: string;
		title: string;
		subtitle: string;
		heroActions?: Snippet;
		heroMeta?: Snippet;
		children?: Snippet;
		heroVariant?: 'wide' | 'narrow';
	}

	let {
		kicker = '',
		title,
		subtitle,
		heroActions,
		heroMeta,
		children,
		heroVariant = 'wide'
	}: Props = $props();
</script>

<div class="public-page">
	<section class="public-page__hero">
		<div class="container mx-auto px-6">
			<div class={`public-page__hero-panel ${heroVariant === 'narrow' ? 'is-narrow' : ''}`}>
				{#if kicker}
					<p class="public-page__kicker">{kicker}</p>
				{/if}
				<h1 class="public-page__title">{title}</h1>
				<p class="public-page__subtitle">{subtitle}</p>
				{#if heroActions}
					<div class="public-page__actions">
						{@render heroActions()}
					</div>
				{/if}
				{#if heroMeta}
					<div class="public-page__meta">
						{@render heroMeta()}
					</div>
				{/if}
			</div>
		</div>
	</section>

	<div class="public-page__body container mx-auto px-6">
		{@render children?.()}
	</div>
</div>
