import { describe, expect, it, vi } from 'vitest';
import { load } from './+page';

type LoadResult = Record<string, unknown>;

describe('admin landing campaigns load contract', () => {
	it('returns immediately without API fetch when unauthenticated', async () => {
		const fetchMock = vi.fn(async () => new Response('{}'));

		const result = (await load({
			fetch: fetchMock as unknown as typeof fetch,
			parent: async () => ({
				session: null,
				user: null
			})
		} as Parameters<typeof load>[0])) as LoadResult;

		expect(fetchMock).not.toHaveBeenCalled();
		expect(result).toEqual({});
	});

	it('returns immediately without API fetch when authenticated', async () => {
		const fetchMock = vi.fn(async () => new Response('{}'));

		const result = (await load({
			fetch: fetchMock as unknown as typeof fetch,
			parent: async () => ({
				session: { access_token: 'token' },
				user: { id: 'user-id' }
			})
		} as Parameters<typeof load>[0])) as LoadResult;

		expect(fetchMock).not.toHaveBeenCalled();
		expect(result).toEqual({});
	});
});
