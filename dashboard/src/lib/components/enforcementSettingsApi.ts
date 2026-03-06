import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import {
	ENFORCEMENT_REQUEST_TIMEOUT_MS,
	extractErrorMessage,
	type EnforcementBudget,
	type EnforcementCredit,
	type EnforcementPolicy
} from './enforcementSettingsModel';

function headers(accessToken?: string | null): Record<string, string> {
	return { Authorization: `Bearer ${accessToken}` };
}

async function getWithTimeout(path: string, accessToken?: string | null): Promise<Response> {
	return api.get(edgeApiPath(path), {
		headers: headers(accessToken),
		timeoutMs: ENFORCEMENT_REQUEST_TIMEOUT_MS
	});
}

export async function loadEnforcementPolicy(
	accessToken?: string | null
): Promise<EnforcementPolicy | null> {
	const response = await getWithTimeout('/enforcement/policies', accessToken);
	if (response.status === 403 || response.status === 404) return null;
	if (!response.ok) {
		const payload = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(payload, 'Failed to load enforcement policy'));
	}
	return (await response.json()) as EnforcementPolicy;
}

export async function loadEnforcementBudgets(
	accessToken?: string | null
): Promise<EnforcementBudget[]> {
	const response = await getWithTimeout('/enforcement/budgets', accessToken);
	if (response.status === 403 || response.status === 404) return [];
	if (!response.ok) {
		const payload = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(payload, 'Failed to load enforcement budgets'));
	}
	return ((await response.json()) as EnforcementBudget[]) ?? [];
}

export async function loadEnforcementCredits(
	accessToken?: string | null
): Promise<EnforcementCredit[]> {
	const response = await getWithTimeout('/enforcement/credits', accessToken);
	if (response.status === 403 || response.status === 404) return [];
	if (!response.ok) {
		const payload = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(payload, 'Failed to load enforcement credits'));
	}
	return ((await response.json()) as EnforcementCredit[]) ?? [];
}

export async function saveEnforcementPolicy(
	accessToken: string | null | undefined,
	policy: EnforcementPolicy
): Promise<void> {
	const response = await api.post(edgeApiPath('/enforcement/policies'), policy, {
		headers: headers(accessToken)
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(payload, 'Failed to save enforcement policy'));
	}
}

export async function saveEnforcementBudget(
	accessToken: string | null | undefined,
	payload: {
		scope_key: string;
		monthly_limit_usd: number;
		active: boolean;
	}
): Promise<void> {
	const response = await api.post(edgeApiPath('/enforcement/budgets'), payload, {
		headers: headers(accessToken)
	});
	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(body, 'Failed to save enforcement budget'));
	}
}

export async function createEnforcementCredit(
	accessToken: string | null | undefined,
	payload: {
		scope_key: string;
		total_amount_usd: number;
		expires_at: string | null;
		reason: string | null;
	}
): Promise<void> {
	const response = await api.post(edgeApiPath('/enforcement/credits'), payload, {
		headers: headers(accessToken)
	});
	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(body, 'Failed to create enforcement credit'));
	}
}
