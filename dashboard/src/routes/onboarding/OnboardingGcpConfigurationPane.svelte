<script lang="ts">
	let {
		gcpProjectId = $bindable(),
		gcpBillingProjectId = $bindable(),
		gcpBillingDataset = $bindable(),
		gcpBillingTable = $bindable(),
		cloudShellSnippet
	} = $props();
</script>

<h2>Step 2: Connect Google Cloud</h2>
<p class="mb-6">Connect using <strong>Identity Federation</strong>.</p>

<div class="form-group mb-5">
	<label for="gcpProject">GCP Project ID</label>
	<input type="text" id="gcpProject" bind:value={gcpProjectId} placeholder="my-awesome-project" />
</div>

<div class="p-4 rounded-xl bg-ink-900 border border-ink-800 mb-8">
	<h4 class="text-xs font-bold text-accent-400 uppercase tracking-wider mb-4">
		BigQuery Cost Export (Required for FinOps)
	</h4>
	<div class="space-y-4">
		<div class="form-group">
			<label for="gcpBillingProject">Billing Data Project ID (Optional)</label>
			<input
				type="text"
				id="gcpBillingProject"
				bind:value={gcpBillingProjectId}
				placeholder={gcpProjectId || 'GCP Project ID'}
			/>
			<p class="text-xs text-ink-500">
				Project where the BigQuery dataset resides (defaults to the project ID above).
			</p>
		</div>
		<div class="form-group">
			<label for="gcpBillingDataset">BigQuery Dataset ID</label>
			<input
				type="text"
				id="gcpBillingDataset"
				bind:value={gcpBillingDataset}
				placeholder="billing_dataset"
			/>
		</div>
		<div class="form-group">
			<label for="gcpBillingTable">BigQuery Table ID</label>
			<input
				type="text"
				id="gcpBillingTable"
				bind:value={gcpBillingTable}
				placeholder="gcp_billing_export_resource_v1_..."
			/>
		</div>
	</div>
</div>

<div class="info-box mb-6">
	<h4 class="text-sm font-bold mb-2">🚀 Magic Snippet</h4>
	<p class="text-xs text-ink-400 mb-3">Run this gcloud command in your GCP Console.</p>
	<div class="bg-black/50 p-3 rounded font-mono text-xs break-all text-yellow-400">
		{cloudShellSnippet || '# Establishing Workload Identity Trust... (Wait for initialization)'}
	</div>
</div>
