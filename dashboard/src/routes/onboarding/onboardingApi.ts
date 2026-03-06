import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { getTurnstileToken } from '$lib/security/turnstile';
import type {
	CloudPlusAuthMethod,
	DiscoveryCandidate,
	DiscoveryStageResponse,
	IdpProvider,
	OnboardingProvider
} from './onboardingTypesUtils';

type JsonObject = Record<string, unknown>;

interface ApiErrorPayload {
	detail?: string;
	message?: string;
	error?: string;
}

function extractApiError(payload: unknown, fallback: string): string {
	if (!payload || typeof payload !== 'object') {
		return fallback;
	}
	const maybeError = payload as ApiErrorPayload;
	for (const candidate of [maybeError.detail, maybeError.message, maybeError.error]) {
		if (typeof candidate === 'string' && candidate.trim().length > 0) {
			return candidate;
		}
	}
	return fallback;
}

async function parseJson(response: Response): Promise<JsonObject> {
	return (await response.json().catch(() => ({}))) as JsonObject;
}

function authHeaders(accessToken: string): Record<string, string> {
	return {
		Authorization: `Bearer ${accessToken}`
	};
}

export async function ensureOnboardedRequest(accessToken: string): Promise<{ ok: true } | { ok: false; error: string }> {
	try {
		const turnstileToken = await getTurnstileToken('onboard');
		const response = await api.post(
			edgeApiPath('/settings/onboard'),
			{ tenant_name: 'My Organization' },
			{
				headers: {
					...authHeaders(accessToken),
					...(turnstileToken ? { 'X-Turnstile-Token': turnstileToken } : {})
				}
			}
		);

		if (response.ok) {
			return { ok: true };
		}

		if (response.status === 400) {
			const payload = await parseJson(response);
			if (payload.detail === 'Already onboarded') {
				return { ok: true };
			}
		}

		const payload = await parseJson(response);
		return {
			ok: false,
			error: extractApiError(payload, 'Unable to complete onboarding preparation.')
		};
	} catch {
		return {
			ok: false,
			error: 'Unable to initialize onboarding right now. Please try again.'
		};
	}
}

export async function fetchSetupPayload(
	accessToken: string,
	provider: OnboardingProvider
): Promise<JsonObject> {
	const endpoint =
		provider === 'aws'
			? '/settings/connections/aws/setup'
			: provider === 'azure'
				? '/settings/connections/azure/setup'
				: provider === 'gcp'
					? '/settings/connections/gcp/setup'
					: provider === 'saas'
						? '/settings/connections/saas/setup'
						: '/settings/connections/license/setup';

	const response = await api.post(edgeApiPath(endpoint), undefined, {
		headers: authHeaders(accessToken)
	});
	const payload = await parseJson(response);
	if (!response.ok) {
		throw new Error(extractApiError(payload, 'Failed to fetch setup data'));
	}
	return payload;
}

export async function runDiscoveryStageARequest(
	accessToken: string,
	email: string
): Promise<Partial<DiscoveryStageResponse>> {
	const response = await api.post(
		edgeApiPath('/settings/connections/discovery/stage-a'),
		{ email },
		{
			headers: authHeaders(accessToken)
		}
	);
	const payload = (await parseJson(response)) as Partial<DiscoveryStageResponse>;
	if (!response.ok) {
		throw new Error(extractApiError(payload, 'Failed to run Stage A discovery'));
	}
	return payload;
}

export async function runDiscoveryStageBRequest(
	accessToken: string,
	domain: string,
	idpProvider: IdpProvider
): Promise<Partial<DiscoveryStageResponse>> {
	const response = await api.post(
		edgeApiPath('/settings/connections/discovery/deep-scan'),
		{
			domain,
			idp_provider: idpProvider,
			max_users: 20
		},
		{
			headers: authHeaders(accessToken)
		}
	);
	const payload = (await parseJson(response)) as Partial<DiscoveryStageResponse>;
	if (!response.ok) {
		throw new Error(extractApiError(payload, 'Failed to run Stage B deep scan'));
	}
	return payload;
}

export async function updateDiscoveryCandidateStatusRequest(
	accessToken: string,
	candidateId: string,
	action: 'accept' | 'ignore' | 'connected'
): Promise<DiscoveryCandidate> {
	const response = await api.post(
		edgeApiPath(`/settings/connections/discovery/candidates/${candidateId}/${action}`),
		undefined,
		{
			headers: authHeaders(accessToken)
		}
	);
	const payload = (await parseJson(response)) as unknown as DiscoveryCandidate;
	if (!response.ok) {
		throw new Error(extractApiError(payload, `Failed to ${action} discovery candidate`));
	}
	return payload;
}

async function verifyCreatedConnection(
	accessToken: string,
	provider: 'aws' | 'azure' | 'gcp' | 'saas' | 'license',
	connectionId: string
): Promise<void> {
	const response = await api.post(
		edgeApiPath(`/settings/connections/${provider}/${connectionId}/verify`),
		undefined,
		{
			headers: authHeaders(accessToken)
		}
	);
	const payload = await parseJson(response);
	if (!response.ok) {
		throw new Error(extractApiError(payload, 'Verification failed'));
	}
}

export async function createAndVerifyAzureConnection(
	accessToken: string,
	input: { subscriptionId: string; tenantId: string; clientId: string }
): Promise<void> {
	const createResponse = await api.post(
		edgeApiPath('/settings/connections/azure'),
		{
			name: `Azure-${input.subscriptionId.slice(0, 8)}`,
			azure_tenant_id: input.tenantId,
			subscription_id: input.subscriptionId,
			client_id: input.clientId,
			auth_method: 'workload_identity'
		},
		{
			headers: authHeaders(accessToken)
		}
	);
	const createPayload = await parseJson(createResponse);
	if (!createResponse.ok) {
		throw new Error(extractApiError(createPayload, 'Failed to connect'));
	}

	const connectionId = String(createPayload.id ?? '');
	await verifyCreatedConnection(accessToken, 'azure', connectionId);
}

export async function createAndVerifyGcpConnection(
	accessToken: string,
	input: {
		projectId: string;
		billingProjectId: string;
		billingDataset: string;
		billingTable: string;
	}
): Promise<void> {
	const createResponse = await api.post(
		edgeApiPath('/settings/connections/gcp'),
		{
			name: `GCP-${input.projectId}`,
			project_id: input.projectId,
			billing_project_id: input.billingProjectId,
			billing_dataset: input.billingDataset,
			billing_table: input.billingTable,
			auth_method: 'workload_identity'
		},
		{
			headers: authHeaders(accessToken)
		}
	);
	const createPayload = await parseJson(createResponse);
	if (!createResponse.ok) {
		throw new Error(extractApiError(createPayload, 'Failed to connect'));
	}

	const connectionId = String(createPayload.id ?? '');
	await verifyCreatedConnection(accessToken, 'gcp', connectionId);
}

export async function createAndVerifyCloudPlusConnection(
	accessToken: string,
	input: {
		provider: 'saas' | 'license';
		name: string;
		vendor: string;
		authMethod: CloudPlusAuthMethod;
		apiKey: string | null;
		connectorConfig: Record<string, unknown>;
		feed: Array<Record<string, unknown>>;
	}
): Promise<void> {
	const payload =
		input.provider === 'saas'
			? {
					name: input.name,
					vendor: input.vendor,
					auth_method: input.authMethod,
					api_key: input.apiKey,
					connector_config: input.connectorConfig,
					spend_feed: input.feed
				}
			: {
					name: input.name,
					vendor: input.vendor,
					auth_method: input.authMethod,
					api_key: input.apiKey,
					connector_config: input.connectorConfig,
					license_feed: input.feed
				};

	const createResponse = await api.post(
		edgeApiPath(`/settings/connections/${input.provider}`),
		payload,
		{
			headers: authHeaders(accessToken)
		}
	);
	const createPayload = await parseJson(createResponse);
	if (!createResponse.ok) {
		throw new Error(extractApiError(createPayload, 'Failed to connect'));
	}

	const connectionId = String(createPayload.id ?? '');
	await verifyCreatedConnection(accessToken, input.provider, connectionId);
}

export async function createAndVerifyAwsConnection(
	accessToken: string,
	input: {
		awsAccountId: string;
		roleArn: string;
		externalId: string;
		isManagementAccount: boolean;
		organizationId: string;
	}
): Promise<void> {
	const createResponse = await api.post(
		edgeApiPath('/settings/connections/aws'),
		{
			aws_account_id: input.awsAccountId,
			role_arn: input.roleArn,
			external_id: input.externalId,
			is_management_account: input.isManagementAccount,
			organization_id: input.organizationId,
			region: 'us-east-1'
		},
		{
			headers: authHeaders(accessToken)
		}
	);
	const createPayload = await parseJson(createResponse);
	if (!createResponse.ok) {
		throw new Error(extractApiError(createPayload, 'Failed to create connection'));
	}

	const connectionId = String(createPayload.id ?? '');
	await verifyCreatedConnection(accessToken, 'aws', connectionId);
}
