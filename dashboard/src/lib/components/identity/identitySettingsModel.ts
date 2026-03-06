import { z } from 'zod';

import type { ScimGroupMapping } from './identitySettingsTypes';

export const IDENTITY_REQUEST_TIMEOUT_MS = 8000;

const PersonaSchema = z.enum(['engineering', 'finance', 'platform', 'leadership']);

const ScimGroupMappingSchema = z.object({
	group: z.string().min(1).max(255),
	role: z.enum(['admin', 'member']),
	persona: PersonaSchema.nullable().optional()
});

export const IdentitySettingsResponseSchema = z.object({
	sso_enabled: z.boolean(),
	allowed_email_domains: z.array(z.string().min(1).max(255)).max(50),
	sso_federation_enabled: z.boolean(),
	sso_federation_mode: z.enum(['domain', 'provider_id']),
	sso_federation_provider_id: z.string().max(255).nullable().optional(),
	scim_enabled: z.boolean(),
	has_scim_token: z.boolean(),
	scim_last_rotated_at: z.string().nullable(),
	scim_group_mappings: z.array(ScimGroupMappingSchema).max(50).default([])
});

export const IdentitySettingsUpdateSchema = z.object({
	sso_enabled: z.boolean(),
	allowed_email_domains: z.array(z.string().min(1).max(255)).max(50),
	sso_federation_enabled: z.boolean(),
	sso_federation_mode: z.enum(['domain', 'provider_id']),
	sso_federation_provider_id: z.string().max(255).nullable().optional(),
	scim_enabled: z.boolean(),
	scim_group_mappings: z.array(ScimGroupMappingSchema).max(50)
});

export const IdentityDiagnosticsSchema = z.object({
	tier: z.string(),
	sso: z.object({
		enabled: z.boolean(),
		allowed_email_domains: z.array(z.string()),
		enforcement_active: z.boolean(),
		federation_enabled: z.boolean(),
		federation_mode: z.enum(['domain', 'provider_id']),
		federation_ready: z.boolean(),
		current_admin_domain: z.string().nullable(),
		current_admin_domain_allowed: z.boolean().nullable(),
		issues: z.array(z.string())
	}),
	scim: z.object({
		available: z.boolean(),
		enabled: z.boolean(),
		has_token: z.boolean(),
		token_blind_index_present: z.boolean(),
		last_rotated_at: z.string().nullable(),
		token_age_days: z.number().int().nullable(),
		rotation_recommended_days: z.number().int(),
		rotation_overdue: z.boolean(),
		issues: z.array(z.string())
	}),
	recommendations: z.array(z.string())
});

export const RotateTokenResponseSchema = z.object({
	scim_token: z.string().min(16),
	rotated_at: z.string().min(10)
});

export const ScimTokenTestResponseSchema = z.object({
	status: z.string(),
	token_matches: z.boolean()
});

export function uniqueScimMappingsOrThrow(mappings: ScimGroupMapping[]): void {
	const seen = new Set<string>();
	for (const mapping of mappings) {
		const key = mapping.group.trim().toLowerCase();
		if (!key) continue;
		if (seen.has(key)) {
			throw new Error(`Duplicate SCIM group mapping: ${key}`);
		}
		seen.add(key);
	}
}

export function extractErrorMessage(data: unknown, fallback: string): string {
	if (!data || typeof data !== 'object') return fallback;
	const payload = data as Record<string, unknown>;
	const detail = payload.detail;
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const parts = detail
			.map((entry) => {
				if (!entry || typeof entry !== 'object') return '';
				const obj = entry as Record<string, unknown>;
				if (typeof obj.msg === 'string') return obj.msg;
				if (typeof obj.message === 'string') return obj.message;
				return '';
			})
			.filter(Boolean);
		if (parts.length) return parts.join(', ');
	}
	const message = payload.message;
	if (typeof message === 'string' && message.trim()) return message;
	return fallback;
}
