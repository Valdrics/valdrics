<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';

	let {
		loadingSaaS,
		loadingLicense,
		saasConnections,
		licenseConnections,
		verifyingCloudPlus,
		creatingSaaS,
		creatingLicense,
		saasName = $bindable(),
		saasVendor = $bindable(),
		saasAuthMethod = $bindable(),
		saasApiKey = $bindable(),
		saasConnectorConfig = $bindable(),
		saasFeedInput = $bindable(),
		licenseName = $bindable(),
		licenseVendor = $bindable(),
		licenseAuthMethod = $bindable(),
		licenseApiKey = $bindable(),
		licenseConnectorConfig = $bindable(),
		licenseFeedInput = $bindable(),
		canUseCloudPlusFeatures,
		createCloudPlusConnection,
		verifyCloudPlusConnection,
		deleteConnection
	} = $props();

	const proUpgradePrompt = getUpgradePrompt('pro', 'Cloud+ connectors');
</script>

<!-- SaaS -->
<div class="glass-panel stagger-enter" style="animation-delay: 300ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="saas" size={40} />
			<div>
				<h3 class="font-bold text-lg">SaaS</h3>
				<p class="text-xs text-ink-500">Cloud+ Spend Connector</p>
			</div>
		</div>
		{#if loadingSaaS}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if saasConnections.length > 0}
			<span class="badge badge-accent">Connected ({saasConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if saasConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each saasConnections as conn (conn.id)}
				<div class="p-3 rounded-xl bg-ink-900/50 border border-ink-800">
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="text-xs text-ink-300 font-semibold">{conn.name || 'SaaS Feed'}</div>
							<div class="text-xs text-ink-500 font-mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="px-2 py-1 rounded-lg text-xs font-semibold bg-accent-500/10 text-accent-300 hover:bg-accent-500/20 transition-all"
								onclick={() => verifyCloudPlusConnection('saas', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
								onclick={() => deleteConnection('saas', conn.id)}
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
				{saasConnections.length > 0 ? 'Add another SaaS connector' : 'Create SaaS connector'}
			</summary>
			<div class="space-y-3 mt-3">
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Connection name (e.g. Stripe Billing)"
					bind:value={saasName}
				/>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Vendor (stripe, salesforce, etc.)"
					bind:value={saasVendor}
				/>
				<select
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					bind:value={saasAuthMethod}
				>
					<option value="api_key">API key</option>
					<option value="oauth">OAuth token</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					type="password"
					placeholder="API key / OAuth token"
					bind:value={saasApiKey}
				/>
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-20 font-mono"
					placeholder="Connector config JSON (example: include instance_url for Salesforce)"
					bind:value={saasConnectorConfig}
				></textarea>
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-24 font-mono"
					placeholder="Spend feed JSON array for manual/csv mode"
					bind:value={saasFeedInput}
				></textarea>
				<button
					type="button"
					class="btn btn-secondary text-xs w-full"
					onclick={() => createCloudPlusConnection('saas')}
					disabled={creatingSaaS}
				>
					{creatingSaaS ? 'Creating...' : 'Create & Verify SaaS Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingSaaS}
		<p class="text-xs text-ink-400 mb-4">
			Connect SaaS spend feeds for Cloud+ cost visibility and optimization.
		</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full">{proUpgradePrompt.cta}</a
			>
			<span class="badge badge-warning text-xs w-full justify-center">{proUpgradePrompt.badge}</span
			>
			<p class="text-[11px] leading-relaxed text-ink-500">{proUpgradePrompt.body}</p>
		</div>
	{/if}
</div>

<!-- License / ITAM -->
<div class="glass-panel stagger-enter" style="animation-delay: 400ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="license" size={40} />
			<div>
				<h3 class="font-bold text-lg">License</h3>
				<p class="text-xs text-ink-500">Cloud+ ITAM Connector</p>
			</div>
		</div>
		{#if loadingLicense}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if licenseConnections.length > 0}
			<span class="badge badge-accent">Connected ({licenseConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if licenseConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each licenseConnections as conn (conn.id)}
				<div class="p-3 rounded-xl bg-ink-900/50 border border-ink-800">
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="text-xs text-ink-300 font-semibold">{conn.name || 'License Feed'}</div>
							<div class="text-xs text-ink-500 font-mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="px-2 py-1 rounded-lg text-xs font-semibold bg-accent-500/10 text-accent-300 hover:bg-accent-500/20 transition-all"
								onclick={() => verifyCloudPlusConnection('license', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
								onclick={() => deleteConnection('license', conn.id)}
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
				{licenseConnections.length > 0
					? 'Add another License connector'
					: 'Create License connector'}
			</summary>
			<div class="space-y-3 mt-3">
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Connection name (e.g. Microsoft 365 Licenses)"
					bind:value={licenseName}
				/>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					placeholder="Vendor (microsoft_365, flexera, etc.)"
					bind:value={licenseVendor}
				/>
				<select
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					bind:value={licenseAuthMethod}
				>
					<option value="oauth">OAuth token</option>
					<option value="api_key">API key</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				<input
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200"
					type="password"
					placeholder="API key / OAuth token"
					bind:value={licenseApiKey}
				/>
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-20 font-mono"
					placeholder="Connector config JSON (example: default_seat_price_usd and sku_prices)"
					bind:value={licenseConnectorConfig}
				></textarea>
				<textarea
					class="w-full rounded-lg bg-ink-950 border border-ink-800 px-3 py-2 text-xs text-ink-200 h-24 font-mono"
					placeholder="License feed JSON array for manual/csv mode"
					bind:value={licenseFeedInput}
				></textarea>
				<button
					type="button"
					class="btn btn-secondary text-xs w-full"
					onclick={() => createCloudPlusConnection('license')}
					disabled={creatingLicense}
				>
					{creatingLicense ? 'Creating...' : 'Create & Verify License Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingLicense}
		<p class="text-xs text-ink-400 mb-4">
			Connect license/ITAM spend feeds to include seat and contract costs in FinOps.
		</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full">{proUpgradePrompt.cta}</a
			>
			<span class="badge badge-warning text-xs w-full justify-center">{proUpgradePrompt.badge}</span
			>
			<p class="text-[11px] leading-relaxed text-ink-500">{proUpgradePrompt.body}</p>
		</div>
	{/if}
</div>
