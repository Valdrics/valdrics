<script lang="ts">
	import type { IngestionSLAResponse } from './opsTypes';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		ingestionSlaWindowHours: number;
		refreshingIngestionSla: boolean;
		refreshIngestionSla: AsyncAction;
		ingestionSla: IngestionSLAResponse | null;
		ingestionSlaBadgeClass: (value: IngestionSLAResponse) => string;
		formatNumber: (value: number | null | undefined, digits?: number) => string;
		formatDuration: (value: number | null | undefined) => string;
		formatDate: (value: string | null | undefined) => string;
	}

	let {
		ingestionSlaWindowHours = $bindable(),
		refreshingIngestionSla,
		refreshIngestionSla,
		ingestionSla,
		ingestionSlaBadgeClass,
		formatNumber,
		formatDuration,
		formatDate
	}: Props = $props();
</script>

<div class="card space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Cost Ingestion SLA</h2>
			<p class="text-xs text-ink-400">
				Track ingestion reliability and processing latency against a 95% success target.
			</p>
		</div>
		<div class="flex items-end gap-2">
			<label class="text-xs text-ink-400">
				<span class="block mb-1">Window</span>
				<select class="input text-xs" bind:value={ingestionSlaWindowHours} aria-label="SLA Window">
					<option value={24}>Last 24h</option>
					<option value={72}>Last 72h</option>
					<option value={168}>Last 7d</option>
				</select>
			</label>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingIngestionSla}
				onclick={refreshIngestionSla}
			>
				{refreshingIngestionSla ? 'Refreshing...' : 'Refresh SLA'}
			</button>
		</div>
	</div>

	{#if ingestionSla}
		<div class="flex items-center gap-2">
			<span class={ingestionSlaBadgeClass(ingestionSla)}>
				{ingestionSla.meets_sla ? 'SLA Healthy' : 'SLA At Risk'}
			</span>
			<span class="text-xs text-ink-500">
				{ingestionSla.success_rate_percent.toFixed(2)}% success ({ingestionSla.successful_jobs}/
				{ingestionSla.total_jobs} jobs)
			</span>
		</div>
		<div class="grid gap-3 md:grid-cols-5">
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Jobs (Window)</p>
				<p class="text-2xl font-bold text-ink-100">{ingestionSla.total_jobs}</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Failed Jobs</p>
				<p class="text-2xl font-bold text-danger-400">{ingestionSla.failed_jobs}</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Records Ingested</p>
				<p class="text-2xl font-bold text-accent-400">
					{formatNumber(ingestionSla.records_ingested, 0)}
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Avg Duration</p>
				<p class="text-2xl font-bold text-ink-100">
					{formatDuration(ingestionSla.avg_duration_seconds)}
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">P95 Duration</p>
				<p class="text-2xl font-bold text-warning-400">
					{formatDuration(ingestionSla.p95_duration_seconds)}
				</p>
			</div>
		</div>
		<p class="text-xs text-ink-500">
			Latest completed ingestion: {formatDate(ingestionSla.latest_completed_at)}
		</p>
	{:else}
		<p class="text-sm text-ink-400">
			No ingestion SLA data is available for this window yet.
		</p>
	{/if}
</div>
