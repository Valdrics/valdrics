<script lang="ts">
	import AuthGate from '$lib/components/AuthGate.svelte';
	import type { AuditDetail, AuditLog } from './auditTypes';
	import AuditDetailModal from './AuditDetailModal.svelte';
	import AuditEventsTable from './AuditEventsTable.svelte';

	interface Props {
		data: {
			user?: unknown;
		};
		loading: boolean;
		loadingDetail: boolean;
		exporting: boolean;
		exportingPack: boolean;
		exportingFocus: boolean;
		error: string;
		success: string;
		logs: AuditLog[];
		eventTypes: string[];
		selectedEventType: string;
		limit: number;
		offset: number;
		selectedLogId: string | null;
		selectedDetail: AuditDetail | null;
		focusStartDate: string;
		focusEndDate: string;
		focusProvider: string;
		focusIncludePreliminary: boolean;
		packIncludeFocus: boolean;
		packIncludeSavingsProof: boolean;
		packIncludeClosePackage: boolean;
		packCloseEnforceFinalized: boolean;
		packCloseMaxRestatements: number;
		formatDate: (value: string) => string;
		applyFilters: () => Promise<void>;
		previousPage: () => Promise<void>;
		nextPage: () => Promise<void>;
		exportCsv: () => Promise<void>;
		exportCompliancePack: () => Promise<void>;
		exportFocusCsv: () => Promise<void>;
		viewDetail: (id: string) => Promise<void>;
		closeDetail: () => void;
	}

	let {
		data,
		loading,
		loadingDetail,
		exporting,
		exportingPack,
		exportingFocus,
		error,
		success,
		logs,
		eventTypes,
		selectedEventType = $bindable(),
		limit = $bindable(),
		offset,
		selectedLogId,
		selectedDetail,
		focusStartDate = $bindable(),
		focusEndDate = $bindable(),
		focusProvider = $bindable(),
		focusIncludePreliminary = $bindable(),
		packIncludeFocus = $bindable(),
		packIncludeSavingsProof = $bindable(),
		packIncludeClosePackage = $bindable(),
		packCloseEnforceFinalized = $bindable(),
		packCloseMaxRestatements = $bindable(),
		formatDate,
		applyFilters,
		previousPage,
		nextPage,
		exportCsv,
		exportCompliancePack,
		exportFocusCsv,
		viewDetail,
		closeDetail
	}: Props = $props();
</script>

<div class="space-y-8">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold mb-1">Audit Logs</h1>
			<p class="text-ink-400 text-sm">Security and governance event trail for compliance workflows.</p>
		</div>
	</div>

	<AuthGate authenticated={!!data.user} action="access audit logs" className="card text-center py-10">
		{#if error}
			<div class="card border-danger-500/50 bg-danger-500/10">
				<p class="text-danger-400">{error}</p>
			</div>
		{/if}
		{#if success}
			<div class="card border-success-500/50 bg-success-500/10">
				<p class="text-success-400">{success}</p>
			</div>
		{/if}

		<div class="card">
			<div class="flex flex-wrap gap-3 items-end">
				<div class="flex flex-col gap-1">
					<label class="text-xs text-ink-400 uppercase tracking-wide" for="event-type">Event Type</label>
					<select id="event-type" bind:value={selectedEventType} class="select-input">
						<option value="">All events</option>
						{#each eventTypes as type (type)}
							<option value={type}>{type}</option>
						{/each}
					</select>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs text-ink-400 uppercase tracking-wide" for="limit">Page Size</label>
					<select id="limit" bind:value={limit} class="select-input">
						<option value={20}>20</option>
						<option value={50}>50</option>
						<option value={100}>100</option>
					</select>
				</div>
				<div class="flex gap-2">
					<button type="button" class="btn btn-secondary text-xs" onclick={applyFilters}>Apply</button>
					<button type="button" class="btn btn-secondary text-xs" onclick={previousPage}>Prev</button>
					<button type="button" class="btn btn-secondary text-xs" onclick={nextPage}>Next</button>
					<button
						type="button"
						class="btn btn-primary text-xs"
						disabled={exporting}
						onclick={exportCsv}
					>
						{exporting ? 'Exporting...' : 'Export CSV'}
					</button>
					<button
						type="button"
						class="btn btn-primary text-xs"
						disabled={exportingPack}
						onclick={exportCompliancePack}
					>
						{exportingPack ? 'Exporting...' : 'Compliance Pack'}
					</button>
				</div>
			</div>
		</div>

		<div class="card">
			<h2 class="text-lg font-semibold mb-1">Compliance Exports</h2>
			<p class="text-ink-400 text-sm mb-4">
				Download FOCUS v1.3 core CSV (Pro+) or bundle exports into the Compliance Pack ZIP (Owner).
			</p>
			<div class="flex flex-wrap gap-3 items-end">
				<div class="flex flex-col gap-1">
					<label class="text-xs text-ink-400 uppercase tracking-wide" for="focus-start">Start</label>
					<input id="focus-start" type="date" class="select-input" bind:value={focusStartDate} />
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs text-ink-400 uppercase tracking-wide" for="focus-end">End</label>
					<input id="focus-end" type="date" class="select-input" bind:value={focusEndDate} />
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs text-ink-400 uppercase tracking-wide" for="focus-provider">Provider</label>
					<select id="focus-provider" bind:value={focusProvider} class="select-input">
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
				<label class="flex items-center gap-2 text-xs text-ink-400">
					<input type="checkbox" class="accent-accent-500" bind:checked={focusIncludePreliminary} />
					<span>Include preliminary</span>
				</label>
				<button
					type="button"
					class="btn btn-primary text-xs"
					disabled={exportingFocus}
					onclick={exportFocusCsv}
				>
					{exportingFocus ? 'Exporting...' : 'FOCUS CSV'}
				</button>
			</div>

			<div class="mt-5 border-t border-ink-700/40 pt-4">
				<h3 class="text-sm font-semibold mb-2">Compliance Pack Add-ons</h3>
				<p class="text-ink-400 text-xs mb-3">
					Optional exports included inside the ZIP. Uses the same date/provider filters above.
				</p>
				<div class="flex flex-wrap gap-4 items-center">
					<label class="flex items-center gap-2 text-xs text-ink-300">
						<input type="checkbox" class="accent-accent-500" bind:checked={packIncludeFocus} />
						<span>Include FOCUS CSV</span>
					</label>
					<label class="flex items-center gap-2 text-xs text-ink-300">
						<input type="checkbox" class="accent-accent-500" bind:checked={packIncludeSavingsProof} />
						<span>Include Savings Proof</span>
					</label>
					<label class="flex items-center gap-2 text-xs text-ink-300">
						<input type="checkbox" class="accent-accent-500" bind:checked={packIncludeClosePackage} />
						<span>Include Close Package</span>
					</label>
					{#if packIncludeClosePackage}
						<label class="flex items-center gap-2 text-xs text-ink-300">
							<input
								type="checkbox"
								class="accent-accent-500"
								bind:checked={packCloseEnforceFinalized}
							/>
							<span>Enforce finalized</span>
						</label>
						<label class="flex items-center gap-2 text-xs text-ink-300">
							<span>Max restatements</span>
							<input
								type="number"
								min="0"
								max="200000"
								step="100"
								class="select-input w-28"
								bind:value={packCloseMaxRestatements}
							/>
						</label>
					{/if}
				</div>
			</div>
		</div>

		<AuditEventsTable {loading} {logs} onViewDetail={viewDetail} {formatDate} />
	</AuthGate>
</div>

<AuditDetailModal {selectedLogId} {selectedDetail} {loadingDetail} {closeDetail} {formatDate} />

<style>
	.select-input {
		min-width: 180px;
		border: 1px solid var(--color-ink-700);
		border-radius: 0.5rem;
		background: var(--color-ink-900);
		color: var(--color-ink-100);
		padding: 0.5rem 0.75rem;
	}
</style>
