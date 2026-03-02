import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

describe('blog redirect route', () => {
	it('redirects blog visitors to insights without losing query params', () => {
		try {
			load({
				url: new URL('https://example.com/blog?topic=finops')
			} as Parameters<typeof load>[0]);
			throw new Error('expected redirect to be thrown');
		} catch (error) {
			expect(error).toMatchObject({
				status: 308,
				location: '/insights?topic=finops'
			});
		}
	});
});
