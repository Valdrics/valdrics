<script lang="ts">
	import FindingsTable from '$lib/components/FindingsTable.svelte';
	import SavingsHero from '$lib/components/SavingsHero.svelte';
	import ZombieTable from '$lib/components/ZombieTable.svelte';
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

	let { zombies, analysisText, zombieCount, onRemediate } = $props<{
		zombies: DashboardZombieCollections | null | undefined;
		analysisText: string;
		zombieCount: number;
		onRemediate: (finding: RemediationFinding) => void;
	}>();
</script>

{#if zombies?.ai_analysis}
	{@const aiData = zombies.ai_analysis as SavingsHeroData}

	<SavingsHero {aiData} />

	{#if aiData.resources && aiData.resources.length > 0}
		<FindingsTable
			resources={aiData.resources as Array<{
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
			}>}
			{onRemediate}
		/>
	{/if}

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

{#if zombieCount > 0}
	<ZombieTable
		zombies={zombies as ZombieCollections<RemediationFinding> | null | undefined}
		{zombieCount}
		{onRemediate}
	/>
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
</style>
