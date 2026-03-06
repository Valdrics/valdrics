<script lang="ts">
	import IdentitySettingsCardView from './IdentitySettingsCardView.svelte';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();
</script>

<IdentitySettingsCardView {accessToken} {tier} />
