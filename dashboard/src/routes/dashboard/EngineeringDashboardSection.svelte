<script lang="ts">
	import { onMount } from 'svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import SavingsHero from '$lib/components/SavingsHero.svelte';
	import type { ZombieCollections } from '$lib/zombieCollections';

	type DashboardFinding = {
		provider?: 'aws' | 'azure' | 'gcp';
		finding_id?: string;
		resource_id: string;
		resource_type?: string;
		connection_id?: string;
		monthly_cost?: string | number;
		confidence?: 'high' | 'medium' | 'low';
		confidence_reason?: string;
		risk_if_deleted?: 'high' | 'medium' | 'low';
		explanation?: string;
		recommended_action?: string;
		owner?: string;
		explainability_notes?: string;
		confidence_score?: number;
		db_class?: string;
		lb_type?: string;
		is_gpu?: boolean;
		instance_type?: string;
		recommended_instance_type?: string;
	};

	type DashboardZombieCollections = ZombieCollections<DashboardFinding>;

	type SavingsHeroData = {
		total_monthly_savings?: string;
		summary?: string;
		resources?: DashboardFinding[];
		general_recommendations?: string[];
	};

	type RemediationFinding = {
		finding_id?: string;
		resource_id: string;
		resource_type?: string;
		provider?: string;
		connection_id?: string;
		monthly_cost?: string | number;
		recommended_action?: string;
		owner?: string;
		explainability_notes?: string;
		confidence_score?: number;
		db_class?: string;
		lb_type?: string;
		is_gpu?: boolean;
		instance_type?: string;
		recommended_instance_type?: string;
	};

	type FindingsTableProps = {
		resources: Array<{
			provider: 'aws' | 'azure' | 'gcp';
			finding_id?: string;
			resource_id: string;
			resource_type?: string;
			monthly_cost?: string | number;
			confidence?: 'high' | 'medium' | 'low';
			risk_if_deleted?: 'high' | 'medium' | 'low';
			explanation: string;
			confidence_reason?: string;
			recommended_action?: string;
			connection_id?: string;
			owner?: string;
			is_gpu?: boolean;
		}>;
		onRemediate: (finding: RemediationFinding) => void;
	};

	type ZombieTableProps = {
		zombies: ZombieCollections<RemediationFinding> | null | undefined;
		zombieCount: number;
		onRemediate: (finding: RemediationFinding) => void;
	};

	const loadFindingsTable = createLazyComponent<FindingsTableProps>(
		() => import('$lib/components/FindingsTable.svelte')
	);
	const loadZombieTable = createLazyComponent<ZombieTableProps>(
		() => import('$lib/components/ZombieTable.svelte')
	);

	let { zombies, analysisText, zombieCount, onRemediate } = $props<{
		zombies: DashboardZombieCollections | null | undefined;
		analysisText: string;
		zombieCount: number;
		onRemediate: (finding: RemediationFinding) => void;
	}>();

	let heavyTablesAnchor: HTMLDivElement | null = $state(null);
	let heavyTablesVisible = $state(false);

	onMount(() => {
		if (import.meta.env.MODE === 'test' || typeof IntersectionObserver === 'undefined') {
			heavyTablesVisible = true;
			return;
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) {
					heavyTablesVisible = true;
					observer.disconnect();
				}
			},
			{ rootMargin: '220px 0px' }
		);

		if (heavyTablesAnchor) {
			observer.observe(heavyTablesAnchor);
		}

		return () => observer.disconnect();
	});
</script>

{#if zombies?.ai_analysis}
	{@const aiData = zombies.ai_analysis as SavingsHeroData}

	<SavingsHero {aiData} />

	{#if aiData.general_recommendations && aiData.general_recommendations.length > 0}
		<div class="card stagger-enter engineering-dashboard__recommendations">
			<h3 class="engineering-dashboard__section-title">💡 Recommendations</h3>
			<ul class="engineering-dashboard__recommendation-list">
				{#each aiData.general_recommendations as recommendation (recommendation)}
					<li class="engineering-dashboard__recommendation-item">
						<span class="engineering-dashboard__recommendation-bullet">•</span>
						{recommendation}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
{:else if analysisText}
	<div class="card stagger-enter engineering-dashboard__insights">
		<div class="engineering-dashboard__insights-header">
			<h2 class="engineering-dashboard__section-title">AI Insights</h2>
			<span class="badge badge-default">LLM</span>
		</div>
		<div class="engineering-dashboard__insights-body">{analysisText}</div>
	</div>
{/if}

{#if (zombies?.ai_analysis && (zombies.ai_analysis as SavingsHeroData).resources?.length) || zombieCount > 0}
	<div bind:this={heavyTablesAnchor}>
		{#if heavyTablesVisible}
			{#if zombies?.ai_analysis}
				{@const aiData = zombies.ai_analysis as SavingsHeroData}
				{#if aiData.resources && aiData.resources.length > 0}
					{#await loadFindingsTable()}
						<div class="card stagger-enter engineering-dashboard__table-skeleton">
							<div class="skeleton h-8 w-48 mb-4"></div>
							<div class="skeleton h-64 rounded-2xl"></div>
						</div>
					{:then module}
						{@const FindingsTable = module.default}
						<FindingsTable
							resources={aiData.resources as FindingsTableProps['resources']}
							{onRemediate}
						/>
					{/await}
				{/if}
			{/if}

			{#if zombieCount > 0}
				{#await loadZombieTable()}
					<div class="card stagger-enter engineering-dashboard__table-skeleton">
						<div class="skeleton h-8 w-48 mb-4"></div>
						<div class="skeleton h-64 rounded-2xl"></div>
					</div>
				{:then module}
					{@const ZombieTable = module.default}
					<ZombieTable
						zombies={zombies as ZombieCollections<RemediationFinding> | null | undefined}
						{zombieCount}
						{onRemediate}
					/>
				{/await}
			{/if}
		{:else}
			<div class="card stagger-enter engineering-dashboard__table-skeleton">
				<div class="skeleton h-8 w-48 mb-4"></div>
				<div class="skeleton h-64 rounded-2xl"></div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.engineering-dashboard__recommendations {
		animation-delay: 400ms;
	}

	.engineering-dashboard__insights {
		animation-delay: 200ms;
	}

	.engineering-dashboard__section-title {
		margin: 0 0 var(--space-3);
		font-size: var(--text-lg);
		font-weight: 600;
	}

	.engineering-dashboard__recommendation-list {
		display: grid;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.engineering-dashboard__recommendation-item {
		display: flex;
		align-items: flex-start;
		gap: var(--space-2);
		font-size: var(--text-sm);
		color: var(--color-ink-300);
	}

	.engineering-dashboard__recommendation-bullet {
		color: var(--color-accent-400);
	}

	.engineering-dashboard__insights-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		margin-bottom: var(--space-3);
	}

	.engineering-dashboard__insights-body {
		white-space: pre-wrap;
		font-size: var(--text-sm);
		line-height: 1.7;
		color: var(--color-ink-300);
	}

	.engineering-dashboard__table-skeleton {
		animation-delay: 520ms;
	}
</style>
