<script lang="ts">
	import { base } from '$app/paths';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
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
		canUseMultiCloudFeatures: () => boolean;
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
		canUseMultiCloudFeatures,
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

	const growthTier = $derived(
		['growth', 'pro', 'enterprise'].includes(data?.subscription?.tier ?? '')
	);
	const loadSelectProviderSection = createLazyComponent(
		() => import('./OnboardingStepSelectProviderSection.svelte')
	);
	const loadConfigurationSection = createLazyComponent(
		() => import('./OnboardingStepConfigurationSection.svelte')
	);
	const loadVerifySuccessSection = createLazyComponent(
		() => import('./OnboardingVerifySuccessSection.svelte')
	);
</script>

<AuthGate authenticated={!!data.user} action="connect providers">
	<div class="onboarding-container">
		<h1>🔗 Connect Cloud & Cloud+ Providers</h1>

		<div class="progress-steps">
			<div class="step" class:active={currentStep === 0} class:complete={currentStep > 0}>
				1. Choose Cloud
			</div>
			<div class="step" class:active={currentStep === 1} class:complete={currentStep > 1}>
				2. Configure
			</div>
			<div class="step" class:active={currentStep === 2} class:complete={currentStep > 2}>
				3. Verify
			</div>
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
			{#await loadSelectProviderSection()}
				<div class="card">
					<div class="skeleton h-8 w-56 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-3/4 mb-6"></div>
					<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
						<div class="skeleton h-28 rounded-2xl"></div>
						<div class="skeleton h-28 rounded-2xl"></div>
						<div class="skeleton h-28 rounded-2xl"></div>
					</div>
				</div>
			{:then module}
				{@const OnboardingStepSelectProviderSection = module.default}
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
					{canUseMultiCloudFeatures}
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
			{:catch}
				<div class="card">
					<div class="skeleton h-8 w-56 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-3/4 mb-6"></div>
				</div>
			{/await}
		{/if}

		{#if currentStep === 1}
			{#await loadConfigurationSection()}
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-2/3 mb-6"></div>
					<div class="skeleton h-64 rounded-2xl"></div>
				</div>
			{:then module}
				{@const OnboardingStepConfigurationSection = module.default}
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
			{:catch}
				<div class="card">
					<div class="skeleton h-8 w-64 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-2/3 mb-6"></div>
				</div>
			{/await}
		{/if}

		{#if currentStep >= 2}
			{#await loadVerifySuccessSection()}
				<div class="card">
					<div class="skeleton h-8 w-48 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-2/3 mb-6"></div>
					<div class="skeleton h-12 w-full rounded-xl"></div>
				</div>
			{:then module}
				{@const OnboardingVerifySuccessSection = module.default}
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
			{:catch}
				<div class="card">
					<div class="skeleton h-8 w-48 mb-4"></div>
					<div class="skeleton h-4 w-full mb-2"></div>
					<div class="skeleton h-4 w-2/3"></div>
				</div>
			{/await}
		{/if}
	</div>
</AuthGate>
