export type CloudPlusAuthMethod = 'manual' | 'api_key' | 'oauth' | 'csv';
export type CloudPlusProvider = 'saas' | 'license';
export type IdpProvider = 'microsoft_365' | 'google_workspace';
export type DiscoveryStatus = 'pending' | 'accepted' | 'ignored' | 'connected';
export type OnboardingProvider = 'aws' | 'azure' | 'gcp' | 'saas' | 'license';

export interface NativeConnectorMeta {
	vendor: string;
	display_name: string;
	recommended_auth_method: CloudPlusAuthMethod;
	supported_auth_methods: CloudPlusAuthMethod[];
	required_connector_config_fields: string[];
	optional_connector_config_fields: string[];
}

export interface ManualFeedSchema {
	required_fields: string[];
	optional_fields: string[];
}

export interface DiscoveryCandidate {
	id: string;
	domain: string;
	category: string;
	provider: string;
	source: string;
	status: DiscoveryStatus;
	confidence_score: number;
	requires_admin_auth: boolean;
	connection_target: string | null;
	connection_vendor_hint: string | null;
	evidence: string[];
	details: Record<string, unknown>;
	last_seen_at: string;
	created_at: string;
	updated_at: string;
}

export interface DiscoveryStageResponse {
	domain: string;
	candidates: DiscoveryCandidate[];
	warnings: string[];
	total_candidates: number;
}

export const CLOUD_PLUS_AUTH_METHODS: CloudPlusAuthMethod[] = ['manual', 'api_key', 'oauth', 'csv'];

export function getProviderLabel(provider: OnboardingProvider): string {
	switch (provider) {
		case 'aws':
			return 'AWS';
		case 'azure':
			return 'Azure';
		case 'gcp':
			return 'GCP';
		case 'saas':
			return 'SaaS';
		case 'license':
			return 'License';
	}
}

export function extractDomainFromEmail(value: string): string {
	const normalized = value.trim().toLowerCase();
	const at = normalized.lastIndexOf('@');
	if (at <= 0 || at >= normalized.length - 1) {
		return '';
	}
	return normalized.slice(at + 1);
}

export function getDiscoveryCategoryLabel(category: string): string {
	if (category === 'cloud_provider') return 'Cloud';
	if (category === 'cloud_plus') return 'Cloud+';
	if (category === 'license') return 'License';
	if (category === 'platform') return 'Platform';
	return category;
}

export function formatDiscoveryConfidence(score: number): string {
	if (!Number.isFinite(score)) {
		return '0%';
	}
	const bounded = Math.max(0, Math.min(score, 1));
	return `${Math.round(bounded * 100)}%`;
}

export function resolveProviderFromCandidate(
	candidate: DiscoveryCandidate
): 'aws' | 'azure' | 'gcp' | 'saas' | 'license' | null {
	if (candidate.category === 'cloud_provider') {
		if (
			candidate.provider === 'aws' ||
			candidate.provider === 'azure' ||
			candidate.provider === 'gcp'
		) {
			return candidate.provider;
		}
		return null;
	}
	if (candidate.category === 'license') {
		return 'license';
	}
	if (candidate.category === 'cloud_plus') {
		return 'saas';
	}
	return null;
}

export function toCloudPlusAuthMethod(
	value: unknown,
	fallback: CloudPlusAuthMethod = 'manual'
): CloudPlusAuthMethod {
	if (typeof value !== 'string') {
		return fallback;
	}
	const normalized = value.trim().toLowerCase();
	if (
		normalized === 'manual' ||
		normalized === 'api_key' ||
		normalized === 'oauth' ||
		normalized === 'csv'
	) {
		return normalized;
	}
	return fallback;
}

export function parseStringArray(value: unknown): string[] {
	if (!Array.isArray(value)) {
		return [];
	}
	return value
		.filter((item): item is string => typeof item === 'string')
		.map((item) => item.trim())
		.filter((item) => item.length > 0);
}

export function normalizeNativeConnectors(value: unknown): NativeConnectorMeta[] {
	if (!Array.isArray(value)) {
		return [];
	}

	return value
		.map((raw) => {
			if (!raw || typeof raw !== 'object') {
				return null;
			}
			const item = raw as Record<string, unknown>;
			const vendor = typeof item.vendor === 'string' ? item.vendor.trim().toLowerCase() : '';
			if (!vendor) {
				return null;
			}
			const displayName =
				typeof item.display_name === 'string' && item.display_name.trim().length > 0
					? item.display_name.trim()
					: vendor;
			const supportedAuthMethodsRaw = parseStringArray(item.supported_auth_methods).map(
				(authMethod) => toCloudPlusAuthMethod(authMethod)
			);
			const supportedAuthMethods: CloudPlusAuthMethod[] = supportedAuthMethodsRaw.length
				? supportedAuthMethodsRaw
				: ['manual'];

			return {
				vendor,
				display_name: displayName,
				recommended_auth_method: toCloudPlusAuthMethod(
					item.recommended_auth_method,
					supportedAuthMethods[0] ?? 'manual'
				),
				supported_auth_methods: supportedAuthMethods,
				required_connector_config_fields: parseStringArray(item.required_connector_config_fields),
				optional_connector_config_fields: parseStringArray(item.optional_connector_config_fields)
			} satisfies NativeConnectorMeta;
		})
		.filter((item): item is NativeConnectorMeta => item !== null);
}

export function parseManualFeedSchema(value: unknown): ManualFeedSchema {
	if (!value || typeof value !== 'object') {
		return { required_fields: [], optional_fields: [] };
	}
	const schema = value as Record<string, unknown>;
	return {
		required_fields: parseStringArray(schema.required_fields),
		optional_fields: parseStringArray(schema.optional_fields)
	};
}

export function parseConnectorConfigInputSafely(input: string): Record<string, unknown> {
	if (!input.trim()) {
		return {};
	}
	try {
		const parsed = JSON.parse(input);
		if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
			return {};
		}
		return parsed as Record<string, unknown>;
	} catch {
		return {};
	}
}
