<script lang="ts">
	import './onboarding.app.css';
	import OnboardingPageView from './OnboardingPageView.svelte';

	let { data } = $props();
</script>

<OnboardingPageView {data} />
