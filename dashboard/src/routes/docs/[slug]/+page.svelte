<script lang="ts">
	import PublicContentArticlePage from '$lib/components/public/PublicContentArticlePage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>{data.entry.title} | Valdrics Documentation</title>
</svelte:head>

<PublicContentArticlePage
	entry={data.entry}
	relatedEntries={data.relatedEntries}
	hubHref="/docs"
	hubLabel="Back to Documentation"
/>
