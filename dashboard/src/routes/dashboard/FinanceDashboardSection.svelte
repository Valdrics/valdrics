<script lang="ts">
	import { onMount } from 'svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import GreenOpsWidget from '$lib/components/GreenOpsWidget.svelte';
	import UnitEconomicsCards from '$lib/components/UnitEconomicsCards.svelte';
	import UpgradeNotice from '$lib/components/UpgradeNotice.svelte';
	import { tierAtLeast } from '$lib/tier';

	type AllocationBucket = {
		name?: string;
		value?: number;
	};

	type AllocationData = {
		buckets?: AllocationBucket[];
	};

	type CloudDistributionMatrixProps = {
		data?: Array<{
			label: string;
			value: number;
			color: string;
		}>;
	};

	type AllocationBreakdownProps = {
		data: {
			buckets: Array<{
				name: string;
				total_amount: number;
				record_count: number;
				color?: string;
			}>;
			total: number;
		} | null;
		loading?: boolean;
		error?: string | null;
	};

	const loadCloudDistributionMatrix = createLazyComponent<CloudDistributionMatrixProps>(
		() => import('$lib/components/CloudDistributionMatrix.svelte')
	);
	const loadRoaChart = createLazyComponent<Record<string, never>>(
		() => import('$lib/components/ROAChart.svelte')
	);
	const loadAllocationBreakdown = createLazyComponent<AllocationBreakdownProps>(
		() => import('$lib/components/AllocationBreakdown.svelte')
	);

	let { allocation, tier, unitEconomics } = $props<{
		allocation: AllocationData | null | undefined;
		tier: string;
		unitEconomics: Record<string, unknown> | null | undefined;
	}>();

	let financeDetailAnchor: HTMLDivElement | null = $state(null);
	let financeDetailsVisible = $state(false);

	onMount(() => {
		if (import.meta.env.MODE === 'test' || typeof IntersectionObserver === 'undefined') {
			financeDetailsVisible = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					financeDetailsVisible = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '220px 0px' }
		);

		if (financeDetailAnchor) {
			observer.observe(financeDetailAnchor);
		}

		return () => observer.disconnect();
	});
</script>

<UnitEconomicsCards {unitEconomics} />

<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-2 finance-dashboard__summary-grid">
	<GreenOpsWidget />
	<div bind:this={financeDetailAnchor}>
		{#if financeDetailsVisible}
			{#await loadCloudDistributionMatrix()}
				<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
					<div class="skeleton h-8 w-40"></div>
					<div class="skeleton finance-dashboard__chart-skeleton"></div>
				</div>
			{:then module}
				{@const CloudDistributionMatrix = module.default}
				<CloudDistributionMatrix />
			{/await}
		{:else}
			<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
				<div class="skeleton h-8 w-40"></div>
				<div class="skeleton finance-dashboard__chart-skeleton"></div>
			</div>
		{/if}
	</div>
</div>

{#if financeDetailsVisible}
	<div class="grid gap-6 md:grid-cols-1 lg:grid-cols-2 finance-dashboard__detail-grid">
		{#await loadRoaChart()}
			<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
				<div class="skeleton h-8 w-32"></div>
				<div
					class="skeleton finance-dashboard__chart-skeleton finance-dashboard__chart-skeleton--tall"
				></div>
			</div>
		{:then module}
			{@const ROAChart = module.default}
			<ROAChart />
		{/await}

		{#if allocation && allocation.buckets && allocation.buckets.length > 0}
			{#await loadAllocationBreakdown()}
				<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
					<div class="skeleton h-8 w-44"></div>
					<div
						class="skeleton finance-dashboard__chart-skeleton finance-dashboard__chart-skeleton--tall"
					></div>
				</div>
			{:then module}
				{@const AllocationBreakdown = module.default}
				<AllocationBreakdown
					data={{
						buckets: allocation.buckets.map((bucket: AllocationBucket) => ({
							name: bucket.name ?? 'Unallocated',
							total_amount: bucket.value ?? 0,
							record_count: 0
						})),
						total: allocation.buckets.reduce(
							(sum: number, bucket: AllocationBucket) => sum + (bucket.value ?? 0),
							0
						)
					}}
				/>
			{/await}
		{:else if !tierAtLeast(tier, 'growth')}
			<UpgradeNotice
				currentTier={tier}
				requiredTier="growth"
				feature="Cost Allocation (chargeback/showback)"
			/>
		{:else}
			<div class="glass-panel finance-dashboard__empty-state">
				<p>Cost Allocation data will appear here once attribution rules are defined.</p>
			</div>
		{/if}
	</div>
{:else}
	<div class="grid gap-6 md:grid-cols-1 lg:grid-cols-2 finance-dashboard__detail-grid">
		<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
			<div class="skeleton h-8 w-32"></div>
			<div
				class="skeleton finance-dashboard__chart-skeleton finance-dashboard__chart-skeleton--tall"
			></div>
		</div>
		<div class="glass-panel finance-dashboard__card-skeleton" aria-hidden="true">
			<div class="skeleton h-8 w-44"></div>
			<div
				class="skeleton finance-dashboard__chart-skeleton finance-dashboard__chart-skeleton--tall"
			></div>
		</div>
	</div>
{/if}

<style>
	.finance-dashboard__summary-grid,
	.finance-dashboard__detail-grid {
		align-items: stretch;
	}

	.finance-dashboard__card-skeleton {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		padding: var(--space-6);
		min-height: 18rem;
	}

	.finance-dashboard__chart-skeleton {
		width: 100%;
		min-height: 13rem;
		border-radius: 1.5rem;
	}

	.finance-dashboard__chart-skeleton--tall {
		min-height: 18rem;
	}

	.finance-dashboard__empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 18rem;
		color: var(--color-ink-500);
		text-align: center;
		padding: var(--space-6);
	}

	.finance-dashboard__empty-state p {
		margin: 0;
	}
</style>
