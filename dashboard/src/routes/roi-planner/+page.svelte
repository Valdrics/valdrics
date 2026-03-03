<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import LandingRoiCalculator from '$lib/components/landing/LandingRoiCalculator.svelte';
	import {
		DEFAULT_LANDING_ROI_INPUTS,
		calculateLandingRoi,
		normalizeLandingRoiInputs,
		formatCurrencyAmount
	} from '$lib/landing/roiCalculator';
	import '$lib/components/LandingHero.css';

	let { data } = $props();

	let roiMonthlySpendUsd = $state(DEFAULT_LANDING_ROI_INPUTS.monthlySpendUsd);
	let roiExpectedReductionPct = $state(DEFAULT_LANDING_ROI_INPUTS.expectedReductionPct);
	let roiRolloutDays = $state(DEFAULT_LANDING_ROI_INPUTS.rolloutDays);
	let roiTeamMembers = $state(DEFAULT_LANDING_ROI_INPUTS.teamMembers);
	let roiBlendedHourlyUsd = $state(DEFAULT_LANDING_ROI_INPUTS.blendedHourlyUsd);
	let roiPlatformAnnualCostUsd = $state(DEFAULT_LANDING_ROI_INPUTS.platformAnnualCostUsd);

	let roiInputs = $derived(
		normalizeLandingRoiInputs({
			monthlySpendUsd: roiMonthlySpendUsd,
			expectedReductionPct: roiExpectedReductionPct,
			rolloutDays: roiRolloutDays,
			teamMembers: roiTeamMembers,
			blendedHourlyUsd: roiBlendedHourlyUsd,
			platformAnnualCostUsd: roiPlatformAnnualCostUsd
		})
	);
	let roiResult = $derived(calculateLandingRoi(roiInputs));

	function formatUsd(amount: number, currency: string = 'USD'): string {
		return formatCurrencyAmount(amount, currency);
	}
</script>

<svelte:head>
	<title>ROI Planner | Valdrics</title>
	<meta
		name="description"
		content="Build a full 12-month ROI plan with your own cloud and software spend assumptions before rollout."
	/>
</svelte:head>

<div class="container mx-auto px-6 py-10">
	<div class="max-w-3xl mb-8">
		<h1 class="text-3xl md:text-4xl font-semibold text-ink-100">ROI Planner Workspace</h1>
		<p class="text-ink-300 mt-3">
			Use your own spend profile to estimate savings potential, payback window, and net annual
			impact before rollout decisions.
		</p>
	</div>

	<AuthGate
		authenticated={!!data.user}
		action="open the ROI planner workspace"
		className="card py-12 text-center"
	>
		<LandingRoiCalculator
			sectionId="roi-planner"
			heading="Build your 12-month ROI plan"
			subtitle="Set realistic assumptions, pressure-test rollout timelines, and align engineering and finance on expected value."
			ctaLabel="Continue to Guided Setup"
			ctaNote="Directional planning model. Validate assumptions with your own usage and contract baselines."
			{roiInputs}
			{roiResult}
			{roiMonthlySpendUsd}
			{roiExpectedReductionPct}
			{roiRolloutDays}
			{roiTeamMembers}
			{roiBlendedHourlyUsd}
			buildRoiCtaHref={`${base}/onboarding?intent=roi_assessment`}
			{formatUsd}
			onRoiControlInput={() => {}}
			onRoiMonthlySpendChange={(value) => {
				roiMonthlySpendUsd = value;
			}}
			onRoiExpectedReductionChange={(value) => {
				roiExpectedReductionPct = value;
			}}
			onRoiRolloutDaysChange={(value) => {
				roiRolloutDays = value;
			}}
			onRoiTeamMembersChange={(value) => {
				roiTeamMembers = value;
			}}
			onRoiBlendedHourlyChange={(value) => {
				roiBlendedHourlyUsd = value;
			}}
			onRoiCta={() => {}}
		/>
	</AuthGate>
</div>
