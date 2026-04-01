<script lang="ts">
	import PublicContentArticlePage from '$lib/components/public/PublicContentArticlePage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>{data.entry.title} | Valdrics Resources</title>
</svelte:head>

<PublicContentArticlePage
	entry={data.entry}
	relatedEntries={data.relatedEntries}
	hubHref="/resources"
	hubLabel="Back to Resources"
/>
