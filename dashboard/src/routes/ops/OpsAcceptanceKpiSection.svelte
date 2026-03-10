<script lang="ts">
	import type {
		AcceptanceKpiCaptureResponse,
		AcceptanceKpiEvidenceItem,
		AcceptanceKpisResponse
	} from './opsTypes';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		capturingAcceptanceKpis: boolean;
		downloadingAcceptanceJson: boolean;
		downloadingAcceptanceCsv: boolean;
		refreshingAcceptanceKpis: boolean;
		refreshingAcceptanceKpiHistory: boolean;
		captureAcceptanceKpis: AsyncAction;
		downloadAcceptanceKpiJson: AsyncAction;
		downloadAcceptanceKpiCsv: AsyncAction;
		refreshAcceptanceKpis: AsyncAction;
		refreshAcceptanceKpiHistory: AsyncAction;
		acceptanceKpis: AcceptanceKpisResponse | null;
		acceptanceKpiHistory: AcceptanceKpiEvidenceItem[];
		lastAcceptanceKpiCapture: AcceptanceKpiCaptureResponse | null;
		acceptanceBadgeClass: (metric: AcceptanceKpisResponse['metrics'][number]) => string;
		formatDate: (value: string | null | undefined) => string;
	}

	let {
		capturingAcceptanceKpis,
		downloadingAcceptanceJson,
		downloadingAcceptanceCsv,
		refreshingAcceptanceKpis,
		refreshingAcceptanceKpiHistory,
		captureAcceptanceKpis,
		downloadAcceptanceKpiJson,
		downloadAcceptanceKpiCsv,
		refreshAcceptanceKpis,
		refreshAcceptanceKpiHistory,
		acceptanceKpis,
		acceptanceKpiHistory,
		lastAcceptanceKpiCapture,
		acceptanceBadgeClass,
		formatDate
	}: Props = $props();
</script>

<div class="card space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Acceptance KPI Evidence</h2>
			<p class="text-xs text-ink-400">
				Production sign-off signals for ingestion reliability, chargeback coverage, and unit
				economics stability, plus ledger data-quality (normalization + canonical mapping coverage).
			</p>
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="btn btn-primary text-xs"
				disabled={capturingAcceptanceKpis}
				onclick={captureAcceptanceKpis}
			>
				{capturingAcceptanceKpis ? 'Capturing...' : 'Capture KPI Evidence'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={downloadingAcceptanceJson}
				onclick={downloadAcceptanceKpiJson}
			>
				{downloadingAcceptanceJson ? 'Exporting...' : 'Download JSON'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={downloadingAcceptanceCsv}
				onclick={downloadAcceptanceKpiCsv}
			>
				{downloadingAcceptanceCsv ? 'Exporting...' : 'Download CSV'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingAcceptanceKpis}
				onclick={refreshAcceptanceKpis}
			>
				{refreshingAcceptanceKpis ? 'Refreshing...' : 'Refresh KPI Evidence'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingAcceptanceKpiHistory}
				onclick={refreshAcceptanceKpiHistory}
			>
				{refreshingAcceptanceKpiHistory ? 'Refreshing...' : 'Refresh History'}
			</button>
		</div>
	</div>
	{#if acceptanceKpis}
		<div class="flex items-center gap-2">
			<span class={acceptanceKpis.all_targets_met ? 'badge badge-success' : 'badge badge-warning'}>
				{acceptanceKpis.all_targets_met ? 'All Targets Met' : 'Gaps Open'}
			</span>
			<span class="text-xs text-ink-500">
				{acceptanceKpis.start_date} -> {acceptanceKpis.end_date} | Tier {acceptanceKpis.tier.toUpperCase()}
				| {acceptanceKpis.available_metrics} active metrics
			</span>
		</div>
		<div class="overflow-x-auto">
			<table class="table">
				<thead>
					<tr>
						<th>Metric</th>
						<th>Target</th>
						<th>Actual</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
					{#each acceptanceKpis.metrics as metric (metric.key)}
						<tr>
							<td class="text-sm">{metric.label}</td>
							<td class="text-xs text-ink-400">{metric.target}</td>
							<td class="text-xs">{metric.actual}</td>
							<td>
								<span class={acceptanceBadgeClass(metric)}>
									{#if !metric.available}
										Unavailable
									{:else if metric.meets_target}
										On Target
									{:else}
										Off Target
									{/if}
								</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<div class="space-y-2">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<p class="text-xs text-ink-400">Captured snapshots (audit-grade). Latest shown first.</p>
				{#if lastAcceptanceKpiCapture}
					<p class="text-xs text-ink-500">
						Last captured: {formatDate(lastAcceptanceKpiCapture.captured_at)}
					</p>
				{/if}
			</div>
			{#if acceptanceKpiHistory.length > 0}
				<div class="space-y-2">
					{#each acceptanceKpiHistory.slice(0, 5) as item (item.event_id)}
						<div class="flex flex-wrap items-center justify-between gap-2 text-xs">
							<div class="flex items-center gap-2">
								<span class="text-ink-300">{formatDate(item.captured_at)}</span>
								<span
									class={item.acceptance_kpis.all_targets_met
										? 'badge badge-success'
										: 'badge badge-warning'}
								>
									{item.acceptance_kpis.all_targets_met ? 'All Targets Met' : 'Gaps Open'}
								</span>
							</div>
							<span class="text-ink-500"
								>Run {item.run_id ? item.run_id.slice(0, 8) : 'unknown'}</span
							>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-xs text-ink-400">No captured KPI snapshots yet.</p>
			{/if}
		</div>
	{:else}
		<p class="text-sm text-ink-400">Acceptance KPIs are currently unavailable.</p>
	{/if}
</div>
