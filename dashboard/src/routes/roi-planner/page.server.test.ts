import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

function buildRequest(headers: Record<string, string> = {}): Request {
	return new Request('https://example.com/roi-planner', {
		method: 'GET',
		headers
	});
}

function asLoadResult(
	value: Awaited<ReturnType<typeof load>>
): Exclude<Awaited<ReturnType<typeof load>>, void> {
	if (!value) {
		throw new Error('expected load result data');
	}
	return value;
}

describe('roi planner currency detection', () => {
	it('defaults to USD when there is no trusted country header', async () => {
		const result = asLoadResult(
			await load({
				request: buildRequest()
			} as Parameters<typeof load>[0])
		);

		expect(result.detectedCurrencyCode).toBe('USD');
	});

	it('uses supported public geo currencies from trusted headers', async () => {
		const result = asLoadResult(
			await load({
				request: buildRequest({ 'x-vercel-ip-country': 'GB' })
			} as Parameters<typeof load>[0])
		);

		expect(result.detectedCurrencyCode).toBe('GBP');
	});

	it('keeps NG visitors on USD for the public planner surface', async () => {
		const result = asLoadResult(
			await load({
				request: buildRequest({ 'cf-ipcountry': 'NG' })
			} as Parameters<typeof load>[0])
		);

		expect(result.detectedCurrencyCode).toBe('USD');
	});
});
