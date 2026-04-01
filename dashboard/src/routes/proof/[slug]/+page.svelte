<script lang="ts">
	import PublicContentArticlePage from '$lib/components/public/PublicContentArticlePage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>{data.entry.title} | Valdrics Proof</title>
</svelte:head>

<PublicContentArticlePage
	entry={data.entry}
	relatedEntries={data.relatedEntries}
	hubHref="/proof"
	hubLabel="Back to Proof Pack"
/>
