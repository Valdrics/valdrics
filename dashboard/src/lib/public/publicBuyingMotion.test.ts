import { describe, expect, it } from 'vitest';

import {
	appendPublicAttribution,
	buildPublicEnterpriseHref,
	buildPublicSalesHref,
	buildPublicSignupHref,
	resolvePublicBuyerPersona,
	resolvePublicBuyingMotion
} from './publicBuyingMotion';

describe('publicBuyingMotion', () => {
	it('keeps operator traffic self-serve first by default', () => {
		const url = new URL(
			'https://example.com/?entry=docs&utm_source=developer-relations&utm_campaign=api_docs'
		);

		expect(resolvePublicBuyerPersona(url)).toBe('cto');
		expect(resolvePublicBuyingMotion(url)).toBe('self_serve_first');
	});

	it('switches to enterprise-first motion for executive and security signals', () => {
		const executiveUrl = new URL(
			'https://example.com/?utm_medium=abm&utm_campaign=procurement_diligence'
		);
		const securityUrl = new URL('https://example.com/?buyer=security');

		expect(resolvePublicBuyerPersona(executiveUrl)).toBe('cfo');
		expect(resolvePublicBuyingMotion(executiveUrl)).toBe('enterprise_first');
		expect(resolvePublicBuyerPersona(securityUrl)).toBe('security');
		expect(resolvePublicBuyingMotion(securityUrl)).toBe('enterprise_first');
	});

	it('builds self-serve and enterprise hrefs with preserved attribution', () => {
		const currentUrl = new URL(
			'https://example.com/resources?utm_source=linkedin&utm_medium=paid_social&utm_campaign=q2_launch&buyer=security'
		);

		expect(
			buildPublicSignupHref('', currentUrl, {
				intent: 'resource_signup',
				entry: 'resources',
				source: 'resource_hub'
			})
		).toBe(
			'/auth/login?entry=resources&source=resource_hub&persona=security&mode=signup&intent=resource_signup&utm_source=linkedin&utm_medium=paid_social&utm_campaign=q2_launch'
		);

		expect(
			buildPublicEnterpriseHref('', currentUrl, {
				entry: 'resources',
				source: 'resource_hub'
			})
		).toBe(
			'/enterprise?entry=resources&source=resource_hub&persona=security&utm_source=linkedin&utm_medium=paid_social&utm_campaign=q2_launch'
		);

		expect(
			buildPublicSalesHref('', currentUrl, {
				entry: 'resources',
				source: 'resource_validation',
				intent: 'enterprise_briefing'
			})
		).toBe(
			'/talk-to-sales?entry=resources&source=resource_validation&persona=security&intent=enterprise_briefing&utm_source=linkedin&utm_medium=paid_social&utm_campaign=q2_launch'
		);
	});

	it('does not overwrite existing destination query params', () => {
		const currentUrl = new URL('https://example.com/?persona=cto&utm_source=docs');

		expect(
			appendPublicAttribution('/enterprise?source=preseed&intent=existing', currentUrl, {
				entry: 'proof',
				source: 'proof_pack',
				extraParams: { intent: 'ignored' }
			})
		).toBe('/enterprise?source=preseed&intent=existing&entry=proof&persona=cto&utm_source=docs');
	});
});
