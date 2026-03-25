<script lang="ts">
	import { createLazyComponent } from '$lib/lazyComponent';
	import OnboardingStepNavigationActions from './OnboardingStepNavigationActions.svelte';
	let {
		selectedProvider,
		selectedTab = $bindable(),
		copied,
		isVerifying,
		magicLink,
		cloudformationYaml,
		terraformHcl,
		roleArn = $bindable(),
		awsAccountId = $bindable(),
		isManagementAccount = $bindable(),
		organizationId = $bindable(),
		azureSubscriptionId = $bindable(),
		azureTenantId = $bindable(),
		azureClientId = $bindable(),
		gcpProjectId = $bindable(),
		gcpBillingProjectId = $bindable(),
		gcpBillingDataset = $bindable(),
		gcpBillingTable = $bindable(),
		cloudShellSnippet,
		cloudPlusSampleFeed,
		cloudPlusName = $bindable(),
		cloudPlusVendor = $bindable(),
		cloudPlusAuthMethod = $bindable(),
		cloudPlusApiKey = $bindable(),
		cloudPlusFeedInput = $bindable(),
		cloudPlusConnectorConfigInput = $bindable(),
		cloudPlusNativeConnectors,
		cloudPlusManualFeedSchema,
		growthTier,
		onBack,
		copyTemplate,
		downloadTemplate,
		handleCloudPlusVendorInputChanged,
		chooseNativeCloudPlusVendor,
		handleCloudPlusAuthMethodChanged,
		getAvailableCloudPlusAuthMethods,
		isCloudPlusNativeAuthMethod,
		setRequiredConfigField,
		getRequiredConfigFieldValue,
		getSelectedNativeConnector,
		proceedToVerify,
		verifyConnection
	} = $props();

	const loadAwsConfigurationPane = createLazyComponent(
		() => import('./OnboardingAwsConfigurationPane.svelte')
	);
	const loadAzureConfigurationPane = createLazyComponent(
		() => import('./OnboardingAzureConfigurationPane.svelte')
	);
	const loadGcpConfigurationPane = createLazyComponent(
		() => import('./OnboardingGcpConfigurationPane.svelte')
	);
	const loadCloudPlusConfigurationPane = createLazyComponent(
		() => import('./OnboardingCloudPlusConfigurationPane.svelte')
	);
</script>

<div class="step-content">
	{#if selectedProvider === 'aws'}
		{#await loadAwsConfigurationPane()}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
				<div class="skeleton h-48 rounded-2xl"></div>
			</div>
		{:then module}
			{@const OnboardingAwsConfigurationPane = module.default}
			<OnboardingAwsConfigurationPane
				bind:selectedTab
				{copied}
				{magicLink}
				{cloudformationYaml}
				{terraformHcl}
				bind:roleArn
				bind:awsAccountId
				bind:isManagementAccount
				bind:organizationId
				{growthTier}
				{copyTemplate}
				{downloadTemplate}
			/>
		{:catch}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
			</div>
		{/await}
	{:else if selectedProvider === 'azure'}
		{#await loadAzureConfigurationPane()}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
				<div class="skeleton h-40 rounded-2xl"></div>
			</div>
		{:then module}
			{@const OnboardingAzureConfigurationPane = module.default}
			<OnboardingAzureConfigurationPane
				bind:azureSubscriptionId
				bind:azureTenantId
				bind:azureClientId
				{cloudShellSnippet}
			/>
		{:catch}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
			</div>
		{/await}
	{:else if selectedProvider === 'gcp'}
		{#await loadGcpConfigurationPane()}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
				<div class="skeleton h-40 rounded-2xl"></div>
			</div>
		{:then module}
			{@const OnboardingGcpConfigurationPane = module.default}
			<OnboardingGcpConfigurationPane
				bind:gcpProjectId
				bind:gcpBillingProjectId
				bind:gcpBillingDataset
				bind:gcpBillingTable
				{cloudShellSnippet}
			/>
		{:catch}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-56"></div>
				<div class="skeleton h-4 w-full"></div>
			</div>
		{/await}
	{:else if selectedProvider === 'saas' || selectedProvider === 'license'}
		{#await loadCloudPlusConfigurationPane()}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-64"></div>
				<div class="skeleton h-4 w-full"></div>
				<div class="skeleton h-56 rounded-2xl"></div>
			</div>
		{:then module}
			{@const OnboardingCloudPlusConfigurationPane = module.default}
			<OnboardingCloudPlusConfigurationPane
				{selectedProvider}
				{cloudShellSnippet}
				{cloudPlusSampleFeed}
				bind:cloudPlusName
				bind:cloudPlusVendor
				bind:cloudPlusAuthMethod
				bind:cloudPlusApiKey
				bind:cloudPlusFeedInput
				bind:cloudPlusConnectorConfigInput
				{cloudPlusNativeConnectors}
				{cloudPlusManualFeedSchema}
				{handleCloudPlusVendorInputChanged}
				{chooseNativeCloudPlusVendor}
				{handleCloudPlusAuthMethodChanged}
				{getAvailableCloudPlusAuthMethods}
				{isCloudPlusNativeAuthMethod}
				{setRequiredConfigField}
				{getRequiredConfigFieldValue}
				{getSelectedNativeConnector}
			/>
		{:catch}
			<div class="space-y-4 mb-8">
				<div class="skeleton h-8 w-64"></div>
				<div class="skeleton h-4 w-full"></div>
			</div>
		{/await}
	{/if}

	<OnboardingStepNavigationActions
		{selectedProvider}
		{isVerifying}
		{onBack}
		{verifyConnection}
		{proceedToVerify}
	/>
</div>
