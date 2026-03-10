<script lang="ts">
	import type { JobRecord, PendingRequest, StrategyRecommendation } from './opsTypes';

	let {
		pendingRequests,
		processingJobs = false,
		jobs,
		recommendations,
		refreshingStrategies = false,
		actingId = null,
		formatDate,
		formatUsd,
		onLoadOpsData,
		onOpenRemediationModal,
		onProcessPendingJobs,
		onRefreshRecommendations,
		onApplyRecommendation
	}: {
		pendingRequests: PendingRequest[];
		processingJobs?: boolean;
		jobs: JobRecord[];
		recommendations: StrategyRecommendation[];
		refreshingStrategies?: boolean;
		actingId?: string | null;
		formatDate: (value: string | null) => string;
		formatUsd: (value: number) => string;
		onLoadOpsData: () => void | Promise<void>;
		onOpenRemediationModal: (req: PendingRequest) => void | Promise<void>;
		onProcessPendingJobs: () => void | Promise<void>;
		onRefreshRecommendations: () => void | Promise<void>;
		onApplyRecommendation: (id: string) => void | Promise<void>;
	} = $props();
</script>

<div class="card">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">Remediation Queue</h2>
	</div>
	{#if pendingRequests.length === 0}
		<p class="text-ink-400 text-sm">No pending remediation requests.</p>
	{:else}
		<div class="overflow-x-auto">
			<table class="table">
				<thead>
					<tr>
						<th>Request</th>
						<th>Resource</th>
						<th>Action</th>
						<th>Savings</th>
						<th>Created</th>
						<th>Controls</th>
					</tr>
				</thead>
				<tbody>
					{#each pendingRequests as req (req.id)}
						<tr>
							<td class="font-mono text-xs">{req.id.slice(0, 8)}...</td>
							<td>
								<div class="text-sm">{req.resource_type}</div>
								<div class="text-xs text-ink-500 font-mono">{req.resource_id}</div>
								<div class="text-xs text-ink-500 capitalize">{req.status.replaceAll('_', ' ')}</div>
								{#if req.escalation_required}
									<div class="badge badge-warning mt-1 text-xs">
										Escalated: {req.escalation_reason || 'Owner approval required'}
									</div>
								{/if}
							</td>
							<td class="capitalize">{req.action.replaceAll('_', ' ')}</td>
							<td>{formatUsd(req.estimated_savings)}</td>
							<td class="text-xs text-ink-500">{formatDate(req.created_at)}</td>
							<td class="flex gap-2">
								<button
									type="button"
									class="btn btn-primary text-xs"
									disabled={actingId === req.id}
									onclick={() => onOpenRemediationModal(req)}
								>
									Review
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<div class="card">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">Background Jobs</h2>
		<div class="flex gap-2">
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={processingJobs}
				onclick={onLoadOpsData}
			>
				Refresh
			</button>
			<button
				type="button"
				class="btn btn-primary text-xs"
				disabled={processingJobs}
				onclick={onProcessPendingJobs}
			>
				{processingJobs ? 'Processing...' : 'Process Pending'}
			</button>
		</div>
	</div>
	<div class="overflow-x-auto">
		<table class="table">
			<thead>
				<tr>
					<th>Type</th>
					<th>Status</th>
					<th>Attempts</th>
					<th>Created</th>
					<th>Error</th>
				</tr>
			</thead>
			<tbody>
				{#if jobs.length === 0}
					<tr>
						<td colspan="5" class="text-ink-400 text-center py-4">No jobs found.</td>
					</tr>
				{:else}
					{#each jobs as job (job.id)}
						<tr>
							<td class="font-mono text-xs">{job.job_type}</td>
							<td class="capitalize">{job.status}</td>
							<td>{job.attempts}</td>
							<td class="text-xs text-ink-500">{formatDate(job.created_at)}</td>
							<td class="text-xs text-danger-400">{job.error_message || '-'}</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</div>

<div class="card">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">RI/SP Strategy Recommendations</h2>
		<div class="flex gap-2">
			<button type="button" class="btn btn-secondary text-xs" onclick={onLoadOpsData}
				>Refresh</button
			>
			<button
				type="button"
				class="btn btn-primary text-xs"
				disabled={refreshingStrategies}
				onclick={onRefreshRecommendations}
			>
				{refreshingStrategies ? 'Refreshing...' : 'Regenerate'}
			</button>
		</div>
	</div>
	<div class="overflow-x-auto">
		<table class="table">
			<thead>
				<tr>
					<th>Resource</th>
					<th>Region</th>
					<th>Term</th>
					<th>Payment</th>
					<th>Savings</th>
					<th>ROI</th>
					<th>Action</th>
				</tr>
			</thead>
			<tbody>
				{#if recommendations.length === 0}
					<tr>
						<td colspan="7" class="text-ink-400 text-center py-4"
							>No open strategy recommendations.</td
						>
					</tr>
				{:else}
					{#each recommendations as rec (rec.id)}
						<tr>
							<td class="text-sm">{rec.resource_type}</td>
							<td class="text-sm">{rec.region}</td>
							<td class="text-sm">{rec.term}</td>
							<td class="text-sm">{rec.payment_option}</td>
							<td class="text-success-400 font-semibold"
								>{formatUsd(rec.estimated_monthly_savings)}</td
							>
							<td>{rec.roi_percentage.toFixed(1)}%</td>
							<td>
								<button
									type="button"
									class="btn btn-secondary text-xs"
									disabled={actingId === rec.id}
									onclick={() => onApplyRecommendation(rec.id)}
								>
									Apply
								</button>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</div>
