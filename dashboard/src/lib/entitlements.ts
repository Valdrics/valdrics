import { tierAtLeast } from '$lib/tier';

function isAdminRole(role: unknown): boolean {
	const normalized = String(role || '')
		.toLowerCase()
		.trim();
	return normalized === 'admin' || normalized === 'owner';
}

export function canAccessAuditLogs(tier: unknown, role: unknown): boolean {
	return isAdminRole(role) && tierAtLeast(tier, 'pro');
}

export function canAccessOpsJobSlo(tier: unknown, role: unknown): boolean {
	return canAccessAuditLogs(tier, role);
}

export function canAccessOpsAcceptanceEvidence(tier: unknown, role: unknown): boolean {
	return isAdminRole(role) && tierAtLeast(tier, 'pro');
}

export function canAccessOpsCloseWorkflow(tier: unknown, role: unknown): boolean {
	return isAdminRole(role) && tierAtLeast(tier, 'pro');
}

export function canAccessAdminHealth(role: unknown, platformOperator: unknown): boolean {
	return isAdminRole(role) && Boolean(platformOperator);
}
