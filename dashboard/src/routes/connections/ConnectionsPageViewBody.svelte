<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';

	let {
		data,
		loadingAWS,
		loadingAzure,
		loadingGCP,
		loadingSaaS,
		loadingLicense,
		loadingPlatform,
		loadingHybrid,
		awsConnection,
		awsConnections,
		azureConnections,
		gcpConnections,
		saasConnections,
		licenseConnections,
		platformConnections,
		hybridConnections,
		discoveredAccounts,
		loadingDiscovered,
		syncingOrg,
		linkingAccount,
		error,
		success,
		verifyingCloudPlus,
		creatingSaaS,
		creatingLicense,
		creatingPlatform,
		creatingHybrid,
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
		syncAWSOrg,
		deleteConnection,
		linkDiscoveredAccount
	} = $props();

	const loadPublicCloudCards = createLazyComponent(
		() => import('./ConnectionsPublicCloudCards.svelte')
	);
	const loadSaasLicenseCards = createLazyComponent(
		() => import('./ConnectionsSaasLicenseCards.svelte')
	);
	const loadPlatformHybridCards = createLazyComponent(
		() => import('./ConnectionsPlatformHybridCards.svelte')
	);
	const loadOrgDiscoverySection = createLazyComponent(
		() => import('./ConnectionsOrgDiscoverySection.svelte')
	);
</script>

<AuthGate authenticated={!!data.user} action="manage cloud accounts">
	<div class="connections-page">
		<div class="connections-page__header">
			<div>
				<h1 class="connections-page__title">Cloud Accounts</h1>
				<p class="connections-page__subtitle">
					Manage your multi-cloud connectivity and enterprise organization discovery.
				</p>
			</div>
			<a href={`${base}/onboarding`} class="btn btn-primary connections-page__cta">
				<span>➕</span> Connect New Provider
			</a>
		</div>

		{#if error}
			<div class="connections-page__notice connections-page__notice--error">
				<p>{error}</p>
			</div>
		{/if}

		{#if success}
			<div class="connections-page__notice connections-page__notice--success">
				<p>{success}</p>
			</div>
		{/if}

		<div class="connections-page__grid">
			{#await loadPublicCloudCards()}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-40 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
			{:then module}
				{@const ConnectionsPublicCloudCards = module.default}
				<ConnectionsPublicCloudCards
					{data}
					{loadingAWS}
					{loadingAzure}
					{loadingGCP}
					{awsConnections}
					{azureConnections}
					{gcpConnections}
					{deleteConnection}
				/>
			{:catch}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-40 mb-4"></div>
				</div>
			{/await}

			{#await loadSaasLicenseCards()}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-48 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
			{:then module}
				{@const ConnectionsSaasLicenseCards = module.default}
				<ConnectionsSaasLicenseCards
					{loadingSaaS}
					{loadingLicense}
					{saasConnections}
					{licenseConnections}
					{verifyingCloudPlus}
					{creatingSaaS}
					{creatingLicense}
					{canUseCloudPlusFeatures}
					{createCloudPlusConnection}
					{verifyCloudPlusConnection}
					{deleteConnection}
					bind:saasName
					bind:saasVendor
					bind:saasAuthMethod
					bind:saasApiKey
					bind:saasConnectorConfig
					bind:saasFeedInput
					bind:licenseName
					bind:licenseVendor
					bind:licenseAuthMethod
					bind:licenseApiKey
					bind:licenseConnectorConfig
					bind:licenseFeedInput
				/>
			{:catch}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-48 mb-4"></div>
				</div>
			{/await}

			{#await loadPlatformHybridCards()}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-48 mb-4"></div>
					<div class="skeleton h-56 rounded-2xl"></div>
				</div>
			{:then module}
				{@const ConnectionsPlatformHybridCards = module.default}
				<ConnectionsPlatformHybridCards
					{loadingPlatform}
					{loadingHybrid}
					{platformConnections}
					{hybridConnections}
					{verifyingCloudPlus}
					{creatingPlatform}
					{creatingHybrid}
					{canUseCloudPlusFeatures}
					{createCloudPlusConnection}
					{verifyCloudPlusConnection}
					{deleteConnection}
					bind:platformName
					bind:platformVendor
					bind:platformAuthMethod
					bind:platformApiKey
					bind:platformApiSecret
					bind:platformConnectorConfig
					bind:platformFeedInput
					bind:hybridName
					bind:hybridVendor
					bind:hybridAuthMethod
					bind:hybridApiKey
					bind:hybridApiSecret
					bind:hybridConnectorConfig
					bind:hybridFeedInput
				/>
			{:catch}
				<div class="card connections-page__placeholder">
					<div class="skeleton h-8 w-48 mb-4"></div>
				</div>
			{/await}
		</div>

		{#await loadOrgDiscoverySection()}
			<div class="card connections-page__org-placeholder">
				<div class="skeleton h-8 w-56 mb-4"></div>
				<div class="skeleton h-32 rounded-2xl"></div>
			</div>
		{:then module}
			{@const ConnectionsOrgDiscoverySection = module.default}
			<ConnectionsOrgDiscoverySection
				{data}
				{awsConnection}
				{syncingOrg}
				{discoveredAccounts}
				{loadingDiscovered}
				{linkingAccount}
				{syncAWSOrg}
				{linkDiscoveredAccount}
			/>
		{:catch}
			<div class="card connections-page__org-placeholder">
				<div class="skeleton h-8 w-56 mb-4"></div>
			</div>
		{/await}
	</div>
</AuthGate>
