<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { page } from '$app/stores';
	import { resolveSessionTenantId } from '$lib/auth/sessionTenant';
	import { buildProductFunnelAttributionContext } from '$lib/funnel/productFunnelTelemetry';
	import OnboardingPageViewBody from './OnboardingPageViewBody.svelte';
	import { ensureOnboardedRequest } from './onboardingApi';
	import { proceedToVerifyFlow, verifyAwsConnectionFlow } from './onboardingFlowActions';
	import { connectDiscoveryCandidateFlow, fetchSetupDataFlow } from './onboardingSetupActions';
	import {
		applyCloudPlusVendorDefaults as applyCloudPlusVendorDefaultsHelper,
		applyDiscoveryCandidateLocally as applyDiscoveryCandidateLocallyHelper,
		getAvailableCloudPlusAuthMethods as getAvailableCloudPlusAuthMethodsHelper,
		getSelectedNativeConnector as getSelectedNativeConnectorHelper,
		upsertDiscoveryCandidates as upsertDiscoveryCandidatesHelper
	} from './onboardingCloudPlusHelpers';
	import {
		formatDiscoveryConfidence,
		getDiscoveryCategoryLabel,
		getProviderLabel,
		type CloudPlusAuthMethod,
		type CloudPlusProvider,
		type DiscoveryCandidate,
		type IdpProvider,
		type ManualFeedSchema,
		type NativeConnectorMeta,
		type OnboardingProvider
	} from './onboardingTypesUtils';
	import {
		canUseCloudPlusFeaturesForTier,
		canUseMultiCloudFeaturesForTier,
		canUseIdpDeepScanForTier
	} from './onboardingTierAccess';
	import {
		runOnboardingDiscoveryStageA,
		runOnboardingDiscoveryStageB,
		updateOnboardingDiscoveryCandidateStatus
	} from './onboardingDiscoveryActions';
	import {
		copyOnboardingTemplate,
		downloadOnboardingTemplate,
		getCloudPlusTemplateForTab,
		getOnboardingSetupAccessError,
		parseOnboardingCloudPlusConnectorConfig,
		parseOnboardingCloudPlusFeed,
		trackOnboardingConnectionVerified
	} from './onboardingUiActions';
	import './OnboardingPageViewContent.css';
	let { data } = $props();
	let currentStep = $state(0),
		selectedProvider: OnboardingProvider = $state('aws'); // 0: Select Provider, 1: Setup, 2: Verify, 3: Done
	let selectedTab: 'cloudformation' | 'terraform' = $state('cloudformation');
	let externalId = $state(''),
		magicLink = $state(''),
		cloudformationYaml = $state(''),
		terraformHcl = $state('');
	let roleArn = $state(''),
		awsAccountId = $state(''),
		isManagementAccount = $state(false),
		organizationId = $state('');
	let azureSubscriptionId = $state(''),
		azureTenantId = $state(''),
		azureClientId = $state('');
	let gcpProjectId = $state(''),
		gcpBillingProjectId = $state(''),
		gcpBillingDataset = $state(''),
		gcpBillingTable = $state('');
	let cloudShellSnippet = $state(''),
		cloudPlusSampleFeed = $state('');
	let cloudPlusName = $state(''),
		cloudPlusVendor = $state('');
	let cloudPlusAuthMethod: CloudPlusAuthMethod = $state('manual');
	let cloudPlusApiKey = $state(''),
		cloudPlusFeedInput = $state('[]'),
		cloudPlusConnectorConfigInput = $state('{}');
	let cloudPlusNativeConnectors = $state<NativeConnectorMeta[]>([]);
	let cloudPlusManualFeedSchema = $state<ManualFeedSchema>({
		required_fields: [],
		optional_fields: []
	});
	let cloudPlusRequiredConfigValues = $state<Record<string, string>>({});
	let cloudPlusConfigProvider = $state<CloudPlusProvider | null>(null);
	let discoveryEmail = $state(''),
		discoveryDomain = $state('');
	let discoveryIdpProvider: IdpProvider = $state('microsoft_365');
	let discoveryCandidates = $state<DiscoveryCandidate[]>([]),
		discoveryWarnings = $state<string[]>([]);
	let discoveryLoadingStageA = $state(false),
		discoveryLoadingStageB = $state(false);
	let discoveryActionCandidateId = $state<string | null>(null);
	let discoveryError = $state(''),
		discoveryInfo = $state('');
	$effect(() => {
		if (discoveryEmail.trim().length > 0) {
			return;
		}
		if (typeof data?.user?.email !== 'string') {
			return;
		}
		const normalized = data.user.email.trim();
		if (normalized.length > 0) {
			discoveryEmail = normalized;
		}
	});
	let isLoading = $state(false),
		isVerifying = $state(false),
		error = $state(''),
		success = $state(false),
		copied = $state(false);
	const canUseMultiCloudFeatures = (): boolean =>
		canUseMultiCloudFeaturesForTier(data?.subscription?.tier);
	const canUseCloudPlusFeatures = (): boolean =>
		canUseCloudPlusFeaturesForTier(data?.subscription?.tier);
	const canUseIdpDeepScan = (): boolean => canUseIdpDeepScanForTier(data?.subscription?.tier);
	const resolveTenantId = (): string | undefined =>
		resolveSessionTenantId({ session: data.session, user: data.user });
	const applyDiscoveryCandidateLocally = (updated: DiscoveryCandidate): void => {
		discoveryCandidates = applyDiscoveryCandidateLocallyHelper(discoveryCandidates, updated);
	};
	const upsertDiscoveryCandidates = (candidates: DiscoveryCandidate[]): void => {
		discoveryCandidates = upsertDiscoveryCandidatesHelper(discoveryCandidates, candidates);
	};
	function applyDiscoveryFlowResult(result: {
		info?: string;
		domain: string;
		warnings: string[];
		candidates: DiscoveryCandidate[];
	}): void {
		if (!result.info) return;
		discoveryDomain = result.domain;
		discoveryWarnings = result.warnings;
		upsertDiscoveryCandidates(result.candidates);
		discoveryInfo = result.info;
	}
	async function runDiscoveryStageA(): Promise<void> {
		await runOnboardingDiscoveryStageA({
			discoveryEmail,
			getAccessToken,
			ensureOnboarded,
			setError: (value) => (discoveryError = value),
			setInfo: (value) => (discoveryInfo = value),
			setLoading: (value) => (discoveryLoadingStageA = value),
			applyDiscoveryFlowResult
		});
	}
	async function runDiscoveryStageB(): Promise<void> {
		await runOnboardingDiscoveryStageB({
			discoveryDomain,
			discoveryEmail,
			discoveryIdpProvider,
			canUseIdpDeepScan: canUseIdpDeepScan(),
			getAccessToken,
			ensureOnboarded,
			setError: (value) => (discoveryError = value),
			setInfo: (value) => (discoveryInfo = value),
			setLoading: (value) => (discoveryLoadingStageB = value),
			applyDiscoveryFlowResult
		});
	}
	async function updateDiscoveryCandidateStatus(
		candidate: DiscoveryCandidate,
		action: 'accept' | 'ignore' | 'connected'
	): Promise<DiscoveryCandidate | null> {
		return updateOnboardingDiscoveryCandidateStatus({
			candidate,
			action,
			getAccessToken,
			applyDiscoveryCandidateLocally,
			setError: (value) => (discoveryError = value),
			setInfo: (value) => (discoveryInfo = value),
			setActionCandidateId: (value) => (discoveryActionCandidateId = value)
		});
	}
	const ignoreDiscoveryCandidate = async (candidate: DiscoveryCandidate): Promise<void> => {
		const updated = await updateDiscoveryCandidateStatus(candidate, 'ignore');
		if (updated) discoveryInfo = `${updated.provider} ignored.`;
	};
	const markDiscoveryCandidateConnected = async (candidate: DiscoveryCandidate): Promise<void> => {
		const updated = await updateDiscoveryCandidateStatus(candidate, 'connected');
		if (updated) discoveryInfo = `${updated.provider} marked as connected.`;
	};
	async function connectDiscoveryCandidate(candidate: DiscoveryCandidate): Promise<void> {
		try {
			const info = await connectDiscoveryCandidateFlow({
				candidate,
				canUseMultiCloudFeatures: canUseMultiCloudFeatures(),
				canUseCloudPlusFeatures: canUseCloudPlusFeatures(),
				updateDiscoveryCandidateStatus,
				setSelectedProvider: (provider) => (selectedProvider = provider),
				setCurrentStep: (step) => (currentStep = step),
				fetchSetupData,
				cloudPlusNativeConnectors,
				chooseNativeCloudPlusVendor,
				setCloudPlusVendor: (vendor) => (cloudPlusVendor = vendor),
				applyCloudPlusVendorDefaults,
				getCloudPlusName: () => cloudPlusName,
				setCloudPlusName: (name) => (cloudPlusName = name)
			});
			if (info) discoveryInfo = info;
		} catch (e) {
			const err = e as Error;
			discoveryError = err.message;
		}
	}
	const getSelectedNativeConnector = (): NativeConnectorMeta | null =>
		getSelectedNativeConnectorHelper(cloudPlusVendor, cloudPlusNativeConnectors);
	const getAvailableCloudPlusAuthMethods = (): CloudPlusAuthMethod[] =>
		getAvailableCloudPlusAuthMethodsHelper(getSelectedNativeConnector());
	function applyCloudPlusVendorDefaults(forceRecommendedAuth: boolean = false): void {
		const nextState = applyCloudPlusVendorDefaultsHelper({
			vendor: cloudPlusVendor,
			connectors: cloudPlusNativeConnectors,
			currentAuthMethod: cloudPlusAuthMethod,
			connectorConfigInput: cloudPlusConnectorConfigInput,
			requiredConfigValues: cloudPlusRequiredConfigValues,
			forceRecommendedAuth
		});
		cloudPlusAuthMethod = nextState.authMethod;
		cloudPlusRequiredConfigValues = nextState.requiredConfigValues;
	}
	const handleCloudPlusVendorInputChanged = (): void => (
		(cloudPlusVendor = cloudPlusVendor.trim().toLowerCase()),
		applyCloudPlusVendorDefaults(false)
	);
	const chooseNativeCloudPlusVendor = (vendor: string): void => (
		(cloudPlusVendor = vendor.trim().toLowerCase()),
		applyCloudPlusVendorDefaults(true)
	);
	function handleCloudPlusAuthMethodChanged(): void {
		const supportedAuthMethods = getAvailableCloudPlusAuthMethods();
		if (!supportedAuthMethods.includes(cloudPlusAuthMethod)) {
			cloudPlusAuthMethod = supportedAuthMethods[0] ?? 'manual';
		}
		if (cloudPlusAuthMethod !== 'api_key' && cloudPlusAuthMethod !== 'oauth') {
			cloudPlusApiKey = '';
		}
	}
	const isCloudPlusNativeAuthMethod = (): boolean =>
		cloudPlusAuthMethod === 'api_key' || cloudPlusAuthMethod === 'oauth';
	const setRequiredConfigField = (field: string, value: string): void => {
		cloudPlusRequiredConfigValues = { ...cloudPlusRequiredConfigValues, [field]: value };
	};
	const getRequiredConfigFieldValue = (field: string): string =>
		cloudPlusRequiredConfigValues[field] ?? '';
	const getAccessToken = async (): Promise<string | null> => data.session?.access_token ?? null;
	async function ensureOnboarded() {
		const token = await getAccessToken();
		if (!token) {
			error = 'Please log in first';
			return false;
		}
		const result = await ensureOnboardedRequest(
			token,
			buildProductFunnelAttributionContext({
				url: $page.url,
				persona: String(data?.profile?.persona ?? '')
			})
		);
		if (!result.ok) {
			error = result.error;
			return false;
		}
		return true;
	}
	async function fetchSetupData() {
		isLoading = true;
		error = '';
		try {
			const setup = await fetchSetupDataFlow({
				selectedProvider,
				getAccessToken,
				cloudPlusConfigProvider,
				cloudPlusVendor,
				cloudPlusConnectorConfigInput
			});
			({
				externalId,
				magicLink,
				cloudformationYaml,
				terraformHcl,
				cloudShellSnippet,
				cloudPlusSampleFeed,
				cloudPlusFeedInput,
				cloudPlusNativeConnectors,
				cloudPlusManualFeedSchema,
				cloudPlusVendor,
				cloudPlusConnectorConfigInput,
				cloudPlusRequiredConfigValues,
				cloudPlusConfigProvider
			} = setup);
			if (setup.shouldApplyCloudPlusVendorDefaults) {
				applyCloudPlusVendorDefaults(true);
			}
		} catch (e) {
			const err = e as Error;
			error = `Failed to initialize ${selectedProvider.toUpperCase()} setup: ${err.message}`;
		} finally {
			isLoading = false;
		}
	}
	async function handleContinueToSetup() {
		const accessError = getOnboardingSetupAccessError({
			selectedProvider,
			canUseMultiCloudFeatures: canUseMultiCloudFeatures(),
			canUseCloudPlusFeatures: canUseCloudPlusFeatures(),
			getProviderLabel
		});
		if (accessError) {
			error = accessError;
			return;
		}

		isLoading = true;
		const onboarded = await ensureOnboarded();
		if (!onboarded) {
			isLoading = false;
			return;
		}
		error = '';
		currentStep = 1;
		await fetchSetupData();
	}
	async function copyTemplate() {
		const { template } = getCloudPlusTemplateForTab({
			selectedTab,
			cloudformationYaml,
			terraformHcl
		});
		await copyOnboardingTemplate(template);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function downloadTemplate() {
		const { template, filename } = getCloudPlusTemplateForTab({
			selectedTab,
			cloudformationYaml,
			terraformHcl
		});
		downloadOnboardingTemplate(template, filename);
	}
	const parseCloudPlusFeed = (): Array<Record<string, unknown>> =>
		parseOnboardingCloudPlusFeed(cloudPlusFeedInput);
	const parseCloudPlusConnectorConfig = (): Record<string, unknown> =>
		parseOnboardingCloudPlusConnectorConfig({
			connectorConfigInput: cloudPlusConnectorConfigInput,
			selectedConnector: getSelectedNativeConnector(),
			isNativeAuthMethod: isCloudPlusNativeAuthMethod(),
			requiredConfigValues: cloudPlusRequiredConfigValues
		});
	async function proceedToVerify() {
		error = '';
		isVerifying = true;
		try {
			const result = await proceedToVerifyFlow({
				selectedProvider,
				getAccessToken,
				azureTenantId,
				azureSubscriptionId,
				azureClientId,
				gcpProjectId,
				gcpBillingProjectId,
				gcpBillingDataset,
				gcpBillingTable,
				cloudPlusName,
				cloudPlusVendor,
				cloudPlusAuthMethod,
				cloudPlusApiKey,
				parseCloudPlusFeed,
				parseCloudPlusConnectorConfig
			});
			currentStep = result.currentStep;
			success = result.success;
			if (result.success) {
				trackOnboardingConnectionVerified({
					accessToken: data.session?.access_token,
					tenantId: resolveTenantId(),
					url: $page.url,
					currentTier: data.subscription?.tier,
					persona: String(data?.profile?.persona ?? ''),
					provider: selectedProvider
				});
			}
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			isVerifying = false;
		}
	}
	async function verifyConnection() {
		isVerifying = true;
		error = '';
		try {
			await verifyAwsConnectionFlow({
				getAccessToken,
				ensureOnboarded,
				awsAccountId,
				roleArn,
				externalId,
				isManagementAccount,
				organizationId
			});
			success = true;
			currentStep = 3;
			trackOnboardingConnectionVerified({
				accessToken: data.session?.access_token,
				tenantId: resolveTenantId(),
				url: $page.url,
				currentTier: data.subscription?.tier,
				persona: String(data?.profile?.persona ?? ''),
				provider: 'aws'
			});
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			isVerifying = false;
		}
	}
	const bodyProps = $derived({
		data,
		error,
		success,
		copied,
		isLoading,
		isVerifying,
		discoveryDomain,
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
		cloudShellSnippet,
		cloudPlusSampleFeed,
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
	});
</script>

<svelte:head>
	<title>Onboarding | Valdrics</title>
</svelte:head>
<OnboardingPageViewBody
	{...bodyProps}
	bind:currentStep
	bind:selectedProvider
	bind:selectedTab
	bind:discoveryEmail
	bind:discoveryIdpProvider
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
	bind:cloudPlusName
	bind:cloudPlusVendor
	bind:cloudPlusAuthMethod
	bind:cloudPlusApiKey
	bind:cloudPlusFeedInput
	bind:cloudPlusConnectorConfigInput
/>
