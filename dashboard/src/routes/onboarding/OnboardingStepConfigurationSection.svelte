<script lang="ts">
	import OnboardingStepNavigationActions from './OnboardingStepNavigationActions.svelte';
	import OnboardingAwsConfigurationPane from './OnboardingAwsConfigurationPane.svelte';
	import OnboardingAzureConfigurationPane from './OnboardingAzureConfigurationPane.svelte';
	import OnboardingGcpConfigurationPane from './OnboardingGcpConfigurationPane.svelte';
	import OnboardingCloudPlusConfigurationPane from './OnboardingCloudPlusConfigurationPane.svelte';
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
</script>

<div class="step-content">
	{#if selectedProvider === 'aws'}
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
	{:else if selectedProvider === 'azure'}
		<OnboardingAzureConfigurationPane
			bind:azureSubscriptionId
			bind:azureTenantId
			bind:azureClientId
			{cloudShellSnippet}
		/>
	{:else if selectedProvider === 'gcp'}
		<OnboardingGcpConfigurationPane
			bind:gcpProjectId
			bind:gcpBillingProjectId
			bind:gcpBillingDataset
			bind:gcpBillingTable
			{cloudShellSnippet}
		/>
	{:else if selectedProvider === 'saas' || selectedProvider === 'license'}
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
	{/if}

	<OnboardingStepNavigationActions
		{selectedProvider}
		{isVerifying}
		{onBack}
		{verifyConnection}
		{proceedToVerify}
	/>
</div>
