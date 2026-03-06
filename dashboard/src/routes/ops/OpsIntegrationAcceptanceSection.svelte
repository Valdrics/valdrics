<script lang="ts">
	import type { IntegrationAcceptanceCaptureResponse, IntegrationAcceptanceRun } from './opsTypes';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		runningAcceptanceSuite: boolean;
		capturingAcceptanceRuns: boolean;
		capturingAcceptanceKpis: boolean;
		refreshingAcceptanceRuns: boolean;
		refreshingAcceptanceKpiHistory: boolean;
		captureIncludeSlack: boolean;
		captureIncludeJira: boolean;
		captureIncludeWorkflow: boolean;
		captureFailFast: boolean;
		runAcceptanceSuite: AsyncAction;
		captureAcceptanceRuns: AsyncAction;
		refreshAcceptanceRuns: AsyncAction;
		lastAcceptanceCapture: IntegrationAcceptanceCaptureResponse | null;
		acceptanceRuns: IntegrationAcceptanceRun[];
		hasSelectedAcceptanceChannels: (includeSlack: boolean, includeJira: boolean, includeWorkflow: boolean) => boolean;
		acceptanceRunStatusClass: (status: string) => string;
		formatDate: (value: string | null | undefined) => string;
	}

	let {
		runningAcceptanceSuite,
		capturingAcceptanceRuns,
		capturingAcceptanceKpis,
		refreshingAcceptanceRuns,
		refreshingAcceptanceKpiHistory,
		captureIncludeSlack = $bindable(),
		captureIncludeJira = $bindable(),
		captureIncludeWorkflow = $bindable(),
		captureFailFast = $bindable(),
		runAcceptanceSuite,
		captureAcceptanceRuns,
		refreshAcceptanceRuns,
		lastAcceptanceCapture,
		acceptanceRuns,
		hasSelectedAcceptanceChannels,
		acceptanceRunStatusClass,
		formatDate
	}: Props = $props();
</script>

<div class="card space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Integration Acceptance Runs</h2>
			<p class="text-xs text-ink-400">
				Latest tenant-scoped Slack/Jira/workflow connectivity evidence captured in audit logs.
			</p>
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="btn btn-primary text-xs"
				disabled={runningAcceptanceSuite ||
					capturingAcceptanceRuns ||
					capturingAcceptanceKpis ||
					refreshingAcceptanceRuns ||
					refreshingAcceptanceKpiHistory ||
					!hasSelectedAcceptanceChannels(captureIncludeSlack, captureIncludeJira, captureIncludeWorkflow)}
				onclick={runAcceptanceSuite}
			>
				{runningAcceptanceSuite ? 'Running...' : 'Run Full Suite'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={capturingAcceptanceRuns ||
					refreshingAcceptanceRuns ||
					!hasSelectedAcceptanceChannels(captureIncludeSlack, captureIncludeJira, captureIncludeWorkflow)}
				onclick={captureAcceptanceRuns}
			>
				{capturingAcceptanceRuns ? 'Running...' : 'Run Checks'}
			</button>
			<button
				type="button"
				class="btn btn-secondary text-xs"
				disabled={refreshingAcceptanceRuns || capturingAcceptanceRuns}
				onclick={refreshAcceptanceRuns}
			>
				{refreshingAcceptanceRuns ? 'Refreshing...' : 'Refresh Runs'}
			</button>
		</div>
	</div>
	<div class="grid gap-3 md:grid-cols-4">
		<label class="flex items-center gap-2 text-xs text-ink-300 cursor-pointer">
			<input
				type="checkbox"
				class="toggle"
				aria-label="Include Slack checks"
				bind:checked={captureIncludeSlack}
				disabled={capturingAcceptanceRuns}
			/>
			<span>Include Slack</span>
		</label>
		<label class="flex items-center gap-2 text-xs text-ink-300 cursor-pointer">
			<input
				type="checkbox"
				class="toggle"
				aria-label="Include Jira checks"
				bind:checked={captureIncludeJira}
				disabled={capturingAcceptanceRuns}
			/>
			<span>Include Jira</span>
		</label>
		<label class="flex items-center gap-2 text-xs text-ink-300 cursor-pointer">
			<input
				type="checkbox"
				class="toggle"
				aria-label="Include Workflow checks"
				bind:checked={captureIncludeWorkflow}
				disabled={capturingAcceptanceRuns}
			/>
			<span>Include Workflow</span>
		</label>
		<label class="flex items-center gap-2 text-xs text-ink-300 cursor-pointer">
			<input
				type="checkbox"
				class="toggle"
				aria-label="Fail fast checks"
				bind:checked={captureFailFast}
				disabled={capturingAcceptanceRuns}
			/>
			<span>Fail fast</span>
		</label>
	</div>
	{#if lastAcceptanceCapture}
		<div class="rounded-lg border border-ink-700/60 bg-ink-900/30 px-3 py-2 text-xs">
			<div class="flex flex-wrap items-center gap-2">
				<span class={acceptanceRunStatusClass(lastAcceptanceCapture.overall_status)}>
					{lastAcceptanceCapture.overall_status.replaceAll('_', ' ').toUpperCase()}
				</span>
				<span class="text-ink-400">
					Last run {lastAcceptanceCapture.run_id.slice(0, 8)}...: {lastAcceptanceCapture.passed}
					passed / {lastAcceptanceCapture.failed} failed
				</span>
			</div>
		</div>
	{/if}
	{#if acceptanceRuns.length > 0}
		<div class="overflow-x-auto">
			<table class="table">
				<thead>
					<tr>
						<th>Run</th>
						<th>Status</th>
						<th>Channels</th>
						<th>Actor</th>
						<th>Captured</th>
					</tr>
				</thead>
				<tbody>
					{#each acceptanceRuns.slice(0, 10) as run (run.runId)}
						<tr>
							<td class="font-mono text-xs">{run.runId.slice(0, 8)}...</td>
							<td>
								<div class="flex items-center gap-2">
									<span class={acceptanceRunStatusClass(run.overallStatus)}>
										{run.overallStatus.replaceAll('_', ' ').toUpperCase()}
									</span>
									<span class="text-xs text-ink-500">
										{run.passed} passed / {run.failed} failed
									</span>
								</div>
							</td>
							<td>
								<div class="flex flex-wrap gap-1">
									{#each run.channels as channel (channel.channel)}
										<span
											class={channel.success ? 'badge badge-success' : 'badge badge-error'}
											title={channel.message || ''}
										>
											{channel.channel}: {channel.success ? 'OK' : 'FAIL'}
										</span>
									{/each}
								</div>
								{#if run.channels.length === 0}
									<span class="text-xs text-ink-500">
										{run.checkedChannels.join(', ') || 'No channels recorded'}
									</span>
								{/if}
							</td>
							<td class="text-xs text-ink-500">{run.actorEmail || '-'}</td>
							<td class="text-xs text-ink-500">{formatDate(run.capturedAt)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="text-sm text-ink-400">
			No integration acceptance runs captured yet. Use Settings -> Notifications to run tests.
		</p>
	{/if}
</div>
