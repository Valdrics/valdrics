<script lang="ts">
	import PublicContentArticlePage from '$lib/components/public/PublicContentArticlePage.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<PublicContentArticlePage entry={data.entry} hubHref="/docs" hubLabel="Back to Documentation" />
