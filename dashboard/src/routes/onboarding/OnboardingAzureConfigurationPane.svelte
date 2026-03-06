<script lang="ts">
	let {
		azureSubscriptionId = $bindable(),
		azureTenantId = $bindable(),
		azureClientId = $bindable(),
		cloudShellSnippet
	} = $props();
</script>

<h2>Step 2: Connect Microsoft Azure</h2>
<p class="mb-6">Connect using <strong>Workload Identity Federation</strong> (Zero-Secret).</p>

<div class="space-y-4 mb-8">
	<div class="form-group">
		<label for="azTenant">Azure Tenant ID</label>
		<input
			type="text"
			id="azTenant"
			bind:value={azureTenantId}
			placeholder="00000000-0000-0000-0000-000000000000"
		/>
	</div>
	<div class="form-group">
		<label for="azSub">Subscription ID</label>
		<input
			type="text"
			id="azSub"
			bind:value={azureSubscriptionId}
			placeholder="00000000-0000-0000-0000-000000000000"
		/>
	</div>
	<div class="form-group">
		<label for="azClient">Application (Client) ID</label>
		<input
			type="text"
			id="azClient"
			bind:value={azureClientId}
			placeholder="00000000-0000-0000-0000-000000000000"
		/>
	</div>
</div>

<div class="info-box mb-6">
	<h4 class="text-sm font-bold mb-2">🚀 Magic Snippet</h4>
	<p class="text-xs text-ink-400 mb-3">
		Copy and paste this into your Azure Cloud Shell to establish trust.
	</p>
	<div class="bg-black/50 p-3 rounded font-mono text-xs break-all text-green-400">
		{cloudShellSnippet || '# Establishing Workload Identity Trust... (Wait for initialization)'}
	</div>
</div>
