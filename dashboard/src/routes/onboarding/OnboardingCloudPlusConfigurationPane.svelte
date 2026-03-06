<script lang="ts">
	let {
		selectedProvider,
		cloudPlusSampleFeed,
		cloudShellSnippet,
		cloudPlusName = $bindable(),
		cloudPlusVendor = $bindable(),
		cloudPlusAuthMethod = $bindable(),
		cloudPlusApiKey = $bindable(),
		cloudPlusFeedInput = $bindable(),
		cloudPlusConnectorConfigInput = $bindable(),
		cloudPlusNativeConnectors,
		cloudPlusManualFeedSchema,
		handleCloudPlusVendorInputChanged,
		chooseNativeCloudPlusVendor,
		handleCloudPlusAuthMethodChanged,
		getAvailableCloudPlusAuthMethods,
		isCloudPlusNativeAuthMethod,
		setRequiredConfigField,
		getRequiredConfigFieldValue,
		getSelectedNativeConnector
	} = $props();
</script>

<h2>Step 2: Connect {selectedProvider === 'saas' ? 'SaaS' : 'License / ITAM'} Spend</h2>
<p class="mb-6">Configure a Cloud+ connector using API key or manual/CSV feed ingestion.</p>

<div class="space-y-4 mb-8">
	{#if cloudPlusNativeConnectors.length > 0}
		<div class="info-box mb-4">
			<h4 class="text-sm font-bold mb-2">🔌 Native Connectors</h4>
			<p class="text-xs text-ink-400 mb-3">
				Choose a supported vendor to auto-configure recommended auth and required fields.
			</p>
			<div class="flex flex-wrap gap-2">
				{#each cloudPlusNativeConnectors as connector (connector.vendor)}
					<button
						type="button"
						class="secondary-btn !w-auto px-3 py-1.5 text-xs"
						class:opacity-70={cloudPlusVendor.trim().toLowerCase() !== connector.vendor}
						onclick={() => chooseNativeCloudPlusVendor(connector.vendor)}
					>
						{connector.display_name}
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<div class="form-group">
		<label for="cloudPlusName">Connection Name</label>
		<input
			type="text"
			id="cloudPlusName"
			bind:value={cloudPlusName}
			placeholder={selectedProvider === 'saas' ? 'Salesforce Spend Feed' : 'Microsoft 365 Seats'}
		/>
	</div>
	<div class="form-group">
		<label for="cloudPlusVendor">Vendor</label>
		<input
			type="text"
			id="cloudPlusVendor"
			bind:value={cloudPlusVendor}
			onchange={handleCloudPlusVendorInputChanged}
			placeholder={selectedProvider === 'saas' ? 'salesforce' : 'microsoft'}
		/>
	</div>
	<div class="form-group">
		<label for="cloudPlusAuthMethod">Auth Method</label>
		<select
			id="cloudPlusAuthMethod"
			bind:value={cloudPlusAuthMethod}
			onchange={handleCloudPlusAuthMethodChanged}
		>
			{#each getAvailableCloudPlusAuthMethods() as authMethod (authMethod)}
				<option value={authMethod}>{authMethod}</option>
			{/each}
		</select>
	</div>
	{#if cloudPlusAuthMethod === 'api_key' || cloudPlusAuthMethod === 'oauth'}
		<div class="form-group">
			<label for="cloudPlusApiKey">API Key / OAuth Token</label>
			<input
				type="password"
				id="cloudPlusApiKey"
				bind:value={cloudPlusApiKey}
				placeholder="Paste vendor API key or OAuth access token"
			/>
		</div>
	{/if}

	{#if isCloudPlusNativeAuthMethod() && getSelectedNativeConnector()?.required_connector_config_fields?.length}
		<div class="info-box">
			<h4 class="text-sm font-bold mb-2">⚙️ Required Connector Fields</h4>
			<p class="text-xs text-ink-400 mb-3">
				These fields are required for {getSelectedNativeConnector()?.display_name} native mode.
			</p>
			<div class="space-y-3">
				{#each getSelectedNativeConnector()?.required_connector_config_fields ?? [] as field (field)}
					<div class="form-group">
						<label for={`cfg-${field}`}>connector_config.{field}</label>
						<input
							type="text"
							id={`cfg-${field}`}
							value={getRequiredConfigFieldValue(field)}
							oninput={(event) =>
								setRequiredConfigField(field, (event.currentTarget as HTMLInputElement).value)}
							placeholder={field === 'instance_url'
								? 'https://your-org.my.salesforce.com'
								: `Enter ${field}`}
						/>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<div class="info-box mb-6">
	<h4 class="text-sm font-bold mb-2">📘 Setup Snippet</h4>
	<p class="text-xs text-ink-400 mb-3">Use this as your setup guide and feed template.</p>
	<div class="bg-black/50 p-3 rounded font-mono text-xs whitespace-pre-wrap break-all text-accent-300">
		{cloudShellSnippet || '# Cloud+ setup snippet is loading...'}
	</div>
</div>

<div class="info-box mb-6">
	<h4 class="text-sm font-bold mb-2">🧩 Connector Config JSON (Optional)</h4>
	<p class="text-xs text-ink-400 mb-3">
		Add non-secret vendor options to <code>connector_config</code> (required fields above are merged
		automatically).
	</p>
	{#if getSelectedNativeConnector()?.optional_connector_config_fields?.length}
		<p class="text-xs text-ink-500 mb-3">
			Optional keys: {getSelectedNativeConnector()?.optional_connector_config_fields.join(', ')}
		</p>
	{/if}
	<textarea
		rows="5"
		class="input font-mono text-xs"
		bind:value={cloudPlusConnectorConfigInput}
		placeholder={selectedProvider === 'license' ? '{"default_seat_price_usd": 36}' : '{}'}
	></textarea>
</div>

<div class="info-box mb-6">
	<h4 class="text-sm font-bold mb-2">🧾 Feed JSON (Optional)</h4>
	<p class="text-xs text-ink-400 mb-3">
		Provide an initial feed payload to validate ingestion immediately.
	</p>
	{#if cloudPlusManualFeedSchema.required_fields.length > 0}
		<p class="text-xs text-ink-500 mb-3">
			Required feed keys: {cloudPlusManualFeedSchema.required_fields.join(', ')}
		</p>
	{/if}
	<textarea
		rows="10"
		class="input font-mono text-xs"
		bind:value={cloudPlusFeedInput}
		placeholder={cloudPlusSampleFeed || '[]'}
	></textarea>
</div>
