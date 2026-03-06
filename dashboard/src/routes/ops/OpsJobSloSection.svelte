<script lang="ts">
	import type { JobSLOResponse } from './opsTypes';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		jobSloWindowHours: number;
		refreshingJobSlo: boolean;
		refreshJobSlo: AsyncAction;
		jobSlo: JobSLOResponse | null;
		jobSloBadgeClass: (value: JobSLOResponse) => string;
		jobSloMetricBadgeClass: (metric: JobSLOResponse['metrics'][number]) => string;
		formatDuration: (value: number | null | undefined) => string;
	}

	let {
		jobSloWindowHours = $bindable(),
		refreshingJobSlo,
		refreshJobSlo,
		jobSlo,
		jobSloBadgeClass,
		jobSloMetricBadgeClass,
		formatDuration
	}: Props = $props();
</script>

<div class="card space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Job Reliability SLO</h2>
			<p class="text-xs text-ink-400">
				Admin-only reliability view for background jobs (success rate + duration tails).
			</p>
		</div>
		<div class="flex items-end gap-2">
			<label class="text-xs text-ink-400">
				<span class="block mb-1">Window</span>
				<select class="input text-xs" bind:value={jobSloWindowHours} aria-label="Job SLO Window">
					<option value={24}>Last 24h</option>
					<option value={72}>Last 72h</option>
					<option value={168}>Last 7d</option>
				</select>
			</label>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingJobSlo}
				onclick={refreshJobSlo}
			>
				{refreshingJobSlo ? 'Refreshing...' : 'Refresh SLO'}
			</button>
		</div>
	</div>

	{#if jobSlo}
		<div class="flex items-center gap-2">
			<span class={jobSloBadgeClass(jobSlo)}>
				{jobSlo.overall_meets_slo ? 'SLO Healthy' : 'SLO At Risk'}
			</span>
			<span class="text-xs text-ink-500">
				{jobSlo.window_hours}h window | target {jobSlo.target_success_rate_percent.toFixed(2)}%
			</span>
		</div>

		<div class="overflow-x-auto">
			<table class="table">
				<thead>
					<tr>
						<th>Job Type</th>
						<th>Success</th>
						<th>Failed</th>
						<th>Rate</th>
						<th>P95 Duration</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
					{#if jobSlo.metrics.length === 0}
						<tr>
							<td colspan="6" class="text-ink-400 text-center py-4">
								No jobs found in this window yet.
							</td>
						</tr>
					{:else}
						{#each jobSlo.metrics as metric (metric.job_type)}
							<tr>
								<td class="text-sm">{metric.job_type}</td>
								<td class="text-sm text-ink-200">{metric.successful_jobs}/{metric.total_jobs}</td>
								<td class="text-sm text-danger-400">{metric.failed_jobs}</td>
								<td class="text-sm">{metric.success_rate_percent.toFixed(2)}%</td>
								<td class="text-sm">{formatDuration(metric.p95_duration_seconds ?? null)}</td>
								<td>
									<span class={jobSloMetricBadgeClass(metric)}>
										{metric.meets_slo ? 'On Target' : 'Off Target'}
									</span>
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="text-sm text-ink-400">
			Job SLO metrics are unavailable (admin-only) or no data exists yet.
		</p>
	{/if}
</div>
