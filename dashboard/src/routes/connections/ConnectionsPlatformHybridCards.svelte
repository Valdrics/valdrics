<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';

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

	const proUpgradePrompt = getUpgradePrompt('pro', 'Cloud+ connectors');
</script>

<!-- Platform -->
<div class="glass-panel stagger-enter connections-connector-card connections-card-delay-5">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="platform" size={40} />
			<div>
				<h3 class="connections-card__title">Platform</h3>
				<p class="connections-card__subtitle">Cloud+ Internal Spend</p>
			</div>
		</div>
		{#if loadingPlatform}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if platformConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Connected ({platformConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if platformConnections.length > 0}
		<div class="connections-list">
			{#each platformConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__name">{conn.name || 'Platform Feed'}</div>
							<div class="connections-record__mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="connections-record__actions">
							<button
								type="button"
								class="connections-inline-action"
								onclick={() => verifyCloudPlusConnection('platform', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="connections-delete-button"
								onclick={() => deleteConnection('platform', conn.id)}
								title="Delete Connection"
							>
								<span>🗑️</span>
							</button>
						</div>
					</div>
					<div class="connections-record__details">
						<div class="connections-record__detail">
							<span class="connections-record__label">Auth Method:</span>
							<span class="connections-record__value connections-record__value--accent">
								{conn.auth_method || 'manual'}
							</span>
						</div>
						<div class="connections-record__detail">
							<span class="connections-record__label">Status:</span>
							<span
								class="connections-status"
								class:connections-status--active={conn.is_active}
								class:connections-status--pending={!conn.is_active}
							>
								{conn.is_active ? 'active' : 'pending verification'}
							</span>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if canUseCloudPlusFeatures()}
		<details class="connections-disclosure">
			<summary class="connections-disclosure__summary">
				{platformConnections.length > 0
					? 'Add another Platform connector'
					: 'Create Platform connector'}
			</summary>
			<div class="connections-disclosure__body">
				<input
					class="input connections-field"
					placeholder="Connection name (e.g. Shared Platform Ledger)"
					bind:value={platformName}
				/>
				<input
					class="input connections-field"
					placeholder="Vendor label (internal_platform, kubernetes, shared_services, etc.)"
					bind:value={platformVendor}
				/>
				<select class="input connections-field" bind:value={platformAuthMethod}>
					<option value="api_key">API key (Native)</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				{#if platformAuthMethod === 'api_key'}
					<input
						class="input connections-field"
						type="password"
						placeholder="API key / username / app credential id"
						bind:value={platformApiKey}
					/>
					{#if platformVendor.toLowerCase() === 'datadog'}
						<input
							class="input connections-field"
							type="password"
							placeholder="Application key (api_secret)"
							bind:value={platformApiSecret}
						/>
					{/if}
				{/if}
				<textarea
					class="input connections-field connections-field--code"
					placeholder={`Connector config JSON (ledger_http: {"base_url":"https://ledger.company.com","costs_path":"/api/v1/finops/costs"} | datadog/newrelic: {"unit_prices_usd":{...}} )`}
					bind:value={platformConnectorConfig}
				></textarea>
				{#if platformAuthMethod !== 'api_key'}
					<textarea
						class="input connections-field connections-field--feed"
						placeholder="Spend feed JSON array for manual/csv mode"
						bind:value={platformFeedInput}
					></textarea>
				{/if}
				<button
					type="button"
					class="btn btn-secondary connections-submit"
					onclick={() => createCloudPlusConnection('platform')}
					disabled={creatingPlatform}
				>
					{creatingPlatform ? 'Creating...' : 'Create & Verify Platform Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingPlatform}
		<p class="connections-card__empty-copy">
			Connect internal platform spend feeds to include shared services in allocation and
			reconciliation workflows.
		</p>
		<div class="connections-upgrade-stack">
			<a href={`${base}/billing`} class="btn btn-secondary connections-submit">
				{proUpgradePrompt.cta}
			</a>
			<span class="badge badge-warning connections-upgrade-badge">{proUpgradePrompt.badge}</span>
			<p class="connections-upgrade-copy">{proUpgradePrompt.body}</p>
		</div>
	{/if}
</div>

<!-- Hybrid -->
<div class="glass-panel stagger-enter connections-connector-card connections-card-delay-6">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="hybrid" size={40} />
			<div>
				<h3 class="connections-card__title">Hybrid</h3>
				<p class="connections-card__subtitle">Cloud+ Private Infra</p>
			</div>
		</div>
		{#if loadingHybrid}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if hybridConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Connected ({hybridConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if hybridConnections.length > 0}
		<div class="connections-list">
			{#each hybridConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__name">{conn.name || 'Hybrid Feed'}</div>
							<div class="connections-record__mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="connections-record__actions">
							<button
								type="button"
								class="connections-inline-action"
								onclick={() => verifyCloudPlusConnection('hybrid', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="connections-delete-button"
								onclick={() => deleteConnection('hybrid', conn.id)}
								title="Delete Connection"
							>
								<span>🗑️</span>
							</button>
						</div>
					</div>
					<div class="connections-record__details">
						<div class="connections-record__detail">
							<span class="connections-record__label">Auth Method:</span>
							<span class="connections-record__value connections-record__value--accent">
								{conn.auth_method || 'manual'}
							</span>
						</div>
						<div class="connections-record__detail">
							<span class="connections-record__label">Status:</span>
							<span
								class="connections-status"
								class:connections-status--active={conn.is_active}
								class:connections-status--pending={!conn.is_active}
							>
								{conn.is_active ? 'active' : 'pending verification'}
							</span>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if canUseCloudPlusFeatures()}
		<details class="connections-disclosure">
			<summary class="connections-disclosure__summary">
				{hybridConnections.length > 0 ? 'Add another Hybrid connector' : 'Create Hybrid connector'}
			</summary>
			<div class="connections-disclosure__body">
				<input
					class="input connections-field"
					placeholder="Connection name (e.g. Datacenter Ledger)"
					bind:value={hybridName}
				/>
				<input
					class="input connections-field"
					placeholder="Vendor label (datacenter, colo, private_cloud, etc.)"
					bind:value={hybridVendor}
				/>
				<select class="input connections-field" bind:value={hybridAuthMethod}>
					<option value="api_key">API key (Native)</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				{#if hybridAuthMethod === 'api_key'}
					<input
						class="input connections-field"
						type="password"
						placeholder="API key / username / app credential id"
						bind:value={hybridApiKey}
					/>
					{#if ['openstack', 'cloudkitty', 'vmware', 'vcenter', 'vsphere'].includes(hybridVendor.toLowerCase())}
						<input
							class="input connections-field"
							type="password"
							placeholder="Second secret (api_secret)"
							bind:value={hybridApiSecret}
						/>
					{/if}
				{/if}
				<textarea
					class="input connections-field connections-field--code"
					placeholder={`Connector config JSON (ledger_http: {"base_url":"https://ledger.company.com"} | cloudkitty: {"auth_url":"...","cloudkitty_base_url":"..."} | vmware: {"base_url":"...","cpu_hour_usd":0.1,"ram_gb_hour_usd":0.01})`}
					bind:value={hybridConnectorConfig}
				></textarea>
				{#if hybridAuthMethod !== 'api_key'}
					<textarea
						class="input connections-field connections-field--feed"
						placeholder="Spend feed JSON array for manual/csv mode"
						bind:value={hybridFeedInput}
					></textarea>
				{/if}
				<button
					type="button"
					class="btn btn-secondary connections-submit"
					onclick={() => createCloudPlusConnection('hybrid')}
					disabled={creatingHybrid}
				>
					{creatingHybrid ? 'Creating...' : 'Create & Verify Hybrid Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingHybrid}
		<p class="connections-card__empty-copy">
			Connect private/hybrid infrastructure spend feeds to include on-prem and colo costs in FinOps
			reporting.
		</p>
		<div class="connections-upgrade-stack">
			<a href={`${base}/billing`} class="btn btn-secondary connections-submit">
				{proUpgradePrompt.cta}
			</a>
			<span class="badge badge-warning connections-upgrade-badge">{proUpgradePrompt.badge}</span>
			<p class="connections-upgrade-copy">{proUpgradePrompt.body}</p>
		</div>
	{/if}
</div>
