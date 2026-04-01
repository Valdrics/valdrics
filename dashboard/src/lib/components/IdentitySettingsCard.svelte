<script lang="ts">
	import { createLazyComponent } from '$lib/lazyComponent';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();

	type IdentitySettingsCardContentProps = {
		accessToken?: string | null;
		tier?: string | null;
	};

	const loadIdentitySettingsCardContent = createLazyComponent<IdentitySettingsCardContentProps>(
		() => import('./IdentitySettingsCardContent.svelte')
	);
</script>

{#await loadIdentitySettingsCardContent()}
	<div class="card">
		<div class="skeleton mb-4 h-6 w-40"></div>
		<div class="skeleton mb-2 h-4 w-full"></div>
		<div class="skeleton h-4 w-3/4"></div>
	</div>
{:then module}
	{@const IdentitySettingsCardContent = module.default}
	<IdentitySettingsCardContent {accessToken} {tier} />
{:catch}
	<div class="card">
		<div class="skeleton mb-4 h-6 w-40"></div>
		<div class="skeleton mb-2 h-4 w-full"></div>
		<div class="skeleton h-4 w-3/4"></div>
	</div>
{/await}
