<script lang="ts">
	import ConnectionsPageView from './ConnectionsPageView.svelte';

	let { data } = $props();
</script>

<ConnectionsPageView {data} />
