<script lang="ts">
	import {
		formatCircuitState,
		formatSafetyDate,
		safetyUsagePercent,
		type SafetyStatus
	} from './settingsPageSchemas';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		loadingSafety: boolean;
		resettingSafety: boolean;
		loadSafetyStatus: AsyncAction;
		resetSafetyCircuitBreaker: AsyncAction;
		safetyError: string;
		safetySuccess: string;
		safetyStatus: SafetyStatus | null;
	}

	let {
		loadingSafety,
		resettingSafety,
		loadSafetyStatus,
		resetSafetyCircuitBreaker,
		safetyError,
		safetySuccess,
		safetyStatus
	}: Props = $props();
</script>

<!-- Safety Controls -->
<div class="card stagger-enter">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold flex items-center gap-2">
			<span>🛡️</span> Remediation Safety Controls
		</h2>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="btn btn-ghost"
				onclick={loadSafetyStatus}
				disabled={loadingSafety || resettingSafety}
				aria-label="Refresh remediation safety status"
			>
				{loadingSafety ? 'Refreshing...' : 'Refresh'}
			</button>
			<button
				type="button"
				class="btn btn-secondary"
				onclick={resetSafetyCircuitBreaker}
				disabled={loadingSafety || resettingSafety}
				aria-label="Reset remediation circuit breaker"
			>
				{resettingSafety ? 'Resetting...' : 'Reset Circuit Breaker'}
			</button>
		</div>
	</div>
	<p class="text-xs text-ink-400 mb-4">
		Tracks runtime safety state for auto-remediation. Reset requires admin role and records an audit
		event.
	</p>

	{#if safetyError}
		<div
			class="mb-4 rounded-lg border border-danger-500/50 bg-danger-500/10 p-3 text-sm text-danger-400"
		>
			{safetyError}
		</div>
	{/if}
	{#if safetySuccess}
		<div
			class="mb-4 rounded-lg border border-success-500/50 bg-success-500/10 p-3 text-sm text-success-400"
		>
			{safetySuccess}
		</div>
	{/if}

	{#if loadingSafety}
		<div class="skeleton h-20 w-full"></div>
	{:else if safetyStatus}
		<div class="space-y-4">
			<div class="grid grid-cols-1 md:grid-cols-4 gap-3">
				<div class="rounded-lg border border-ink-700 p-3">
					<p class="text-xs uppercase tracking-wide text-ink-500 mb-1">Circuit State</p>
					<span
						class="badge"
						class:badge-success={safetyStatus.circuit_state === 'closed'}
						class:badge-warning={safetyStatus.circuit_state === 'half_open'}
						class:badge-error={['open', 'unknown'].includes(safetyStatus.circuit_state)}
					>
						{formatCircuitState(safetyStatus.circuit_state)}
					</span>
				</div>

				<div class="rounded-lg border border-ink-700 p-3">
					<p class="text-xs uppercase tracking-wide text-ink-500 mb-1">Execution</p>
					<p class={safetyStatus.can_execute ? 'text-success-400' : 'text-danger-400'}>
						{safetyStatus.can_execute ? 'Allowed' : 'Blocked'}
					</p>
				</div>

				<div class="rounded-lg border border-ink-700 p-3">
					<p class="text-xs uppercase tracking-wide text-ink-500 mb-1">Failure Count</p>
					<p class="text-white">{safetyStatus.failure_count}</p>
				</div>

				<div class="rounded-lg border border-ink-700 p-3">
					<p class="text-xs uppercase tracking-wide text-ink-500 mb-1">Last Failure</p>
					<p class="text-white text-xs">{formatSafetyDate(safetyStatus.last_failure_at)}</p>
				</div>
			</div>

			<div class="rounded-lg border border-ink-700 p-3">
				<div class="flex items-center justify-between text-xs text-ink-400 mb-2">
					<span>Daily Savings Guardrail</span>
					<span>
						${safetyStatus.daily_savings_used.toFixed(2)} / ${safetyStatus.daily_savings_limit.toFixed(
							2
						)}
					</span>
				</div>
				<div class="h-2 w-full bg-ink-800 rounded-full overflow-hidden">
					<div
						class="h-full rounded-full transition-all duration-500"
						class:bg-success-500={safetyUsagePercent(safetyStatus) < 70}
						class:bg-warning-500={safetyUsagePercent(safetyStatus) >= 70 &&
							safetyUsagePercent(safetyStatus) < 90}
						class:bg-danger-500={safetyUsagePercent(safetyStatus) >= 90}
						style="width: {safetyUsagePercent(safetyStatus)}%"
					></div>
				</div>
				<p class="mt-1 text-right text-xs text-ink-500">
					{safetyUsagePercent(safetyStatus).toFixed(1)}% used
				</p>
			</div>
		</div>
	{/if}
</div>
