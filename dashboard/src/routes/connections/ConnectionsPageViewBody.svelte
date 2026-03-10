<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import ConnectionsOrgDiscoverySection from './ConnectionsOrgDiscoverySection.svelte';
	import ConnectionsPlatformHybridCards from './ConnectionsPlatformHybridCards.svelte';
	import ConnectionsPublicCloudCards from './ConnectionsPublicCloudCards.svelte';
	import ConnectionsSaasLicenseCards from './ConnectionsSaasLicenseCards.svelte';

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
</script>

<AuthGate authenticated={!!data.user} action="manage cloud accounts">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold mb-2">Cloud Accounts</h1>
			<p class="text-ink-400">
				Manage your multi-cloud connectivity and enterprise organization discovery.
			</p>
		</div>
		<a href={`${base}/onboarding`} class="btn btn-primary !w-auto">
			<span>➕</span> Connect New Provider
		</a>
	</div>

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

	<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
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
	</div>

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
</AuthGate>
