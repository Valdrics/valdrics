import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

function buildRequest(url: string, headers: Record<string, string> = {}): Request {
	return new Request(url, {
		method: 'GET',
		headers
	});
}

async function expectRedirectLocation(
	callback: () => unknown,
	expected: { status: number; location: string }
): Promise<void> {
	try {
		await callback();
		throw new Error('expected redirect to be thrown');
	} catch (error) {
		const redirectError = error as { status?: number; location?: string };
		expect(redirectError.status).toBe(expected.status);
		expect(redirectError.location).toBe(expected.location);
	}
}

function asLoadResult(
	value: Awaited<ReturnType<typeof load>>
): Exclude<Awaited<ReturnType<typeof load>>, void> {
	if (!value) {
		throw new Error('expected load result data');
	}
	return value;
}

describe('landing motion query canonicalization', () => {
	it('passes through supported motion variants', async () => {
		const result = asLoadResult(
			await load({
				url: new URL('https://example.com/?motion=cinematic'),
				request: buildRequest('https://example.com/?motion=cinematic'),
				locals: {
					safeGetSession: async () => ({ user: null })
				}
			} as Parameters<typeof load>[0])
		);

		expect(result.landingHero).toMatchObject({
			initialExperiments: {
				buyerPersonaDefault: 'cto',
				heroVariant: 'control_every_dollar',
				ctaVariant: 'start_free',
				sectionOrderVariant: 'problem_first',
				seed: 'default'
			},
			includeExperimentQueryParams: false,
			initialMotionProfile: 'cinematic',
			canonicalUrl: 'https://example.com/',
			ogImageUrl: 'https://example.com/og-image.png',
			detectedCurrencyCode: 'USD',
			buyerPersonaId: 'cto',
			heroPrimaryIntent: 'engineering_control',
			heroTitle: 'Control cloud spend without slowing delivery.',
			heroSubtitle:
				'Valdrics gives finance and engineering one workflow for triage, approval, execution, and savings proof.',
			initialSnapshot: {
				id: 'snp-2026-02-27-a'
			}
		});
	});

	it('returns landing hero defaults when no motion query is present', async () => {
		const result = asLoadResult(
			await load({
				url: new URL('https://example.com/?persona=security'),
				request: buildRequest('https://example.com/?persona=security'),
				locals: {
					safeGetSession: async () => ({ user: null })
				}
			} as Parameters<typeof load>[0])
		);

		expect(result.landingHero).toMatchObject({
			initialExperiments: {
				buyerPersonaDefault: 'security',
				heroVariant: 'control_every_dollar',
				ctaVariant: 'book_briefing',
				sectionOrderVariant: 'problem_first',
				seed: 'default'
			},
			includeExperimentQueryParams: false,
			initialMotionProfile: 'subtle',
			canonicalUrl: 'https://example.com/',
			ogImageUrl: 'https://example.com/og-image.png',
			detectedCurrencyCode: 'USD',
			buyerPersonaId: 'security',
			heroPrimaryIntent: 'security_governance',
			heroTitle: 'Review spend-changing actions with context.',
			heroSubtitle:
				'Valdrics keeps policy checks, approval lineage, and decision evidence attached before cost-changing actions move.',
			initialSnapshot: {
				id: 'snp-2026-02-27-a'
			}
		});
	});

	it('uses trusted geo headers but keeps the public landing USD-first for NG visitors', async () => {
		const result = asLoadResult(
			await load({
				url: new URL('https://example.com/'),
				request: buildRequest('https://example.com/', { 'cf-ipcountry': 'NG' }),
				locals: {
					safeGetSession: async () => ({ user: null })
				}
			} as Parameters<typeof load>[0])
		);

		expect(result.landingHero.detectedCurrencyCode).toBe('USD');
	});

	it('uses trusted geo headers for supported public landing currencies', async () => {
		const result = asLoadResult(
			await load({
				url: new URL('https://example.com/'),
				request: buildRequest('https://example.com/', { 'cf-ipcountry': 'GB' }),
				locals: {
					safeGetSession: async () => ({ user: null })
				}
			} as Parameters<typeof load>[0])
		);

		expect(result.landingHero.detectedCurrencyCode).toBe('GBP');
	});

	it('canonicalizes supported motion values to lowercase', async () => {
		await expectRedirectLocation(
			() =>
				load({
					url: new URL('https://example.com/?motion=CINEMATIC&utm_source=ads'),
					request: buildRequest('https://example.com/?motion=CINEMATIC&utm_source=ads'),
					locals: {
						safeGetSession: async () => ({ user: null })
					}
				} as Parameters<typeof load>[0]),
			{
				status: 308,
				location: '/?motion=cinematic&utm_source=ads'
			}
		);
	});

	it('strips unsupported motion values and preserves other query params', async () => {
		await expectRedirectLocation(
			() =>
				load({
					url: new URL('https://example.com/?motion=neon&utm_source=ads&persona=finance'),
					request: buildRequest('https://example.com/?motion=neon&utm_source=ads&persona=finance'),
					locals: {
						safeGetSession: async () => ({ user: null })
					}
				} as Parameters<typeof load>[0]),
			{
				status: 308,
				location: '/?utm_source=ads&persona=finance'
			}
		);
	});

	it('redirects authenticated users to the dedicated dashboard route', async () => {
		await expectRedirectLocation(
			() =>
				load({
					url: new URL('https://example.com/?start_date=2024-01-01&end_date=2024-01-31'),
					request: buildRequest('https://example.com/?start_date=2024-01-01&end_date=2024-01-31'),
					locals: {
						safeGetSession: async () => ({ user: { id: 'user-1' } })
					}
				} as Parameters<typeof load>[0]),
			{
				status: 307,
				location: '/dashboard?start_date=2024-01-01&end_date=2024-01-31'
			}
		);
	});
});
