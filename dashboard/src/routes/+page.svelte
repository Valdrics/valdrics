<script lang="ts">
	import LandingHero from '$lib/components/LandingHero.svelte';
	import type { PageData } from './$types';
	import { PUBLIC_HOME_META } from './homeDashboardContent';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>{PUBLIC_HOME_META.title}</title>
	<meta name="description" content={PUBLIC_HOME_META.description} />
	<meta name="keywords" content={PUBLIC_HOME_META.keywords} />
	<meta property="og:title" content={PUBLIC_HOME_META.title} />
	<meta property="og:description" content={PUBLIC_HOME_META.ogDescription} />
	<meta property="og:type" content="website" />
	<meta property="og:url" content={data.landingHero.canonicalUrl} />
	<meta property="og:image" content={data.landingHero.ogImageUrl} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={PUBLIC_HOME_META.title} />
	<meta name="twitter:description" content={PUBLIC_HOME_META.ogDescription} />
	<meta name="twitter:image" content={data.landingHero.ogImageUrl} />
</svelte:head>

<LandingHero {...data.landingHero} />
