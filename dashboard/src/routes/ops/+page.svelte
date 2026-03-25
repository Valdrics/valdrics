<script lang="ts">
	import './ops.app.css';
	import OpsPageView from './OpsPageView.svelte';

	let { data } = $props();
</script>

<OpsPageView {data} />
