<script lang="ts">
	import DashboardPage from '../../dashboard/+page.svelte';
	import type { PageData as DashboardPageData } from '../../dashboard/$types';
	import { buildDashboardHeroCaptureData } from '../../dashboard/dashboardHeroCaptureFixture';

	const data = buildDashboardHeroCaptureData() as unknown as DashboardPageData;
</script>

<svelte:head>
	<title>Dashboard Hero Capture</title>
	<meta name="robots" content="noindex, nofollow" />
</svelte:head>

<div class="dashboard-hero-capture-shell">
	<div class="dashboard-hero-capture" data-dashboard-hero-capture>
		<DashboardPage {data} />
	</div>
</div>

<style>
	.dashboard-hero-capture-shell {
		display: grid;
		place-items: center;
		padding: 1.5rem;
		background:
			radial-gradient(circle at top left, rgb(8 126 164 / 0.22), transparent 28%),
			radial-gradient(circle at top right, rgb(56 189 248 / 0.18), transparent 24%),
			linear-gradient(180deg, rgb(3 7 18), rgb(10 16 30));
	}

	.dashboard-hero-capture {
		width: 1440px;
		height: 960px;
		padding: 1.5rem;
		border-radius: 1.5rem;
		border: 1px solid rgb(56 189 248 / 0.12);
		background:
			radial-gradient(circle at top right, rgb(8 126 164 / 0.12), transparent 28%),
			linear-gradient(180deg, rgb(6 10 19 / 0.98), rgb(10 15 25 / 0.98));
		box-shadow:
			0 30px 70px rgb(2 8 23 / 0.34),
			inset 0 1px 0 rgb(255 255 255 / 0.04);
		overflow: hidden;
	}

	:global(.dashboard-hero-capture .card),
	:global(.dashboard-hero-capture .glass-panel),
	:global(.dashboard-hero-capture .freshness-indicator) {
		backdrop-filter: blur(10px);
	}
</style>
