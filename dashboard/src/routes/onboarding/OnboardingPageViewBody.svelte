<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import OnboardingStepConfigurationSection from './OnboardingStepConfigurationSection.svelte';
	import OnboardingStepSelectProviderSection from './OnboardingStepSelectProviderSection.svelte';
	import OnboardingVerifySuccessSection from './OnboardingVerifySuccessSection.svelte';
	import type {
		CloudPlusAuthMethod,
		DiscoveryCandidate,
		IdpProvider,
		NativeConnectorMeta,
		OnboardingProvider
	} from './onboardingTypesUtils';

	type AsyncAction = () => void | Promise<void>;
	type CandidateAction = (candidate: DiscoveryCandidate) => void | Promise<void>;
	type ConfigFieldSetter = (field: string, value: string) => void;
	type ConfigFieldGetter = (field: string) => string;

	interface Props {
		data: {
			user?: unknown;
			subscription?: {
				tier?: string;
			};
		};
		currentStep: number;
		selectedProvider: OnboardingProvider;
		selectedTab: 'cloudformation' | 'terraform';
		error: string;
		success: boolean;
		copied: boolean;
		isLoading: boolean;
		isVerifying: boolean;
		discoveryEmail: string;
		discoveryDomain: string;
		discoveryIdpProvider: IdpProvider;
		discoveryCandidates: DiscoveryCandidate[];
		discoveryWarnings: string[];
		discoveryLoadingStageA: boolean;
		discoveryLoadingStageB: boolean;
		discoveryActionCandidateId: string | null;
		discoveryError: string;
		discoveryInfo: string;
		externalId: string;
		magicLink: string;
		cloudformationYaml: string;
		terraformHcl: string;
		roleArn: string;
		awsAccountId: string;
		isManagementAccount: boolean;
		organizationId: string;
		azureSubscriptionId: string;
		azureTenantId: string;
		azureClientId: string;
		gcpProjectId: string;
		gcpBillingProjectId: string;
		gcpBillingDataset: string;
		gcpBillingTable: string;
		cloudShellSnippet: string;
		cloudPlusSampleFeed: string;
		cloudPlusName: string;
		cloudPlusVendor: string;
		cloudPlusAuthMethod: CloudPlusAuthMethod;
		cloudPlusApiKey: string;
		cloudPlusFeedInput: string;
		cloudPlusConnectorConfigInput: string;
		cloudPlusNativeConnectors: NativeConnectorMeta[];
		cloudPlusManualFeedSchema: {
			required_fields: string[];
			optional_fields: string[];
		};
		canUseGrowthFeatures: () => boolean;
		canUseCloudPlusFeatures: () => boolean;
		canUseIdpDeepScan: () => boolean;
		getProviderLabel: (provider: OnboardingProvider) => string;
		getDiscoveryCategoryLabel: (category: string) => string;
		formatDiscoveryConfidence: (score: number) => string;
		runDiscoveryStageA: AsyncAction;
		runDiscoveryStageB: AsyncAction;
		connectDiscoveryCandidate: CandidateAction;
		ignoreDiscoveryCandidate: CandidateAction;
		markDiscoveryCandidateConnected: CandidateAction;
		handleContinueToSetup: AsyncAction;
		copyTemplate: () => void;
		downloadTemplate: () => void;
		handleCloudPlusVendorInputChanged: () => void;
		chooseNativeCloudPlusVendor: (vendor: string) => void;
		handleCloudPlusAuthMethodChanged: () => void;
		getAvailableCloudPlusAuthMethods: () => CloudPlusAuthMethod[];
		isCloudPlusNativeAuthMethod: () => boolean;
		setRequiredConfigField: ConfigFieldSetter;
		getRequiredConfigFieldValue: ConfigFieldGetter;
		getSelectedNativeConnector: () => NativeConnectorMeta | null;
		proceedToVerify: AsyncAction;
		verifyConnection: AsyncAction;
	}

	let {
		data,
		currentStep = $bindable(),
		selectedProvider = $bindable(),
		selectedTab = $bindable(),
		error,
		success,
		copied,
		isLoading,
		isVerifying,
		discoveryEmail = $bindable(),
		discoveryDomain,
		discoveryIdpProvider = $bindable(),
		discoveryCandidates,
		discoveryWarnings,
		discoveryLoadingStageA,
		discoveryLoadingStageB,
		discoveryActionCandidateId,
		discoveryError,
		discoveryInfo,
		externalId,
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
		canUseGrowthFeatures,
		canUseCloudPlusFeatures,
		canUseIdpDeepScan,
		getProviderLabel,
		getDiscoveryCategoryLabel,
		formatDiscoveryConfidence,
		runDiscoveryStageA,
		runDiscoveryStageB,
		connectDiscoveryCandidate,
		ignoreDiscoveryCandidate,
		markDiscoveryCandidateConnected,
		handleContinueToSetup,
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
	}: Props = $props();

	const growthTier = $derived(['growth', 'pro', 'enterprise'].includes(data?.subscription?.tier ?? ''));
</script>

<AuthGate authenticated={!!data.user} action="connect providers">
	<div class="onboarding-container">
		<h1>🔗 Connect Cloud & Cloud+ Providers</h1>

		<div class="progress-steps">
			<div class="step" class:active={currentStep === 0} class:complete={currentStep > 0}>1. Choose Cloud</div>
			<div class="step" class:active={currentStep === 1} class:complete={currentStep > 1}>2. Configure</div>
			<div class="step" class:active={currentStep === 2} class:complete={currentStep > 2}>3. Verify</div>
			<div class="step" class:active={currentStep === 3}>4. Done!</div>
		</div>

		{#if isLoading}
			<div class="loading-overlay">
				<div class="spinner mb-4"></div>
				<p class="text-sm text-ink-300">Fetching configuration details...</p>
			</div>
		{/if}

		{#if error}
			<div class="error-banner">{error}</div>
		{/if}

		{#if currentStep === 0}
			<OnboardingStepSelectProviderSection
				{data}
				bind:selectedProvider
				bind:discoveryEmail
				{discoveryDomain}
				bind:discoveryIdpProvider
				{discoveryCandidates}
				{discoveryWarnings}
				{discoveryLoadingStageA}
				{discoveryLoadingStageB}
				{discoveryActionCandidateId}
				{discoveryError}
				{discoveryInfo}
				{isLoading}
				{canUseGrowthFeatures}
				{canUseCloudPlusFeatures}
				{canUseIdpDeepScan}
				{getDiscoveryCategoryLabel}
				{formatDiscoveryConfidence}
				{runDiscoveryStageA}
				{runDiscoveryStageB}
				{connectDiscoveryCandidate}
				{ignoreDiscoveryCandidate}
				{markDiscoveryCandidateConnected}
				{handleContinueToSetup}
			/>
		{/if}

		{#if currentStep === 1}
			<OnboardingStepConfigurationSection
				{selectedProvider}
				bind:selectedTab
				{copied}
				{isVerifying}
				{magicLink}
				{cloudformationYaml}
				{terraformHcl}
				bind:roleArn
				bind:awsAccountId
				bind:isManagementAccount
				bind:organizationId
				bind:azureSubscriptionId
				bind:azureTenantId
				bind:azureClientId
				bind:gcpProjectId
				bind:gcpBillingProjectId
				bind:gcpBillingDataset
				bind:gcpBillingTable
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
				{growthTier}
				onBack={() => (currentStep = 0)}
				{copyTemplate}
				{downloadTemplate}
				{handleCloudPlusVendorInputChanged}
				{chooseNativeCloudPlusVendor}
				{handleCloudPlusAuthMethodChanged}
				{getAvailableCloudPlusAuthMethods}
				{isCloudPlusNativeAuthMethod}
				{setRequiredConfigField}
				{getRequiredConfigFieldValue}
				{getSelectedNativeConnector}
				{proceedToVerify}
				{verifyConnection}
			/>
		{/if}

		<OnboardingVerifySuccessSection
			{data}
			{success}
			{selectedProvider}
			{isVerifying}
			{verifyConnection}
			{getProviderLabel}
			bind:currentStep
			bind:awsAccountId
			bind:roleArn
			bind:isManagementAccount
			bind:organizationId
		/>
	</div>
</AuthGate>
