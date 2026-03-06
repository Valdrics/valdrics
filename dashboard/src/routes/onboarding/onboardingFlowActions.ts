import {
	createAndVerifyAwsConnection,
	createAndVerifyAzureConnection,
	createAndVerifyCloudPlusConnection,
	createAndVerifyGcpConnection,
	runDiscoveryStageARequest,
	runDiscoveryStageBRequest,
	updateDiscoveryCandidateStatusRequest
} from './onboardingApi';
import { extractDomainFromEmail, type DiscoveryCandidate, type IdpProvider, type OnboardingProvider } from './onboardingTypesUtils';

async function requireAccessToken(
	getAccessToken: () => Promise<string | null>
): Promise<string> {
	const token = await getAccessToken();
	if (!token) {
		throw new Error('Please log in first');
	}
	return token;
}

interface DiscoveryFlowBase {
	getAccessToken: () => Promise<string | null>;
	ensureOnboarded: () => Promise<boolean>;
}

export async function runDiscoveryStageAFlow(
	input: DiscoveryFlowBase & {
		email: string;
	}
): Promise<{
	domain: string;
	warnings: string[];
	candidates: DiscoveryCandidate[];
	info: string;
}> {
	const normalizedEmail = input.email.trim();
	if (!normalizedEmail) {
		throw new Error('Enter a valid work email to run discovery.');
	}
	const token = await requireAccessToken(input.getAccessToken);
	const onboarded = await input.ensureOnboarded();
	if (!onboarded) {
		return { domain: '', warnings: [], candidates: [], info: '' };
	}
	const payload = await runDiscoveryStageARequest(token, normalizedEmail);
	const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
	return {
		domain: typeof payload.domain === 'string' ? payload.domain : '',
		warnings: Array.isArray(payload.warnings)
			? payload.warnings.filter((warning): warning is string => typeof warning === 'string')
			: [],
		candidates,
		info: `Stage A complete: found ${candidates.length} candidate(s).`
	};
}

export async function runDiscoveryStageBFlow(
	input: DiscoveryFlowBase & {
		discoveryDomain: string;
		discoveryEmail: string;
		idpProvider: IdpProvider;
		canUseIdpDeepScan: boolean;
	}
): Promise<{
	domain: string;
	warnings: string[];
	candidates: DiscoveryCandidate[];
	info: string;
}> {
	if (!input.canUseIdpDeepScan) {
		throw new Error('Deep scan requires Pro tier or higher.');
	}
	const domain = input.discoveryDomain || extractDomainFromEmail(input.discoveryEmail);
	if (!domain) {
		throw new Error('Run Stage A first or enter a valid email domain.');
	}
	const token = await requireAccessToken(input.getAccessToken);
	const onboarded = await input.ensureOnboarded();
	if (!onboarded) {
		return { domain, warnings: [], candidates: [], info: '' };
	}
	const payload = await runDiscoveryStageBRequest(token, domain, input.idpProvider);
	const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
	return {
		domain: typeof payload.domain === 'string' ? payload.domain : domain,
		warnings: Array.isArray(payload.warnings)
			? payload.warnings.filter((warning): warning is string => typeof warning === 'string')
			: [],
		candidates,
		info: `Stage B complete: ${candidates.length} candidate(s) now in scope.`
	};
}

export async function updateDiscoveryCandidateStatusFlow(input: {
	getAccessToken: () => Promise<string | null>;
	candidateId: string;
	action: 'accept' | 'ignore' | 'connected';
}): Promise<DiscoveryCandidate> {
	const token = await requireAccessToken(input.getAccessToken);
	return updateDiscoveryCandidateStatusRequest(token, input.candidateId, input.action);
}

export async function proceedToVerifyFlow(input: {
	selectedProvider: OnboardingProvider;
	getAccessToken: () => Promise<string | null>;
	azureTenantId: string;
	azureSubscriptionId: string;
	azureClientId: string;
	gcpProjectId: string;
	gcpBillingProjectId: string;
	gcpBillingDataset: string;
	gcpBillingTable: string;
	cloudPlusName: string;
	cloudPlusVendor: string;
	cloudPlusAuthMethod: 'manual' | 'api_key' | 'oauth' | 'csv';
	cloudPlusApiKey: string;
	parseCloudPlusFeed: () => Array<Record<string, unknown>>;
	parseCloudPlusConnectorConfig: () => Record<string, unknown>;
}): Promise<{ currentStep: number; success: boolean }> {
	if (input.selectedProvider === 'aws') {
		return { currentStep: 2, success: false };
	}

	const token = await requireAccessToken(input.getAccessToken);

	if (input.selectedProvider === 'azure') {
		if (!input.azureTenantId || !input.azureSubscriptionId || !input.azureClientId) {
			throw new Error('Please enter Tenant ID, Subscription ID, and Client ID');
		}
		await createAndVerifyAzureConnection(token, {
			subscriptionId: input.azureSubscriptionId,
			tenantId: input.azureTenantId,
			clientId: input.azureClientId
		});
		return { currentStep: 3, success: true };
	}

	if (input.selectedProvider === 'gcp') {
		if (!input.gcpProjectId) {
			throw new Error('Please enter Project ID');
		}
		await createAndVerifyGcpConnection(token, {
			projectId: input.gcpProjectId,
			billingProjectId: input.gcpBillingProjectId || input.gcpProjectId,
			billingDataset: input.gcpBillingDataset,
			billingTable: input.gcpBillingTable
		});
		return { currentStep: 3, success: true };
	}

	if (input.selectedProvider === 'saas' || input.selectedProvider === 'license') {
		if (!input.cloudPlusName.trim() || input.cloudPlusName.trim().length < 3) {
			throw new Error('Please enter a connection name (minimum 3 characters).');
		}
		if (!input.cloudPlusVendor.trim() || input.cloudPlusVendor.trim().length < 2) {
			throw new Error('Please enter a vendor name (minimum 2 characters).');
		}
		if (
			(input.cloudPlusAuthMethod === 'api_key' || input.cloudPlusAuthMethod === 'oauth') &&
			!input.cloudPlusApiKey.trim()
		) {
			throw new Error('API key / OAuth token is required for this auth method.');
		}
		await createAndVerifyCloudPlusConnection(token, {
			provider: input.selectedProvider,
			name: input.cloudPlusName.trim(),
			vendor: input.cloudPlusVendor.trim().toLowerCase(),
			authMethod: input.cloudPlusAuthMethod,
			apiKey: input.cloudPlusApiKey.trim() || null,
			connectorConfig: input.parseCloudPlusConnectorConfig(),
			feed: input.parseCloudPlusFeed()
		});
		return { currentStep: 3, success: true };
	}

	return { currentStep: 2, success: false };
}

export async function verifyAwsConnectionFlow(input: {
	getAccessToken: () => Promise<string | null>;
	ensureOnboarded: () => Promise<boolean>;
	awsAccountId: string;
	roleArn: string;
	externalId: string;
	isManagementAccount: boolean;
	organizationId: string;
}): Promise<void> {
	if (!input.roleArn || !input.awsAccountId) {
		throw new Error('Please enter both AWS Account ID and Role ARN');
	}

	const onboarded = await input.ensureOnboarded();
	if (!onboarded) {
		return;
	}

	const token = await requireAccessToken(input.getAccessToken);
	await createAndVerifyAwsConnection(token, {
		awsAccountId: input.awsAccountId,
		roleArn: input.roleArn,
		externalId: input.externalId,
		isManagementAccount: input.isManagementAccount,
		organizationId: input.organizationId
	});
}
