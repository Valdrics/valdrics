<script lang="ts">
	import { createLazyComponent } from '$lib/lazyComponent';

	let { data } = $props();

	const loadOnboardingPageViewContent = createLazyComponent(
		() => import('./OnboardingPageViewContent.svelte')
	);
	const onboardingPageViewContentPromise =
		import.meta.env.MODE === 'test' ? loadOnboardingPageViewContent() : null;
</script>

{#await onboardingPageViewContentPromise ?? loadOnboardingPageViewContent()}
	<div class="card py-10">
		<div class="skeleton h-8 w-64 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-2/3 mb-8"></div>
		<div class="skeleton h-96 rounded-2xl"></div>
	</div>
{:then module}
	{@const OnboardingPageViewContent = module.default}
	<OnboardingPageViewContent {data} />
{/await}
