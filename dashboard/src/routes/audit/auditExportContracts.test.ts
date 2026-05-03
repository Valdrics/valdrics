import { describe, expect, it } from 'vitest';

import {
	FOCUS_EXPORT_PROVIDER_OPTIONS,
	buildAuditCompliancePackOptions,
	normalizeComplianceAddOnProvider,
	normalizeFocusExportProvider
} from './auditExportContracts';

const baseFilters = {
	packIncludeFocus: true,
	packIncludeSavingsProof: true,
	packIncludeClosePackage: true,
	packCloseEnforceFinalized: true,
	packCloseMaxRestatements: 25,
	focusProvider: '',
	focusIncludePreliminary: false,
	focusStartDate: '2026-01-01',
	focusEndDate: '2026-01-31'
};

describe('audit export contracts', () => {
	it('exposes AI as a FOCUS-only provider option', () => {
		expect(FOCUS_EXPORT_PROVIDER_OPTIONS).toContainEqual({ value: 'ai', label: 'AI' });
		expect(normalizeFocusExportProvider(' AI ')).toBe('ai');
		expect(normalizeComplianceAddOnProvider(' AI ')).toBeUndefined();
	});

	it('keeps AI on the FOCUS filter and omits it from savings and close add-ons', () => {
		const options = buildAuditCompliancePackOptions({
			...baseFilters,
			focusProvider: 'ai'
		});

		expect(options.focusProvider).toBe('ai');
		expect(options.savingsProvider).toBeUndefined();
		expect(options.closeProvider).toBeUndefined();
	});

	it('shares non-AI ledger providers with compliance pack add-ons', () => {
		const options = buildAuditCompliancePackOptions({
			...baseFilters,
			focusProvider: ' Platform '
		});

		expect(options.focusProvider).toBe('platform');
		expect(options.savingsProvider).toBe('platform');
		expect(options.closeProvider).toBe('platform');
	});
});
