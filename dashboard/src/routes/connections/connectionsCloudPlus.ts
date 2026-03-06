export type CloudPlusProvider = 'saas' | 'license' | 'platform' | 'hybrid';

export type CloudPlusAuthMethod = 'manual' | 'api_key' | 'oauth' | 'csv';

export interface CloudPlusCreateInput {
	provider: CloudPlusProvider;
	name: string;
	vendor: string;
	authMethod: CloudPlusAuthMethod;
	apiKey: string;
	apiSecret: string;
	connectorConfigRaw: string;
	feedRaw: string;
}

export interface PreparedCloudPlusCreateRequest {
	provider: CloudPlusProvider;
	name: string;
	vendor: string;
	authMethod: CloudPlusAuthMethod;
	apiKey: string | null;
	apiSecret: string | null;
	connectorConfig: Record<string, unknown>;
	feed: Array<Record<string, unknown>>;
}

export function parseJsonObject(raw: string, fieldName: string): Record<string, unknown> {
	if (!raw.trim()) return {};
	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch {
		throw new Error(`${fieldName} must be valid JSON.`);
	}
	if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
		throw new Error(`${fieldName} must be a JSON object.`);
	}
	return parsed as Record<string, unknown>;
}

export function parseJsonArray(raw: string, fieldName: string): Array<Record<string, unknown>> {
	if (!raw.trim()) return [];
	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch {
		throw new Error(`${fieldName} must be valid JSON.`);
	}
	if (!Array.isArray(parsed)) {
		throw new Error(`${fieldName} must be a JSON array.`);
	}
	return parsed as Array<Record<string, unknown>>;
}

export function extractErrorMessage(payload: unknown, fallback: string): string {
	if (!payload || typeof payload !== 'object') return fallback;
	const maybeError = payload as { detail?: unknown; message?: unknown; error?: unknown };
	for (const candidate of [maybeError.detail, maybeError.message, maybeError.error]) {
		if (typeof candidate === 'string' && candidate.trim()) return candidate;
	}
	return fallback;
}

function validatePlatformConnectorConfig(
	vendorKey: string,
	connectorConfig: Record<string, unknown>,
	apiSecret: string
): void {
	if (['ledger_http', 'cmdb_ledger', 'cmdb-ledger', 'ledger'].includes(vendorKey)) {
		if (typeof connectorConfig.base_url !== 'string' || !connectorConfig.base_url.trim()) {
			throw new Error('Platform ledger_http requires connector_config.base_url.');
		}
	}

	if (vendorKey === 'datadog') {
		if (!apiSecret) throw new Error('Datadog requires an application key (api_secret).');
		if (typeof connectorConfig.unit_prices_usd !== 'object' || !connectorConfig.unit_prices_usd) {
			throw new Error('Datadog requires connector_config.unit_prices_usd for pricing.');
		}
	}

	if (['newrelic', 'new_relic', 'new-relic'].includes(vendorKey)) {
		if (connectorConfig.account_id === undefined || connectorConfig.account_id === null) {
			throw new Error('New Relic requires connector_config.account_id.');
		}
		if (!connectorConfig.nrql_template && !connectorConfig.nrql_query) {
			throw new Error('New Relic requires connector_config.nrql_template.');
		}
		if (typeof connectorConfig.unit_prices_usd !== 'object' || !connectorConfig.unit_prices_usd) {
			throw new Error('New Relic requires connector_config.unit_prices_usd for pricing.');
		}
	}
}

function validateHybridConnectorConfig(
	vendorKey: string,
	connectorConfig: Record<string, unknown>,
	apiSecret: string
): void {
	if (['ledger_http', 'cmdb_ledger', 'cmdb-ledger', 'ledger'].includes(vendorKey)) {
		if (typeof connectorConfig.base_url !== 'string' || !connectorConfig.base_url.trim()) {
			throw new Error('Hybrid ledger_http requires connector_config.base_url.');
		}
	}

	if (['openstack', 'cloudkitty'].includes(vendorKey)) {
		if (!apiSecret) throw new Error('OpenStack/CloudKitty requires api_secret.');
		if (typeof connectorConfig.auth_url !== 'string' || !connectorConfig.auth_url.trim()) {
			throw new Error('OpenStack/CloudKitty requires connector_config.auth_url.');
		}
		if (
			typeof connectorConfig.cloudkitty_base_url !== 'string' ||
			!connectorConfig.cloudkitty_base_url.trim()
		) {
			throw new Error('OpenStack/CloudKitty requires connector_config.cloudkitty_base_url.');
		}
	}

	if (['vmware', 'vcenter', 'vsphere'].includes(vendorKey)) {
		if (!apiSecret) throw new Error('VMware/vCenter requires a password (api_secret).');
		if (typeof connectorConfig.base_url !== 'string' || !connectorConfig.base_url.trim()) {
			throw new Error('VMware/vCenter requires connector_config.base_url.');
		}
		if (typeof connectorConfig.cpu_hour_usd !== 'number' || connectorConfig.cpu_hour_usd <= 0) {
			throw new Error('VMware/vCenter requires connector_config.cpu_hour_usd > 0.');
		}
		if (
			typeof connectorConfig.ram_gb_hour_usd !== 'number' ||
			connectorConfig.ram_gb_hour_usd <= 0
		) {
			throw new Error('VMware/vCenter requires connector_config.ram_gb_hour_usd > 0.');
		}
	}
}

export function prepareCloudPlusCreateRequest(
	input: CloudPlusCreateInput
): PreparedCloudPlusCreateRequest {
	const name = input.name.trim();
	const vendor = input.vendor.trim();
	const apiKey = input.apiKey.trim();
	const apiSecret = input.apiSecret.trim();

	if (name.length < 3) throw new Error('Connection name must have at least 3 characters.');
	if (vendor.length < 2) throw new Error('Vendor must have at least 2 characters.');
	if ((input.authMethod === 'api_key' || input.authMethod === 'oauth') && !apiKey) {
		throw new Error('API key or OAuth token is required for selected auth method.');
	}

	const connectorConfig = parseJsonObject(input.connectorConfigRaw, 'Connector config');
	const feed = parseJsonArray(input.feedRaw, 'Feed');
	const vendorKey = vendor.toLowerCase();

	if (input.authMethod === 'api_key') {
		if (input.provider === 'platform') {
			validatePlatformConnectorConfig(vendorKey, connectorConfig, apiSecret);
		}
		if (input.provider === 'hybrid') {
			validateHybridConnectorConfig(vendorKey, connectorConfig, apiSecret);
		}
	}

	return {
		provider: input.provider,
		name,
		vendor,
		authMethod: input.authMethod,
		apiKey: apiKey || null,
		apiSecret: apiSecret || null,
		connectorConfig,
		feed
	};
}

export function buildCloudPlusCreatePayload(
	request: PreparedCloudPlusCreateRequest
): Record<string, unknown> {
	if (request.provider === 'license') {
		return {
			name: request.name,
			vendor: request.vendor,
			auth_method: request.authMethod,
			api_key: request.apiKey,
			connector_config: request.connectorConfig,
			license_feed: request.feed
		};
	}

	if (request.provider === 'platform' || request.provider === 'hybrid') {
		return {
			name: request.name,
			vendor: request.vendor,
			auth_method: request.authMethod,
			api_key: request.apiKey,
			api_secret: request.apiSecret,
			connector_config: request.connectorConfig,
			spend_feed: request.feed
		};
	}

	return {
		name: request.name,
		vendor: request.vendor,
		auth_method: request.authMethod,
		api_key: request.apiKey,
		connector_config: request.connectorConfig,
		spend_feed: request.feed
	};
}
