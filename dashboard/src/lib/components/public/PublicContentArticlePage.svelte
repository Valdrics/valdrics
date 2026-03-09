<script lang="ts">
	import { base } from '$app/paths';
	import {
		listRelatedPublicContent,
		type PublicContentEntry
	} from '$lib/content/publicContent';
	import PublicPageMeta from './PublicPageMeta.svelte';
	import './PublicMarketingPage.css';

	interface Props {
		entry: PublicContentEntry;
		hubHref: string;
		hubLabel: string;
	}

	let { entry, hubHref, hubLabel }: Props = $props();

	const relatedEntries = $derived(listRelatedPublicContent(entry));

	function resolveHref(href: string): string {
		if (/^(https?:|mailto:)/i.test(href)) return href;
		if (!base) return href;
		if (href === '/') return base || '/';
		return `${base}${href}`;
	}

	function toSectionId(value: string): string {
		return value
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-+|-+$/g, '');
	}

	const updatedAtLabel = $derived(
		new Date(entry.updatedAt).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			timeZone: 'UTC'
		})
	);
</script>

<PublicPageMeta title={entry.seoTitle} description={entry.seoDescription} contentEntry={entry} />

<article class="public-page public-article-page">
	<section class="public-page__hero public-article-page__hero">
		<div class="container mx-auto px-6">
			<div class="public-page__hero-panel public-page__hero-panel--article">
				<p class="public-page__kicker">{entry.kicker}</p>
				<h1 class="public-page__title public-page__title--article">{entry.title}</h1>
				<p class="public-page__subtitle public-page__subtitle--article">{entry.summary}</p>
				<div class="public-page__actions">
					<a href={resolveHref(entry.primaryCta.href)} class="btn btn-primary">{entry.primaryCta.label}</a>
					{#if entry.secondaryCta}
						<a href={resolveHref(entry.secondaryCta.href)} class="btn btn-secondary">
							{entry.secondaryCta.label}
						</a>
					{/if}
					<a href={resolveHref(hubHref)} class="btn btn-secondary">{hubLabel}</a>
				</div>
				<div class="public-article-page__meta">
					<span>Updated {updatedAtLabel}</span>
					<span>{entry.readingMinutes} min read</span>
					<span>{entry.stage}</span>
				</div>
				<div class="public-page__badge-cloud">
					{#each entry.audiences as audience (audience)}
						<span class="public-page__badge">For {audience}</span>
					{/each}
				</div>
				{#if entry.downloads.length > 0}
					<div class="public-page__actions-row">
						{#each entry.downloads as download (download.href)}
							<a href={resolveHref(download.href)} class="btn btn-secondary">{download.label}</a>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</section>

	<div class="container mx-auto px-6 public-article-page__shell">
		<aside class="public-article-page__toc" aria-label="Page sections">
			<div class="public-article-page__toc-card">
				<p class="public-page__eyebrow">On this page</p>
				<nav class="public-article-page__toc-nav">
					{#each entry.sections as section (section.title)}
						<a href={`#${toSectionId(section.title)}`}>{section.title}</a>
					{/each}
				</nav>
			</div>
		</aside>

		<div class="public-article-page__content">
			<div class="public-article-page__prose">
				{#each entry.sections as section (section.title)}
					<section id={toSectionId(section.title)} class="public-article-page__section">
						<h2>{section.title}</h2>
						{#each section.body as paragraph (paragraph)}
							<p>{paragraph}</p>
						{/each}
						{#if section.bullets.length > 0}
							<ul class="public-page__list public-page__list--reading">
								{#each section.bullets as bullet (bullet)}
									<li>{bullet}</li>
								{/each}
							</ul>
						{/if}
					</section>
				{/each}
			</div>

			{#if relatedEntries.length > 0}
				<section class="public-page__section" aria-labelledby="related-content-title">
					<div class="public-page__section-head">
						<p class="public-page__eyebrow">Next reads</p>
						<h2 id="related-content-title" class="public-page__section-title">Related content</h2>
					</div>
					<div class="public-page__grid public-page__grid--2">
						{#each relatedEntries as related (related.slug)}
							<article class="public-page__card">
								<p class="public-page__card-kicker">{related.kicker}</p>
								<h2 class="public-page__card-title">{related.title}</h2>
								<p class="public-page__card-copy">{related.summary}</p>
								<a href={resolveHref(`/${related.kind}/${related.slug}`)} class="btn btn-secondary">
									Open {related.kind}
								</a>
							</article>
						{/each}
					</div>
				</section>
			{/if}
		</div>
	</div>
</article>
