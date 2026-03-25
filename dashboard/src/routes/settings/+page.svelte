<script lang="ts">
	import './settings.app.css';
	import SettingsPageView from './SettingsPageView.svelte';

	let { data } = $props();
</script>

<SettingsPageView {data} />
