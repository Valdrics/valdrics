<script lang="ts">
	import './connections.app.css';
	import ConnectionsPageView from './ConnectionsPageView.svelte';

	let { data } = $props();
</script>

<ConnectionsPageView {data} />
