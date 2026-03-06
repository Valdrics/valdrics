<script lang="ts">
	import type { UnitEconomicsResponse, UnitEconomicsSettings } from './opsTypes';

	type ClickAction = () => void | Promise<void>;
	type SubmitAction = (event?: SubmitEvent) => void | Promise<void>;

	interface Props {
		unitStartDate: string;
		unitEndDate: string;
		unitAlertOnAnomaly: boolean;
		refreshingUnitEconomics: boolean;
		refreshUnitEconomics: ClickAction;
		unitEconomics: UnitEconomicsResponse | null;
		unitSettings: UnitEconomicsSettings | null;
		saveUnitEconomicsSettings: SubmitAction;
		savingUnitSettings: boolean;
		formatUsd: (value: number | null | undefined) => string;
		formatNumber: (value: number | null | undefined, digits?: number) => string;
		formatDelta: (value: number | null | undefined) => string;
		unitDeltaClass: (metric: UnitEconomicsResponse['metrics'][number]) => string;
	}

	let {
		unitStartDate = $bindable(),
		unitEndDate = $bindable(),
		unitAlertOnAnomaly = $bindable(),
		refreshingUnitEconomics,
		refreshUnitEconomics,
		unitEconomics,
		unitSettings = $bindable(),
		saveUnitEconomicsSettings,
		savingUnitSettings,
		formatUsd,
		formatNumber,
		formatDelta,
		unitDeltaClass
	}: Props = $props();
</script>

<div class="card space-y-5">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Unit Economics Monitor</h2>
			<p class="text-xs text-ink-400">
				Track cost-per-request/workload/customer versus a previous window baseline.
			</p>
		</div>
		<div class="flex items-end gap-2">
			<label class="text-xs text-ink-400">
				<span class="block mb-1">Start</span>
				<input class="input text-xs" type="date" bind:value={unitStartDate} />
			</label>
			<label class="text-xs text-ink-400">
				<span class="block mb-1">End</span>
				<input class="input text-xs" type="date" bind:value={unitEndDate} />
			</label>
			<label class="flex items-center gap-2 text-xs text-ink-400 mb-1">
				<input type="checkbox" bind:checked={unitAlertOnAnomaly} />
				Alert on anomaly
			</label>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingUnitEconomics}
				onclick={refreshUnitEconomics}
			>
				{refreshingUnitEconomics ? 'Refreshing...' : 'Refresh Unit Metrics'}
			</button>
		</div>
	</div>

	{#if unitEconomics}
		<div class="grid gap-3 md:grid-cols-4">
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Current Window Cost</p>
				<p class="text-2xl font-bold text-ink-100">{formatUsd(unitEconomics.total_cost)}</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Baseline Cost</p>
				<p class="text-2xl font-bold text-ink-100">
					{formatUsd(unitEconomics.baseline_total_cost)}
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Threshold</p>
				<p class="text-2xl font-bold text-accent-400">
					{unitEconomics.threshold_percent.toFixed(2)}%
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Anomalies</p>
				<p
					class={`text-2xl font-bold ${unitEconomics.anomaly_count > 0 ? 'text-danger-400' : 'text-success-400'}`}
				>
					{unitEconomics.anomaly_count}
				</p>
			</div>
		</div>

		<div class="overflow-x-auto">
			<table class="table">
				<thead>
					<tr>
						<th>Metric</th>
						<th>Denominator</th>
						<th>Current Cost/Unit</th>
						<th>Baseline Cost/Unit</th>
						<th>Delta</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
					{#if unitEconomics.metrics.length === 0}
						<tr>
							<td colspan="6" class="text-ink-400 text-center py-4">
								No unit metrics available for this window.
							</td>
						</tr>
					{:else}
						{#each unitEconomics.metrics as metric (metric.metric_key)}
							<tr>
								<td class="text-sm">{metric.label}</td>
								<td>{formatNumber(metric.denominator, 2)}</td>
								<td>{formatUsd(metric.cost_per_unit)}</td>
								<td>{formatUsd(metric.baseline_cost_per_unit)}</td>
								<td class={unitDeltaClass(metric)}>{formatDelta(metric.delta_percent)}</td>
								<td class={metric.is_anomalous ? 'text-danger-400' : 'text-success-400'}>
									{metric.is_anomalous ? 'Anomalous' : 'Normal'}
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="text-sm text-ink-400">
			Unit economics data is unavailable for the selected window. Try refreshing.
		</p>
	{/if}

	{#if unitSettings}
		<form class="space-y-3" onsubmit={saveUnitEconomicsSettings}>
			<h3 class="text-sm font-semibold text-ink-200">Default Unit Volumes</h3>
			<p class="text-xs text-ink-500">
				Admins can set baseline denominators used when query overrides are not provided.
			</p>
			<div class="grid gap-3 md:grid-cols-4">
				<label class="text-xs text-ink-400">
					<span class="block mb-1">Request Volume</span>
					<input
						class="input text-xs"
						type="number"
						min="0.0001"
						step="0.0001"
						bind:value={unitSettings.default_request_volume}
					/>
				</label>
				<label class="text-xs text-ink-400">
					<span class="block mb-1">Workload Volume</span>
					<input
						class="input text-xs"
						type="number"
						min="0.0001"
						step="0.0001"
						bind:value={unitSettings.default_workload_volume}
					/>
				</label>
				<label class="text-xs text-ink-400">
					<span class="block mb-1">Customer Volume</span>
					<input
						class="input text-xs"
						type="number"
						min="0.0001"
						step="0.0001"
						bind:value={unitSettings.default_customer_volume}
					/>
				</label>
				<label class="text-xs text-ink-400">
					<span class="block mb-1">Anomaly Threshold %</span>
					<input
						class="input text-xs"
						type="number"
						min="0.01"
						step="0.01"
						bind:value={unitSettings.anomaly_threshold_percent}
					/>
				</label>
			</div>
			<div class="flex justify-end">
				<button class="btn btn-primary text-xs" type="submit" disabled={savingUnitSettings}>
					{savingUnitSettings ? 'Saving...' : 'Save Defaults'}
				</button>
			</div>
		</form>
	{/if}
</div>
