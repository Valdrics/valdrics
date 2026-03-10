import {
	CLOUD_PLUS_AUTH_METHODS,
	parseConnectorConfigInputSafely,
	type CloudPlusAuthMethod,
	type NativeConnectorMeta
} from './onboardingTypesUtils';

export function applyDiscoveryCandidateLocally<T extends { id: string }>(
	candidates: T[],
	updated: T
): T[] {
	return candidates.map((candidate) => (candidate.id === updated.id ? updated : candidate));
}

export function upsertDiscoveryCandidates<
	T extends { id: string; confidence_score: number; provider: string }
>(existing: T[], candidates: T[]): T[] {
	const merged = [...existing];
	for (const candidate of candidates) {
		const existingIndex = merged.findIndex((item) => item.id === candidate.id);
		if (existingIndex >= 0) {
			merged[existingIndex] = candidate;
		} else {
			merged.push(candidate);
		}
	}
	return merged.sort((a, b) => {
		if (b.confidence_score !== a.confidence_score) {
			return b.confidence_score - a.confidence_score;
		}
		return a.provider.localeCompare(b.provider);
	});
}

export function getSelectedNativeConnector(
	vendor: string,
	connectors: NativeConnectorMeta[]
): NativeConnectorMeta | null {
	const normalizedVendor = vendor.trim().toLowerCase();
	if (!normalizedVendor) {
		return null;
	}
	return connectors.find((connector) => connector.vendor === normalizedVendor) ?? null;
}

export function getAvailableCloudPlusAuthMethods(
	selectedConnector: NativeConnectorMeta | null
): CloudPlusAuthMethod[] {
	if (!selectedConnector) {
		return CLOUD_PLUS_AUTH_METHODS;
	}
	return selectedConnector.supported_auth_methods.length
		? selectedConnector.supported_auth_methods
		: CLOUD_PLUS_AUTH_METHODS;
}

interface CloudPlusDefaultsParams {
	vendor: string;
	connectors: NativeConnectorMeta[];
	currentAuthMethod: CloudPlusAuthMethod;
	connectorConfigInput: string;
	requiredConfigValues: Record<string, string>;
	forceRecommendedAuth: boolean;
}

interface CloudPlusDefaultsResult {
	authMethod: CloudPlusAuthMethod;
	requiredConfigValues: Record<string, string>;
}

export function applyCloudPlusVendorDefaults(
	params: CloudPlusDefaultsParams
): CloudPlusDefaultsResult {
	const selectedConnector = getSelectedNativeConnector(params.vendor, params.connectors);
	if (!selectedConnector) {
		return {
			authMethod: params.currentAuthMethod,
			requiredConfigValues: {}
		};
	}

	const supportedAuthMethods = selectedConnector.supported_auth_methods.length
		? selectedConnector.supported_auth_methods
		: CLOUD_PLUS_AUTH_METHODS;
	let authMethod = params.currentAuthMethod;
	if (params.forceRecommendedAuth || !supportedAuthMethods.includes(authMethod)) {
		authMethod = supportedAuthMethods.includes(selectedConnector.recommended_auth_method)
			? selectedConnector.recommended_auth_method
			: (supportedAuthMethods[0] ?? 'manual');
	}

	const existingConfig = parseConnectorConfigInputSafely(params.connectorConfigInput);
	const nextValues: Record<string, string> = {};
	for (const field of selectedConnector.required_connector_config_fields) {
		const currentValue = params.requiredConfigValues[field];
		if (typeof currentValue === 'string' && currentValue.trim().length > 0) {
			nextValues[field] = currentValue;
			continue;
		}
		const configuredValue = existingConfig[field];
		nextValues[field] =
			configuredValue === undefined || configuredValue === null ? '' : String(configuredValue);
	}

	return {
		authMethod,
		requiredConfigValues: nextValues
	};
}

export function parseCloudPlusFeed(feedInput: string): Array<Record<string, unknown>> {
	if (!feedInput.trim()) {
		return [];
	}
	const parsed = JSON.parse(feedInput);
	if (!Array.isArray(parsed)) {
		throw new Error('Feed JSON must be an array of records.');
	}
	return parsed as Array<Record<string, unknown>>;
}

interface ParseConnectorConfigParams {
	connectorConfigInput: string;
	selectedConnector: NativeConnectorMeta | null;
	isNativeAuthMethod: boolean;
	requiredConfigValues: Record<string, string>;
}

export function parseCloudPlusConnectorConfig(
	params: ParseConnectorConfigParams
): Record<string, unknown> {
	let parsed: unknown = {};
	if (params.connectorConfigInput.trim()) {
		try {
			parsed = JSON.parse(params.connectorConfigInput);
		} catch {
			throw new Error('Connector config JSON must be valid.');
		}
		if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
			throw new Error('Connector config JSON must be an object.');
		}
	}

	const connectorConfig: Record<string, unknown> = {
		...(parsed as Record<string, unknown>)
	};
	if (!params.selectedConnector || !params.isNativeAuthMethod) {
		return connectorConfig;
	}

	for (const field of params.selectedConnector.required_connector_config_fields) {
		const fieldValue = (params.requiredConfigValues[field] ?? '').trim();
		if (!fieldValue) {
			throw new Error(
				`connector_config.${field} is required for ${params.selectedConnector.display_name}.`
			);
		}
		if (field.toLowerCase().includes('url') && !/^https?:\/\//i.test(fieldValue)) {
			throw new Error(`connector_config.${field} must be an http(s) URL.`);
		}
		connectorConfig[field] = fieldValue;
	}

	return connectorConfig;
}
