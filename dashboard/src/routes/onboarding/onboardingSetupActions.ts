import { fetchSetupPayload } from './onboardingApi';
import {
	getProviderLabel,
	normalizeNativeConnectors,
	parseManualFeedSchema,
	resolveProviderFromCandidate,
	type CloudPlusProvider,
	type DiscoveryCandidate,
	type ManualFeedSchema,
	type NativeConnectorMeta,
	type OnboardingProvider
} from './onboardingTypesUtils';

interface FetchSetupFlowInput {
	selectedProvider: OnboardingProvider;
	getAccessToken: () => Promise<string | null>;
	cloudPlusConfigProvider: CloudPlusProvider | null;
	cloudPlusVendor: string;
	cloudPlusConnectorConfigInput: string;
}

interface FetchSetupFlowResult {
	externalId: string;
	magicLink: string;
	cloudformationYaml: string;
	terraformHcl: string;
	cloudShellSnippet: string;
	cloudPlusSampleFeed: string;
	cloudPlusFeedInput: string;
	cloudPlusNativeConnectors: NativeConnectorMeta[];
	cloudPlusManualFeedSchema: ManualFeedSchema;
	cloudPlusVendor: string;
	cloudPlusConnectorConfigInput: string;
	cloudPlusRequiredConfigValues: Record<string, string>;
	cloudPlusConfigProvider: CloudPlusProvider | null;
	shouldApplyCloudPlusVendorDefaults: boolean;
}

export async function fetchSetupDataFlow(
	input: FetchSetupFlowInput
): Promise<FetchSetupFlowResult> {
	const token = await input.getAccessToken();
	if (!token) {
		throw new Error('Please log in first');
	}

	const responseData = await fetchSetupPayload(token, input.selectedProvider);
	const defaults = {
		externalId: '',
		magicLink: '',
		cloudformationYaml: '',
		terraformHcl: '',
		cloudShellSnippet: '',
		cloudPlusSampleFeed: '',
		cloudPlusFeedInput: '[]',
		cloudPlusNativeConnectors: [] as NativeConnectorMeta[],
		cloudPlusManualFeedSchema: { required_fields: [], optional_fields: [] } as ManualFeedSchema,
		cloudPlusVendor: input.cloudPlusVendor,
		cloudPlusConnectorConfigInput: input.cloudPlusConnectorConfigInput,
		cloudPlusRequiredConfigValues: {} as Record<string, string>,
		cloudPlusConfigProvider: input.cloudPlusConfigProvider,
		shouldApplyCloudPlusVendorDefaults: false
	};

	if (input.selectedProvider === 'aws') {
		return {
			...defaults,
			externalId: typeof responseData.external_id === 'string' ? responseData.external_id : '',
			magicLink: typeof responseData.magic_link === 'string' ? responseData.magic_link : '',
			cloudformationYaml:
				typeof responseData.cloudformation_yaml === 'string'
					? responseData.cloudformation_yaml
					: '',
			terraformHcl: typeof responseData.terraform_hcl === 'string' ? responseData.terraform_hcl : ''
		};
	}

	if (input.selectedProvider === 'azure' || input.selectedProvider === 'gcp') {
		return {
			...defaults,
			cloudShellSnippet: typeof responseData.snippet === 'string' ? responseData.snippet : ''
		};
	}

	const providerDefaults: Record<CloudPlusProvider, { vendor: string; config: string }> = {
		saas: { vendor: 'stripe', config: '{}' },
		license: { vendor: 'microsoft_365', config: '{"default_seat_price_usd": 36}' }
	};
	const providerKey = input.selectedProvider as CloudPlusProvider;
	const providerSwitched = input.cloudPlusConfigProvider !== providerKey;
	const nativeConnectors = normalizeNativeConnectors(responseData.native_connectors);
	const sampleFeed = typeof responseData.sample_feed === 'string' ? responseData.sample_feed : '[]';

	return {
		...defaults,
		cloudShellSnippet: typeof responseData.snippet === 'string' ? responseData.snippet : '',
		cloudPlusSampleFeed: sampleFeed,
		cloudPlusFeedInput: sampleFeed,
		cloudPlusNativeConnectors: nativeConnectors,
		cloudPlusManualFeedSchema: parseManualFeedSchema(responseData.manual_feed_schema),
		cloudPlusVendor:
			providerSwitched || !input.cloudPlusVendor.trim()
				? nativeConnectors[0]?.vendor || providerDefaults[providerKey].vendor
				: input.cloudPlusVendor.trim().toLowerCase(),
		cloudPlusConnectorConfigInput:
			providerSwitched || !input.cloudPlusConnectorConfigInput.trim()
				? providerDefaults[providerKey].config
				: input.cloudPlusConnectorConfigInput,
		cloudPlusRequiredConfigValues:
			providerSwitched || !input.cloudPlusConnectorConfigInput.trim()
				? {}
				: defaults.cloudPlusRequiredConfigValues,
		cloudPlusConfigProvider: providerKey,
		shouldApplyCloudPlusVendorDefaults: true
	};
}

interface ConnectDiscoveryCandidateFlowInput {
	candidate: DiscoveryCandidate;
	canUseGrowthFeatures: boolean;
	canUseCloudPlusFeatures: boolean;
	updateDiscoveryCandidateStatus: (
		candidate: DiscoveryCandidate,
		action: 'accept' | 'ignore' | 'connected'
	) => Promise<DiscoveryCandidate | null>;
	setSelectedProvider: (provider: OnboardingProvider) => void;
	setCurrentStep: (step: number) => void;
	fetchSetupData: () => Promise<void>;
	cloudPlusNativeConnectors: NativeConnectorMeta[];
	chooseNativeCloudPlusVendor: (vendor: string) => void;
	setCloudPlusVendor: (vendor: string) => void;
	applyCloudPlusVendorDefaults: (forceRecommendedAuth?: boolean) => void;
	getCloudPlusName: () => string;
	setCloudPlusName: (name: string) => void;
}

export async function connectDiscoveryCandidateFlow(
	input: ConnectDiscoveryCandidateFlowInput
): Promise<string> {
	const provider = resolveProviderFromCandidate(input.candidate);
	if (!provider) {
		throw new Error(
			'This candidate maps to a connector not yet supported in this onboarding flow. Use Connections page.'
		);
	}

	if ((provider === 'azure' || provider === 'gcp') && !input.canUseGrowthFeatures) {
		throw new Error(`${getProviderLabel(provider)} onboarding requires Growth tier or higher.`);
	}
	if ((provider === 'saas' || provider === 'license') && !input.canUseCloudPlusFeatures) {
		throw new Error(`${getProviderLabel(provider)} onboarding requires Pro tier or higher.`);
	}

	const accepted = await input.updateDiscoveryCandidateStatus(input.candidate, 'accept');
	if (!accepted) {
		return '';
	}

	input.setSelectedProvider(provider);
	input.setCurrentStep(1);
	await input.fetchSetupData();

	if (provider === 'saas' || provider === 'license') {
		const preferredVendor = (accepted.connection_vendor_hint || accepted.provider || '')
			.trim()
			.toLowerCase();
		if (preferredVendor) {
			const knownConnector = input.cloudPlusNativeConnectors.find(
				(connector) => connector.vendor === preferredVendor
			);
			if (knownConnector) {
				input.chooseNativeCloudPlusVendor(knownConnector.vendor);
			} else {
				input.setCloudPlusVendor(preferredVendor);
				input.applyCloudPlusVendorDefaults(false);
			}
		}
		if (!input.getCloudPlusName().trim()) {
			const label = accepted.provider.replace(/_/g, ' ');
			input.setCloudPlusName(`${label} connector`);
		}
	}
	return `${accepted.provider} ready for setup.`;
}
