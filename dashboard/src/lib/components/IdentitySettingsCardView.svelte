<script lang="ts">
	import IdentitySettingsCardContent from '$lib/components/IdentitySettingsCardContent.svelte';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();
</script>

<IdentitySettingsCardContent {accessToken} {tier} />
