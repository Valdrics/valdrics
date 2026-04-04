import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import {
	extractErrorMessage,
	IdentitySettingsResponseSchema,
	IdentitySettingsUpdateSchema
} from './identitySettingsModel';
import { parseDomains } from './identitySettingsHelpers';
import type { IdentitySettings } from './identitySettingsTypes';

function normalizeIdentitySettings(settings: IdentitySettings): IdentitySettings {
	return {
		...settings,
		sso_federation_provider_id: settings.sso_federation_provider_id ?? '',
		scim_group_mappings: (settings.scim_group_mappings ?? []).map((mapping) => ({
			...mapping,
			persona: mapping.persona ?? null
		}))
	};
}

function buildHeaders(accessToken: string): Record<string, string> {
	return {
		Authorization: `Bearer ${accessToken}`
	};
}

export async function loadIdentitySettingsState(
	accessToken: string,
	requestTimeoutMs: number
): Promise<{ settings: IdentitySettings | null; domainsText: string }> {
	const res = await api.get(edgeApiPath('/settings/identity'), {
		headers: buildHeaders(accessToken),
		timeoutMs: requestTimeoutMs
	});

	if (res.status === 403) {
		return {
			settings: null,
			domainsText: ''
		};
	}

	if (!res.ok) {
		const data = await res.json().catch(() => ({}));
		throw new Error(extractErrorMessage(data, 'Failed to load identity settings'));
	}

	const parsed = IdentitySettingsResponseSchema.safeParse(await res.json());
	if (!parsed.success) {
		throw parsed.error;
	}

	const settings = normalizeIdentitySettings(parsed.data as IdentitySettings);
	return {
		settings,
		domainsText: (parsed.data.allowed_email_domains ?? []).join(', ')
	};
}

export async function saveIdentitySettingsState(
	accessToken: string,
	settings: IdentitySettings,
	domainsText: string
): Promise<{ settings: IdentitySettings; domainsText: string }> {
	const payload = {
		sso_enabled: settings.sso_enabled,
		allowed_email_domains: parseDomains(domainsText),
		sso_federation_enabled: settings.sso_federation_enabled,
		sso_federation_mode: settings.sso_federation_mode,
		sso_federation_provider_id:
			settings.sso_federation_mode === 'provider_id'
				? (settings.sso_federation_provider_id?.trim() ?? null)
				: null,
		scim_enabled: settings.scim_enabled,
		scim_group_mappings: (settings.scim_group_mappings ?? []).map((mapping) => ({
			group: mapping.group.trim().toLowerCase(),
			role: mapping.role,
			persona: mapping.persona || null
		}))
	};

	const validated = IdentitySettingsUpdateSchema.safeParse(payload);
	if (!validated.success) {
		throw validated.error;
	}

	const res = await api.put(edgeApiPath('/settings/identity'), validated.data, {
		headers: buildHeaders(accessToken)
	});
	if (!res.ok) {
		const data = await res.json().catch(() => ({}));
		throw new Error(extractErrorMessage(data, 'Failed to save identity settings'));
	}

	const parsed = IdentitySettingsResponseSchema.safeParse(await res.json());
	if (!parsed.success) {
		throw parsed.error;
	}

	const nextSettings = normalizeIdentitySettings(parsed.data as IdentitySettings);
	return {
		settings: nextSettings,
		domainsText: (parsed.data.allowed_email_domains ?? []).join(', ')
	};
}
