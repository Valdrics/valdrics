import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import {
	buildCloudPlusCreatePayload,
	extractErrorMessage,
	prepareCloudPlusCreateRequest
} from './connectionsCloudPlus';

export type CloudPlusProvider = 'saas' | 'license' | 'platform' | 'hybrid';
export type CloudPlusAuthMethod = 'manual' | 'api_key' | 'oauth' | 'csv';
type CloudPlusPlatformAuthMethod = 'manual' | 'api_key' | 'csv';

export type ConnectionsCloudPlusFormsState = {
	saasName: string;
	saasVendor: string;
	saasAuthMethod: CloudPlusAuthMethod;
	saasApiKey: string;
	saasConnectorConfig: string;
	saasFeedInput: string;
	licenseName: string;
	licenseVendor: string;
	licenseAuthMethod: CloudPlusAuthMethod;
	licenseApiKey: string;
	licenseConnectorConfig: string;
	licenseFeedInput: string;
	platformName: string;
	platformVendor: string;
	platformAuthMethod: CloudPlusPlatformAuthMethod;
	platformApiKey: string;
	platformApiSecret: string;
	platformConnectorConfig: string;
	platformFeedInput: string;
	hybridName: string;
	hybridVendor: string;
	hybridAuthMethod: CloudPlusPlatformAuthMethod;
	hybridApiKey: string;
	hybridApiSecret: string;
	hybridConnectorConfig: string;
	hybridFeedInput: string;
};

type CloudPlusCreateFields = {
	name: string;
	vendor: string;
	authMethod: CloudPlusAuthMethod;
	apiKey: string;
	apiSecret: string;
	connectorConfigRaw: string;
	feedRaw: string;
};

function authHeaders(accessToken: string | null | undefined): Record<string, string> {
	return {
		'Content-Type': 'application/json',
		Authorization: `Bearer ${accessToken ?? ''}`
	};
}

export function buildCloudPlusCreateFields(
	provider: CloudPlusProvider,
	forms: ConnectionsCloudPlusFormsState
): CloudPlusCreateFields {
	switch (provider) {
		case 'saas':
			return {
				name: forms.saasName,
				vendor: forms.saasVendor,
				authMethod: forms.saasAuthMethod,
				apiKey: forms.saasApiKey,
				apiSecret: '',
				connectorConfigRaw: forms.saasConnectorConfig,
				feedRaw: forms.saasFeedInput
			};
		case 'license':
			return {
				name: forms.licenseName,
				vendor: forms.licenseVendor,
				authMethod: forms.licenseAuthMethod,
				apiKey: forms.licenseApiKey,
				apiSecret: '',
				connectorConfigRaw: forms.licenseConnectorConfig,
				feedRaw: forms.licenseFeedInput
			};
		case 'platform':
			return {
				name: forms.platformName,
				vendor: forms.platformVendor,
				authMethod: forms.platformAuthMethod,
				apiKey: forms.platformApiKey,
				apiSecret: forms.platformApiSecret,
				connectorConfigRaw: forms.platformConnectorConfig,
				feedRaw: forms.platformFeedInput
			};
		case 'hybrid':
			return {
				name: forms.hybridName,
				vendor: forms.hybridVendor,
				authMethod: forms.hybridAuthMethod,
				apiKey: forms.hybridApiKey,
				apiSecret: forms.hybridApiSecret,
				connectorConfigRaw: forms.hybridConnectorConfig,
				feedRaw: forms.hybridFeedInput
			};
	}
}

export function resetCloudPlusForms(
	provider: CloudPlusProvider,
	forms: ConnectionsCloudPlusFormsState
): ConnectionsCloudPlusFormsState {
	switch (provider) {
		case 'saas':
			return {
				...forms,
				saasName: '',
				saasApiKey: '',
				saasConnectorConfig: '{}',
				saasFeedInput: '[]'
			};
		case 'license':
			return {
				...forms,
				licenseName: '',
				licenseApiKey: '',
				licenseConnectorConfig: '{"default_seat_price_usd": 36}',
				licenseFeedInput: '[]'
			};
		case 'platform':
			return {
				...forms,
				platformName: '',
				platformApiKey: '',
				platformApiSecret: '',
				platformConnectorConfig: '{}',
				platformFeedInput: '[]'
			};
		case 'hybrid':
			return {
				...forms,
				hybridName: '',
				hybridApiKey: '',
				hybridApiSecret: '',
				hybridConnectorConfig: '{}',
				hybridFeedInput: '[]'
			};
	}
}

export async function createAndVerifyCloudPlusConnection(args: {
	provider: CloudPlusProvider;
	accessToken: string | null | undefined;
	fields: CloudPlusCreateFields;
}): Promise<{ message: string }> {
	const { provider, accessToken, fields } = args;
	const headers = authHeaders(accessToken);
	const request = prepareCloudPlusCreateRequest({
		provider,
		name: fields.name,
		vendor: fields.vendor,
		authMethod: fields.authMethod,
		apiKey: fields.apiKey,
		apiSecret: fields.apiSecret,
		connectorConfigRaw: fields.connectorConfigRaw,
		feedRaw: fields.feedRaw
	});
	const payload = buildCloudPlusCreatePayload(request);

	const response = await api.post(edgeApiPath(`/settings/connections/${provider}`), payload, {
		headers
	});
	const body = await response.json().catch(() => ({}));
	if (!response.ok) {
		throw new Error(
			extractErrorMessage(body, `Failed to create ${provider.toUpperCase()} connection.`)
		);
	}

	const connectionId =
		typeof (body as { id?: unknown }).id === 'string' ? (body as { id: string }).id : null;
	if (!connectionId) {
		throw new Error(`Failed to read ${provider.toUpperCase()} connection id from create response.`);
	}

	await verifyCloudPlusConnectionRequest({
		provider,
		connectionId,
		accessToken
	});

	return { message: `${provider.toUpperCase()} connection created and verified.` };
}

export async function verifyCloudPlusConnectionRequest(args: {
	provider: CloudPlusProvider;
	connectionId: string;
	accessToken: string | null | undefined;
}): Promise<{ message: string }> {
	const { provider, connectionId, accessToken } = args;
	const response = await api.post(
		edgeApiPath(`/settings/connections/${provider}/${connectionId}/verify`),
		{},
		{ headers: authHeaders(accessToken) }
	);
	const body = await response.json().catch(() => ({}));
	if (!response.ok) {
		throw new Error(
			extractErrorMessage(body, `Failed to verify ${provider.toUpperCase()} connection.`)
		);
	}
	return { message: extractErrorMessage(body, `${provider.toUpperCase()} connection verified.`) };
}
