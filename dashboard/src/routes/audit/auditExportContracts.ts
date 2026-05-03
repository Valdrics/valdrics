import type { CompliancePackOptions } from '$lib/compliancePack';

export const FOCUS_EXPORT_PROVIDER_OPTIONS = [
	{ value: '', label: 'All providers' },
	{ value: 'aws', label: 'AWS' },
	{ value: 'azure', label: 'Azure' },
	{ value: 'gcp', label: 'GCP' },
	{ value: 'saas', label: 'SaaS' },
	{ value: 'license', label: 'License' },
	{ value: 'platform', label: 'Platform' },
	{ value: 'hybrid', label: 'Hybrid' },
	{ value: 'ai', label: 'AI' }
] as const;

const COMPLIANCE_ADD_ON_PROVIDERS = new Set([
	'aws',
	'azure',
	'gcp',
	'hybrid',
	'license',
	'platform',
	'saas'
]);

export type AuditCompliancePackFilters = {
	packIncludeFocus: boolean;
	packIncludeSavingsProof: boolean;
	packIncludeClosePackage: boolean;
	packCloseEnforceFinalized: boolean;
	packCloseMaxRestatements: number;
	focusProvider: string;
	focusIncludePreliminary: boolean;
	focusStartDate: string;
	focusEndDate: string;
};

export function normalizeComplianceAddOnProvider(provider: string): string | undefined {
	const normalized = provider.trim().toLowerCase();
	return COMPLIANCE_ADD_ON_PROVIDERS.has(normalized) ? normalized : undefined;
}

export function normalizeFocusExportProvider(provider: string): string | undefined {
	const normalized = provider.trim().toLowerCase();
	return normalized ? normalized : undefined;
}

export function buildAuditCompliancePackOptions(
	filters: AuditCompliancePackFilters
): CompliancePackOptions {
	const focusProvider = normalizeFocusExportProvider(filters.focusProvider);
	const addOnProvider = normalizeComplianceAddOnProvider(filters.focusProvider);

	return {
		includeFocusExport: filters.packIncludeFocus,
		focusProvider,
		focusIncludePreliminary: filters.focusIncludePreliminary,
		focusMaxRows: 50000,
		focusStartDate: filters.focusStartDate,
		focusEndDate: filters.focusEndDate,
		includeSavingsProof: filters.packIncludeSavingsProof,
		savingsProvider: addOnProvider,
		savingsStartDate: filters.focusStartDate,
		savingsEndDate: filters.focusEndDate,
		includeClosePackage: filters.packIncludeClosePackage,
		closeProvider: addOnProvider,
		closeStartDate: filters.focusStartDate,
		closeEndDate: filters.focusEndDate,
		closeEnforceFinalized: filters.packCloseEnforceFinalized,
		closeMaxRestatements: filters.packCloseMaxRestatements
	};
}
