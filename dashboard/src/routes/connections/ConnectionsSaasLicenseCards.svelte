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
<div class="glass-panel stagger-enter connections-connector-card connections-card-delay-3">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="saas" size={40} />
			<div>
				<h3 class="connections-card__title">SaaS</h3>
				<p class="connections-card__subtitle">Cloud+ Spend Connector</p>
			</div>
		</div>
		{#if loadingSaaS}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if saasConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Connected ({saasConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if saasConnections.length > 0}
		<div class="connections-list">
			{#each saasConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__name">{conn.name || 'SaaS Feed'}</div>
							<div class="connections-record__mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="connections-record__actions">
							<button
								type="button"
								class="connections-inline-action"
								onclick={() => verifyCloudPlusConnection('saas', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="connections-delete-button"
								onclick={() => deleteConnection('saas', conn.id)}
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
				{saasConnections.length > 0 ? 'Add another SaaS connector' : 'Create SaaS connector'}
			</summary>
			<div class="connections-disclosure__body">
				<input
					class="input connections-field"
					placeholder="Connection name (e.g. Stripe Billing)"
					bind:value={saasName}
				/>
				<input
					class="input connections-field"
					placeholder="Vendor (stripe, salesforce, etc.)"
					bind:value={saasVendor}
				/>
				<select class="input connections-field" bind:value={saasAuthMethod}>
					<option value="api_key">API key</option>
					<option value="oauth">OAuth token</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				<input
					class="input connections-field"
					type="password"
					placeholder="API key / OAuth token"
					bind:value={saasApiKey}
				/>
				<textarea
					class="input connections-field connections-field--code"
					placeholder="Connector config JSON (example: include instance_url for Salesforce)"
					bind:value={saasConnectorConfig}
				></textarea>
				<textarea
					class="input connections-field connections-field--feed"
					placeholder="Spend feed JSON array for manual/csv mode"
					bind:value={saasFeedInput}
				></textarea>
				<button
					type="button"
					class="btn btn-secondary connections-submit"
					onclick={() => createCloudPlusConnection('saas')}
					disabled={creatingSaaS}
				>
					{creatingSaaS ? 'Creating...' : 'Create & Verify SaaS Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingSaaS}
		<p class="connections-card__empty-copy">
			Connect SaaS spend feeds for Cloud+ cost visibility and optimization.
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

<!-- License / ITAM -->
<div class="glass-panel stagger-enter connections-connector-card connections-card-delay-4">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="license" size={40} />
			<div>
				<h3 class="connections-card__title">License</h3>
				<p class="connections-card__subtitle">Cloud+ ITAM Connector</p>
			</div>
		</div>
		{#if loadingLicense}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if licenseConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Connected ({licenseConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if licenseConnections.length > 0}
		<div class="connections-list">
			{#each licenseConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__name">{conn.name || 'License Feed'}</div>
							<div class="connections-record__mono">Vendor: {conn.vendor || 'unknown'}</div>
						</div>
						<div class="connections-record__actions">
							<button
								type="button"
								class="connections-inline-action"
								onclick={() => verifyCloudPlusConnection('license', conn.id)}
								disabled={!!verifyingCloudPlus[conn.id]}
							>
								{verifyingCloudPlus[conn.id] ? 'Verifying...' : 'Verify'}
							</button>
							<button
								type="button"
								class="connections-delete-button"
								onclick={() => deleteConnection('license', conn.id)}
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
				{licenseConnections.length > 0
					? 'Add another License connector'
					: 'Create License connector'}
			</summary>
			<div class="connections-disclosure__body">
				<input
					class="input connections-field"
					placeholder="Connection name (e.g. Microsoft 365 Licenses)"
					bind:value={licenseName}
				/>
				<input
					class="input connections-field"
					placeholder="Vendor (microsoft_365, flexera, etc.)"
					bind:value={licenseVendor}
				/>
				<select class="input connections-field" bind:value={licenseAuthMethod}>
					<option value="oauth">OAuth token</option>
					<option value="api_key">API key</option>
					<option value="manual">Manual feed</option>
					<option value="csv">CSV feed</option>
				</select>
				<input
					class="input connections-field"
					type="password"
					placeholder="API key / OAuth token"
					bind:value={licenseApiKey}
				/>
				<textarea
					class="input connections-field connections-field--code"
					placeholder="Connector config JSON (example: default_seat_price_usd and sku_prices)"
					bind:value={licenseConnectorConfig}
				></textarea>
				<textarea
					class="input connections-field connections-field--feed"
					placeholder="License feed JSON array for manual/csv mode"
					bind:value={licenseFeedInput}
				></textarea>
				<button
					type="button"
					class="btn btn-secondary connections-submit"
					onclick={() => createCloudPlusConnection('license')}
					disabled={creatingLicense}
				>
					{creatingLicense ? 'Creating...' : 'Create & Verify License Connector'}
				</button>
			</div>
		</details>
	{:else if !loadingLicense}
		<p class="connections-card__empty-copy">
			Connect license/ITAM spend feeds to include seat and contract costs in FinOps.
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
