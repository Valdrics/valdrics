<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';

	let {
		loadingPlatform,
		loadingHybrid,
		platformConnections,
		hybridConnections,
		verifyingCloudPlus,
		creatingPlatform,
		creatingHybrid,
		platformName = $bindable(),
		platformVendor = $bindable(),
		platformAuthMethod = $bindable(),
		platformApiKey = $bindable(),
		platformApiSecret = $bindable(),
		platformConnectorConfig = $bindable(),
		platformFeedInput = $bindable(),
		hybridName = $bindable(),
		hybridVendor = $bindable(),
		hybridAuthMethod = $bindable(),
		hybridApiKey = $bindable(),
		hybridApiSecret = $bindable(),
		hybridConnectorConfig = $bindable(),
		hybridFeedInput = $bindable(),
		canUseCloudPlusFeatures,
		createCloudPlusConnection,
		verifyCloudPlusConnection,
		deleteConnection
	} = $props();
</script>

<!-- Platform -->
<div class="glass-panel stagger-enter" style="animation-delay: 500ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="platform" size={40} />
			<div>
				<h3 class="font-bold text-lg">Platform</h3>
				<p class="text-xs text-ink-500">Cloud+ Internal Spend</p>
			</div>
		</div>
		{#if loadingPlatform}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if platformConnections.length > 0}
			<span class="badge badge-accent">Connected ({platformConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if platformConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each platformConnections as conn (conn.id)}
				<div class="p-3 rounded-xl bg-ink-900/50 border border-ink-800">
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="text-xs text-ink-300 font-semibold">{conn.name || 'Platform Feed'}</div>
							<div class="text-xs text-ink-500 font-mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="px-2 py-1 rounded-lg text-xs font-semibold bg-accent-500/10 text-accent-300 hover:bg-accent-500/20 transition-all"
								onclick={() => verifyCloudPlusConnection('platform', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
								onclick={() => deleteConnection('platform', conn.id)}
								title="Delete Connection"
							>
								<span class="text-xs">🗑️</span>
							</button>
						</div>
					</div>
					<div class="flex justify-between text-xs">
						<span class="text-ink-500">Auth Method:</span>
						<span class="text-accent-400">{conn.auth_method || 'manual'}</span>
					</div>
					<div class="flex justify-between text-xs mt-1">
						<span class="text-ink-500">Status:</span>
						<span class={conn.is_active ? 'text-success-400' : 'text-warning-400'}>
							{conn.is_active ? 'active' : 'pending verification'}
						</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if canUseCloudPlusFeatures()}
		<details class="rounded-xl border border-ink-800 bg-ink-900/40 p-3 space-y-3">
			<summary class="cursor-pointer text-xs font-semibold text-ink-200">
				{platformConnections.length > 0
					? 'Add another Platform connector'
					: 'Create Platform connector'}
			</summary>
			<div class="space-y-3 mt-3">
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Connection name (e.g. Shared Platform Ledger)"
					bind:value={platformName}
				/>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Vendor label (internal_platform, kubernetes, shared_services, etc.)"
					bind:value={platformVendor}
				/>
				<select
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					bind:value={platformAuthMethod}
				>
					<option value="api_key">API key (Native)</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				{#if platformAuthMethod === 'api_key'}
					<input
						class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
						type="password"
						placeholder="API key / username / app credential id"
						bind:value={platformApiKey}
					/>
					{#if platformVendor.toLowerCase() === 'datadog'}
						<input
							class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
							type="password"
							placeholder="Application key (api_secret)"
							bind:value={platformApiSecret}
						/>
					{/if}
				{/if}
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-20 font-mono"
					placeholder={`Connector config JSON (ledger_http: {"base_url":"https://ledger.company.com","costs_path":"/api/v1/finops/costs"} | datadog/newrelic: {"unit_prices_usd":{...}} )`}
					bind:value={platformConnectorConfig}
				></textarea>
				{#if platformAuthMethod !== 'api_key'}
					<textarea
						class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-24 font-mono"
						placeholder="Spend feed JSON array for manual/csv mode"
						bind:value={platformFeedInput}
					></textarea>
				{/if}
				<button
					type="button"
					class="btn btn-secondary text-xs w-full"
					onclick={() => createCloudPlusConnection('platform')}
					disabled={creatingPlatform}
				>
					{creatingPlatform ? 'Creating...' : 'Create & Verify Platform Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingPlatform}
		<p class="text-xs text-ink-400 mb-4">
			Connect internal platform spend feeds to include shared services in allocation and reconciliation
			workflows.
		</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full"
				>Upgrade for Platform Connectors</a
			>
			<span class="badge badge-warning text-xs w-full justify-center">Pro Tier Required</span>
		</div>
	{/if}
</div>

<!-- Hybrid -->
<div class="glass-panel stagger-enter" style="animation-delay: 600ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="hybrid" size={40} />
			<div>
				<h3 class="font-bold text-lg">Hybrid</h3>
				<p class="text-xs text-ink-500">Cloud+ Private Infra</p>
			</div>
		</div>
		{#if loadingHybrid}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if hybridConnections.length > 0}
			<span class="badge badge-accent">Connected ({hybridConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if hybridConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each hybridConnections as conn (conn.id)}
				<div class="p-3 rounded-xl bg-ink-900/50 border border-ink-800">
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="text-xs text-ink-300 font-semibold">{conn.name || 'Hybrid Feed'}</div>
							<div class="text-xs text-ink-500 font-mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="px-2 py-1 rounded-lg text-xs font-semibold bg-accent-500/10 text-accent-300 hover:bg-accent-500/20 transition-all"
								onclick={() => verifyCloudPlusConnection('hybrid', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
								onclick={() => deleteConnection('hybrid', conn.id)}
								title="Delete Connection"
							>
								<span class="text-xs">🗑️</span>
							</button>
						</div>
					</div>
					<div class="flex justify-between text-xs">
						<span class="text-ink-500">Auth Method:</span>
						<span class="text-accent-400">{conn.auth_method || 'manual'}</span>
					</div>
					<div class="flex justify-between text-xs mt-1">
						<span class="text-ink-500">Status:</span>
						<span class={conn.is_active ? 'text-success-400' : 'text-warning-400'}>
							{conn.is_active ? 'active' : 'pending verification'}
						</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if canUseCloudPlusFeatures()}
		<details class="rounded-xl border border-ink-800 bg-ink-900/40 p-3 space-y-3">
			<summary class="cursor-pointer text-xs font-semibold text-ink-200">
				{hybridConnections.length > 0 ? 'Add another Hybrid connector' : 'Create Hybrid connector'}
			</summary>
			<div class="space-y-3 mt-3">
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Connection name (e.g. Datacenter Ledger)"
					bind:value={hybridName}
				/>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Vendor label (datacenter, colo, private_cloud, etc.)"
					bind:value={hybridVendor}
				/>
				<select
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					bind:value={hybridAuthMethod}
				>
					<option value="api_key">API key (Native)</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				{#if hybridAuthMethod === 'api_key'}
					<input
						class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
						type="password"
						placeholder="API key / username / app credential id"
						bind:value={hybridApiKey}
					/>
					{#if ['openstack', 'cloudkitty', 'vmware', 'vcenter', 'vsphere'].includes(hybridVendor.toLowerCase())}
						<input
							class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
							type="password"
							placeholder="Second secret (api_secret)"
							bind:value={hybridApiSecret}
						/>
					{/if}
				{/if}
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-20 font-mono"
					placeholder={`Connector config JSON (ledger_http: {"base_url":"https://ledger.company.com"} | cloudkitty: {"auth_url":"...","cloudkitty_base_url":"..."} | vmware: {"base_url":"...","cpu_hour_usd":0.1,"ram_gb_hour_usd":0.01})`}
					bind:value={hybridConnectorConfig}
				></textarea>
				{#if hybridAuthMethod !== 'api_key'}
					<textarea
						class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-24 font-mono"
						placeholder="Spend feed JSON array for manual/csv mode"
						bind:value={hybridFeedInput}
					></textarea>
				{/if}
				<button
					type="button"
					class="btn btn-secondary text-xs w-full"
					onclick={() => createCloudPlusConnection('hybrid')}
					disabled={creatingHybrid}
				>
					{creatingHybrid ? 'Creating...' : 'Create & Verify Hybrid Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingHybrid}
		<p class="text-xs text-ink-400 mb-4">
			Connect private/hybrid infrastructure spend feeds to include on-prem and colo costs in FinOps
			reporting.
		</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full"
				>Upgrade for Hybrid Connectors</a
			>
			<span class="badge badge-warning text-xs w-full justify-center">Pro Tier Required</span>
		</div>
	{/if}
</div>
