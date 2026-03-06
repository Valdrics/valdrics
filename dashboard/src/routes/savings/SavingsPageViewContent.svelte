<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import type { SavingsProofDrilldownResponse, SavingsProofResponse } from './savingsTypes';

	interface Props {
		data: {
			user?: unknown;
			subscription?: {
				tier?: string;
			};
		};
		loading: boolean;
		downloading: boolean;
		error: string;
		success: string;
		report: SavingsProofResponse | null;
		drilldown: SavingsProofDrilldownResponse | null;
		drilldownDimension: 'strategy_type' | 'remediation_action';
		provider: string;
		datePreset: string;
		dateRange: {
			startDate: string;
			endDate: string;
		};
		isProPlus: (tierValue: string | null | undefined) => boolean;
		formatUsd: (value: number) => string;
		formatDate: (value: string) => string;
		loadReport: () => Promise<void>;
		loadDrilldown: () => Promise<void>;
		downloadCsv: () => Promise<void>;
	}

	let {
		data,
		loading,
		downloading,
		error,
		success,
		report,
		drilldown,
		drilldownDimension = $bindable(),
		provider = $bindable(),
		datePreset = $bindable(),
		dateRange = $bindable(),
		isProPlus,
		formatUsd,
		formatDate,
		loadReport,
		loadDrilldown,
		downloadCsv
	}: Props = $props();
</script>

<div class="space-y-8">
	<div class="flex items-center justify-between gap-4 flex-wrap">
		<div>
			<h1 class="text-2xl font-bold mb-1">Savings Proof</h1>
			<p class="text-ink-400 text-sm">
				A procurement-friendly snapshot of savings opportunity vs realized actions.
			</p>
		</div>
	</div>

	<AuthGate authenticated={!!data.user} action="view savings proof">
		<div
			class="card stagger-enter relative"
			class:opacity-60={!isProPlus(data.subscription?.tier)}
			class:pointer-events-none={!isProPlus(data.subscription?.tier)}
		>
			<div class="flex items-center justify-between gap-3 mb-5 flex-wrap">
				<div class="flex items-center gap-3 flex-wrap">
					<DateRangePicker
						bind:value={datePreset}
						onDateChange={(dates) => {
							dateRange = dates;
							void loadReport();
						}}
					/>
					<div class="form-group">
						<label class="sr-only" for="provider">Provider</label>
						<select id="provider" bind:value={provider} class="select" onchange={() => void loadReport()}>
							<option value="">All providers</option>
							<option value="aws">AWS</option>
							<option value="azure">Azure</option>
							<option value="gcp">GCP</option>
							<option value="saas">SaaS</option>
							<option value="license">License</option>
							<option value="platform">Platform</option>
							<option value="hybrid">Hybrid</option>
						</select>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<button type="button" class="btn btn-secondary" onclick={loadReport} disabled={loading}>
						Refresh
					</button>
					<button
						type="button"
						class="btn btn-primary"
						onclick={downloadCsv}
						disabled={downloading || loading}
					>
						{downloading ? 'Exporting…' : 'Download CSV'}
					</button>
				</div>
			</div>

			{#if !isProPlus(data.subscription?.tier)}
				<div class="absolute inset-0 z-10 flex items-center justify-center bg-transparent">
					<a href={`${base}/billing`} class="btn btn-primary shadow-lg pointer-events-auto">
						Upgrade to Unlock Savings Proof
					</a>
				</div>
			{/if}

			{#if error}
				<div role="alert" class="mb-4 rounded-lg border border-danger-500/40 bg-danger-500/10 p-3">
					<p class="text-danger-300 text-sm">{error}</p>
				</div>
			{/if}

			{#if success}
				<div role="status" class="mb-4 rounded-lg border border-success-500/40 bg-success-500/10 p-3">
					<p class="text-success-300 text-sm">{success}</p>
				</div>
			{/if}

			{#if loading}
				<div class="skeleton h-5 w-56 mb-3"></div>
				<div class="skeleton h-24 w-full"></div>
			{:else if !report}
				<p class="text-sm text-ink-400">No report available.</p>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500 uppercase tracking-wide">Opportunity (Monthly)</p>
						<p class="text-xl font-bold mt-2">{formatUsd(report.opportunity_monthly_usd)}</p>
					</div>
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500 uppercase tracking-wide">Realized (Monthly)</p>
						<p class="text-xl font-bold mt-2">{formatUsd(report.realized_monthly_usd)}</p>
					</div>
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500 uppercase tracking-wide">Open Recommendations</p>
						<p class="text-xl font-bold mt-2">{report.open_recommendations}</p>
					</div>
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500 uppercase tracking-wide">Completed Remediations</p>
						<p class="text-xl font-bold mt-2">{report.completed_remediations}</p>
					</div>
				</div>

				<div class="mt-6 rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
					<div class="flex items-center justify-between flex-wrap gap-2 mb-3">
						<h2 class="text-lg font-semibold">Breakdown</h2>
						<p class="text-xs text-ink-500">As of {formatDate(report.as_of)} • Tier {report.tier}</p>
					</div>

					<div class="overflow-x-auto">
						<table class="table">
							<thead>
								<tr>
									<th>Provider</th>
									<th>Opportunity (Monthly)</th>
									<th>Realized (Monthly)</th>
									<th>Open</th>
									<th>Applied</th>
									<th>Pending</th>
									<th>Completed</th>
								</tr>
							</thead>
							<tbody>
								{#each report.breakdown as row (row.provider)}
									<tr>
										<td class="font-mono text-xs">{row.provider}</td>
										<td>{formatUsd(row.opportunity_monthly_usd)}</td>
										<td>{formatUsd(row.realized_monthly_usd)}</td>
										<td>{row.open_recommendations}</td>
										<td>{row.applied_recommendations}</td>
										<td>{row.pending_remediations}</td>
										<td>{row.completed_remediations}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>

				<div class="mt-6 rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
					<div class="flex items-center justify-between flex-wrap gap-3 mb-3">
						<div>
							<h2 class="text-lg font-semibold">Drilldown</h2>
							<p class="text-xs text-ink-500">
								Break down savings proof by category for faster investigation.
							</p>
						</div>
						<div class="flex items-center gap-2">
							<select
								class="select"
								bind:value={drilldownDimension}
								onchange={() => void loadDrilldown()}
								aria-label="Drilldown dimension"
							>
								<option value="strategy_type">Strategy type</option>
								<option value="remediation_action">Remediation action</option>
							</select>
							<button
								type="button"
								class="btn btn-secondary"
								onclick={loadDrilldown}
								disabled={!report || loading}
							>
								Refresh
							</button>
						</div>
					</div>

					{#if !drilldown}
						<p class="text-sm text-ink-400">No drilldown available.</p>
					{:else}
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
							<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
								<p class="text-xs text-ink-500 uppercase tracking-wide">Opportunity (Monthly)</p>
								<p class="text-xl font-bold mt-2">{formatUsd(drilldown.opportunity_monthly_usd)}</p>
							</div>
							<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
								<p class="text-xs text-ink-500 uppercase tracking-wide">Realized (Monthly)</p>
								<p class="text-xl font-bold mt-2">{formatUsd(drilldown.realized_monthly_usd)}</p>
							</div>
							<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
								<p class="text-xs text-ink-500 uppercase tracking-wide">Buckets</p>
								<p class="text-xl font-bold mt-2">{(drilldown.buckets ?? []).length}</p>
							</div>
							<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
								<p class="text-xs text-ink-500 uppercase tracking-wide">Truncated</p>
								<p class="text-xl font-bold mt-2">{drilldown.truncated ? 'Yes' : 'No'}</p>
							</div>
						</div>

						<div class="overflow-x-auto">
							<table class="table">
								<thead>
									<tr>
										<th>Key</th>
										<th>Opportunity (Monthly)</th>
										<th>Realized (Monthly)</th>
										<th>Open</th>
										<th>Applied</th>
										<th>Pending</th>
										<th>Completed</th>
									</tr>
								</thead>
								<tbody>
									{#each drilldown.buckets ?? [] as row (row.key)}
										<tr>
											<td class="font-mono text-xs">{row.key}</td>
											<td>{formatUsd(row.opportunity_monthly_usd)}</td>
											<td>{formatUsd(row.realized_monthly_usd)}</td>
											<td>{row.open_recommendations}</td>
											<td>{row.applied_recommendations}</td>
											<td>{row.pending_remediations}</td>
											<td>{row.completed_remediations}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>

				{#if report.notes?.length}
					<div class="mt-6 rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<h3 class="text-sm font-semibold mb-2">Notes</h3>
						<ul class="list-disc ml-5 text-sm text-ink-400 space-y-1">
							{#each report.notes as note (note)}
								<li>{note}</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/if}
		</div>
	</AuthGate>
</div>
