import { z } from 'zod';

export const ENFORCEMENT_REQUEST_TIMEOUT_MS = 8000;

export type EnforcementPolicy = {
	terraform_mode: 'shadow' | 'soft' | 'hard';
	k8s_admission_mode: 'shadow' | 'soft' | 'hard';
	require_approval_for_prod: boolean;
	require_approval_for_nonprod: boolean;
	auto_approve_below_monthly_usd: number;
	hard_deny_above_monthly_usd: number;
	default_ttl_seconds: number;
	policy_version?: number;
	updated_at?: string;
};

export type EnforcementBudget = {
	id: string;
	scope_key: string;
	monthly_limit_usd: number | string;
	active: boolean;
};

export type EnforcementCredit = {
	id: string;
	scope_key: string;
	total_amount_usd: number | string;
	remaining_amount_usd: number | string;
	expires_at: string | null;
	reason: string | null;
	active: boolean;
};

export const PolicySchema = z.object({
	terraform_mode: z.enum(['shadow', 'soft', 'hard']),
	k8s_admission_mode: z.enum(['shadow', 'soft', 'hard']),
	require_approval_for_prod: z.boolean(),
	require_approval_for_nonprod: z.boolean(),
	auto_approve_below_monthly_usd: z.number().min(0),
	hard_deny_above_monthly_usd: z.number().gt(0),
	default_ttl_seconds: z.number().int().min(60).max(86400)
});

export function isProPlus(currentTier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes((currentTier ?? '').toLowerCase());
}

export function extractErrorMessage(data: unknown, fallback: string): string {
	if (!data || typeof data !== 'object') return fallback;
	const payload = data as Record<string, unknown>;
	if (typeof payload.detail === 'string' && payload.detail.trim()) return payload.detail;
	if (typeof payload.message === 'string' && payload.message.trim()) return payload.message;
	return fallback;
}

export function buildEnforcementHeaders(accessToken?: string | null): Record<string, string> {
	return { Authorization: `Bearer ${accessToken}` };
}
