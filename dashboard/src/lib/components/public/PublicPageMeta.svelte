<script lang="ts">
	import { assets } from '$app/paths';
	import { page } from '$app/stores';
	import createDOMPurify from 'dompurify';
	import type { PublicContentEntry } from '$lib/content/publicContent';
	import {
		buildPublicContentStructuredData,
		buildPublicPageStructuredData,
		resolveCanonicalUrl,
		resolvePublicMetaImage,
		type PublicStructuredDataPageType
	} from '$lib/seo/publicMeta';

	interface Props {
		title: string;
		description: string;
		contentEntry?: PublicContentEntry;
		pageType?: PublicStructuredDataPageType;
		pageSection?: string;
		keywords?: string[];
		ogType?: 'website' | 'article';
	}

	let {
		title,
		description,
		contentEntry,
		pageType,
		pageSection,
		keywords = [],
		ogType
	}: Props = $props();

	const canonicalUrl = $derived(resolveCanonicalUrl($page.url));
	const imageUrl = $derived(resolvePublicMetaImage($page.url, assets));
	const effectiveOgType = $derived(
		ogType ?? (contentEntry ? (contentEntry.kind === 'proof' ? 'website' : 'article') : 'website')
	);
	const structuredData = $derived.by(() => {
		if (contentEntry) {
			return [buildPublicContentStructuredData(contentEntry, canonicalUrl)];
		}
		if (pageType) {
			return [
				buildPublicPageStructuredData({
					pageType,
					name: title,
					description,
					canonicalUrl,
					section: pageSection,
					keywords
				})
			];
		}
		return [];
	});
	const DOMPurify = typeof window === 'undefined' ? null : createDOMPurify(window);
	const structuredDataJson = $derived(
		structuredData.map((value) =>
			JSON.stringify(value).replaceAll('<', '\\u003c').replaceAll('</script', '<\\/script')
		)
	);
	const structuredDataMarkup = $derived(
		structuredDataJson.map((value) => {
			const sanitizedValue = DOMPurify
				? DOMPurify.sanitize(value, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
				: value;
			return '<script type="application/ld+json">' + sanitizedValue + '</scr' + 'ipt>';
		})
	);
</script>

<svelte:head>
	<title>{title} | Valdrics</title>
	<meta name="description" content={description} />
	{#if keywords.length > 0}
		<meta name="keywords" content={Array.from(new Set(keywords)).join(', ')} />
	{/if}
	<meta property="og:title" content={`${title} | Valdrics`} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content={effectiveOgType} />
	<meta property="og:url" content={canonicalUrl} />
	<meta property="og:image" content={imageUrl} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={`${title} | Valdrics`} />
	<meta name="twitter:description" content={description} />
	<meta name="twitter:image" content={imageUrl} />
	{#if contentEntry && effectiveOgType === 'article'}
		<meta property="article:published_time" content={contentEntry.updatedAt} />
		<meta property="article:modified_time" content={contentEntry.updatedAt} />
		<meta property="article:section" content={contentEntry.kind} />
	{/if}
	{#each structuredDataMarkup as item, index (`structured-data-${index}`)}
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		{@html item}
	{/each}
</svelte:head>
