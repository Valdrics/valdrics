<script lang="ts">
	import type { ProviderInvoiceForm, ReconciliationClosePackage } from './opsTypes';

	type ClickAction = () => void | Promise<void>;
	type SubmitAction = (event?: SubmitEvent) => void | Promise<void>;

	interface Props {
		closeStartDate: string;
		closeEndDate: string;
		closeProvider: string;
		refreshingClosePackage: boolean;
		downloadingCloseJson: boolean;
		downloadingCloseCsv: boolean;
		downloadingRestatementCsv: boolean;
		previewClosePackage: ClickAction;
		downloadClosePackageJson: ClickAction;
		downloadClosePackageCsv: ClickAction;
		downloadRestatementCsv: ClickAction;
		closePackage: ReconciliationClosePackage | null;
		invoiceForm: ProviderInvoiceForm;
		saveProviderInvoice: SubmitAction;
		savingInvoice: boolean;
		deletingInvoice: boolean;
		deleteProviderInvoice: ClickAction;
		closeStatusBadgeClass: (value: string | null | undefined) => string;
		formatUsd: (value: number | null | undefined) => string;
	}

	let {
		closeStartDate = $bindable(),
		closeEndDate = $bindable(),
		closeProvider = $bindable(),
		refreshingClosePackage,
		downloadingCloseJson,
		downloadingCloseCsv,
		downloadingRestatementCsv,
		previewClosePackage,
		downloadClosePackageJson,
		downloadClosePackageCsv,
		downloadRestatementCsv,
		closePackage = null,
		invoiceForm = $bindable(),
		saveProviderInvoice,
		savingInvoice,
		deletingInvoice,
		deleteProviderInvoice,
		closeStatusBadgeClass,
		formatUsd
	}: Props = $props();
</script>

<div class="card space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-lg font-semibold">Reconciliation Close Workflow</h2>
			<p class="text-xs text-ink-400">
				Preview month-end close readiness and export close/restatement evidence artifacts.
			</p>
		</div>
		<div class="flex items-end gap-2">
			<label class="text-xs text-ink-400">
				<span class="block mb-1">Start</span>
				<input class="input text-xs" type="date" bind:value={closeStartDate} />
			</label>
			<label class="text-xs text-ink-400">
				<span class="block mb-1">End</span>
				<input class="input text-xs" type="date" bind:value={closeEndDate} />
			</label>
			<label class="text-xs text-ink-400">
				<span class="block mb-1">Provider</span>
				<select class="input text-xs" bind:value={closeProvider}>
					<option value="all">All</option>
					<option value="aws">AWS</option>
					<option value="azure">Azure</option>
					<option value="gcp">GCP</option>
					<option value="saas">SaaS</option>
					<option value="license">License</option>
					<option value="platform">Platform</option>
					<option value="hybrid">Hybrid</option>
				</select>
			</label>
		</div>
	</div>

	<div class="flex flex-wrap gap-2">
		<button
			type="button"
			class="btn btn-secondary text-xs"
			disabled={refreshingClosePackage}
			onclick={() => previewClosePackage()}
		>
			{refreshingClosePackage ? 'Refreshing...' : 'Preview Close Status'}
		</button>
		<button
			type="button"
			class="btn btn-secondary text-xs"
			disabled={downloadingCloseJson}
			onclick={downloadClosePackageJson}
		>
			{downloadingCloseJson ? 'Exporting...' : 'Download Close JSON'}
		</button>
		<button
			type="button"
			class="btn btn-secondary text-xs"
			disabled={downloadingCloseCsv}
			onclick={downloadClosePackageCsv}
		>
			{downloadingCloseCsv ? 'Exporting...' : 'Download Close CSV'}
		</button>
		<button
			type="button"
			class="btn btn-secondary text-xs"
			disabled={downloadingRestatementCsv}
			onclick={downloadRestatementCsv}
		>
			{downloadingRestatementCsv ? 'Exporting...' : 'Download Restatements CSV'}
		</button>
	</div>

	{#if closePackage}
		<div class="flex items-center gap-2">
			<span class={closeStatusBadgeClass(closePackage.close_status)}>
				{closePackage.close_status.replaceAll('_', ' ').toUpperCase()}
			</span>
			<span class="text-xs text-ink-500">
				{closePackage.period.start_date} -> {closePackage.period.end_date} | {closePackage.package_version}
			</span>
		</div>
		{#if closePackage.invoice_reconciliation}
			<div class="rounded-lg border border-ink-700/60 bg-ink-900/20 px-3 py-2 text-xs space-y-1">
				<div class="flex flex-wrap items-center gap-2">
					<span class="badge badge-default">Invoice Reconciliation</span>
					<span
						class={`badge ${closePackage.invoice_reconciliation.status === 'match' ? 'badge-success' : closePackage.invoice_reconciliation.status === 'missing_invoice' ? 'badge-warning' : 'badge-error'}`}
					>
						{closePackage.invoice_reconciliation.status.replaceAll('_', ' ').toUpperCase()}
					</span>
					<span class="text-ink-500">
						Threshold {closePackage.invoice_reconciliation.threshold_percent}%
					</span>
				</div>
				{#if closePackage.invoice_reconciliation.invoice}
					<div class="flex flex-wrap gap-3 text-ink-400">
						<span>
							Invoice total (USD): <span class="text-ink-200"
								>{formatUsd(closePackage.invoice_reconciliation.invoice.total_amount_usd)}</span
							>
						</span>
						<span>
							Ledger final (USD): <span class="text-ink-200"
								>{formatUsd(closePackage.invoice_reconciliation.ledger_final_cost_usd || 0)}</span
							>
						</span>
						<span>
							Delta: <span class="text-ink-200"
								>{formatUsd(closePackage.invoice_reconciliation.delta_usd || 0)}</span
							>
						</span>
						<span>
							Delta %: <span class="text-ink-200"
								>{(closePackage.invoice_reconciliation.delta_percent || 0).toFixed(2)}%</span
							>
						</span>
					</div>
				{:else}
					<p class="text-ink-500">
						No invoice stored for this provider/period yet. Add one below to enable invoice-linked
						reconciliation.
					</p>
				{/if}

				<form class="mt-3 grid gap-2 md:grid-cols-6" onsubmit={saveProviderInvoice}>
					<label class="text-xs text-ink-400 md:col-span-2">
						<span class="block mb-1">Invoice #</span>
						<input class="input text-xs" placeholder="Optional" bind:value={invoiceForm.invoice_number} />
					</label>
					<label class="text-xs text-ink-400">
						<span class="block mb-1">Currency</span>
						<input class="input text-xs" placeholder="USD" bind:value={invoiceForm.currency} />
					</label>
					<label class="text-xs text-ink-400">
						<span class="block mb-1">Total</span>
						<input
							class="input text-xs"
							type="number"
							step="0.01"
							min="0"
							bind:value={invoiceForm.total_amount}
						/>
					</label>
					<label class="text-xs text-ink-400">
						<span class="block mb-1">Status</span>
						<select class="input text-xs" bind:value={invoiceForm.status}>
							<option value="submitted">Submitted</option>
							<option value="paid">Paid</option>
							<option value="reconciled">Reconciled</option>
							<option value="disputed">Disputed</option>
							<option value="void">Void</option>
						</select>
					</label>
					<label class="text-xs text-ink-400 md:col-span-6">
						<span class="block mb-1">Notes</span>
						<input class="input text-xs" placeholder="Optional" bind:value={invoiceForm.notes} />
					</label>
					<div class="md:col-span-6 flex flex-wrap items-center gap-2">
						<button class="btn btn-secondary text-xs" type="submit" disabled={savingInvoice}>
							{savingInvoice
								? 'Saving...'
								: closePackage.invoice_reconciliation.invoice
									? 'Update Invoice'
									: 'Save Invoice'}
						</button>
						{#if closePackage.invoice_reconciliation.invoice}
							<button
								class="btn btn-ghost text-xs"
								type="button"
								disabled={deletingInvoice}
								onclick={deleteProviderInvoice}
							>
								{deletingInvoice ? 'Deleting...' : 'Delete'}
							</button>
						{/if}
						<span class="text-xs text-ink-500">
							Note: non-USD invoices require DB exchange rates (Settings -> Billing).
						</span>
					</div>
				</form>
			</div>
		{/if}
		<div class="grid gap-3 md:grid-cols-5">
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Total Records</p>
				<p class="text-2xl font-bold text-ink-100">{closePackage.lifecycle.total_records}</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Preliminary</p>
				<p
					class={`text-2xl font-bold ${closePackage.lifecycle.preliminary_records > 0 ? 'text-warning-400' : 'text-success-400'}`}
				>
					{closePackage.lifecycle.preliminary_records}
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Final</p>
				<p class="text-2xl font-bold text-success-400">{closePackage.lifecycle.final_records}</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Discrepancy %</p>
				<p class="text-2xl font-bold text-warning-400">
					{closePackage.reconciliation.discrepancy_percentage.toFixed(2)}%
				</p>
			</div>
			<div class="card card-stat">
				<p class="text-xs text-ink-400 uppercase tracking-wide">Restatements</p>
				<p class="text-2xl font-bold text-accent-400">{closePackage.restatements.count}</p>
			</div>
		</div>
		<p class="text-xs text-ink-500 font-mono break-all">Integrity hash: {closePackage.integrity_hash}</p>
	{:else}
		<p class="text-sm text-ink-400">
			No close package preview loaded for the selected period/provider yet.
		</p>
	{/if}
</div>
