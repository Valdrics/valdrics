import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

function expectRedirectLocation(
	callback: () => unknown,
	expected: { status: number; location: string }
): void {
	try {
		callback();
		throw new Error('expected redirect to be thrown');
	} catch (error) {
		const redirectError = error as { status?: number; location?: string };
		expect(redirectError.status).toBe(expected.status);
		expect(redirectError.location).toBe(expected.location);
	}
}

describe('landing motion query canonicalization', () => {
	it('passes through supported motion variants', async () => {
		const result = await load({
			url: new URL('https://example.com/?motion=cinematic')
		} as Parameters<typeof load>[0]);

		expect(result).toEqual({});
	});

	it('canonicalizes supported motion values to lowercase', async () => {
		expectRedirectLocation(
			() =>
				load({
					url: new URL('https://example.com/?motion=CINEMATIC&utm_source=ads')
				} as Parameters<typeof load>[0]),
			{
				status: 308,
				location: '/?motion=cinematic&utm_source=ads'
			}
		);
	});

	it('strips unsupported motion values and preserves other query params', async () => {
		expectRedirectLocation(
			() =>
				load({
					url: new URL('https://example.com/?motion=neon&utm_source=ads&persona=finance')
				} as Parameters<typeof load>[0]),
			{
				status: 308,
				location: '/?utm_source=ads&persona=finance'
			}
		);
	});
});
