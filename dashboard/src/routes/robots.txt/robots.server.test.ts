import { describe, expect, it } from 'vitest';
import { GET } from './+server';

describe('robots.txt route', () => {
	it('disallows auth and build assets while advertising sitemap', async () => {
		const response = await GET({
			url: new URL('https://example.com/robots.txt')
		} as Parameters<typeof GET>[0]);

		expect(response.status).toBe(200);
		expect(response.headers.get('content-type')).toContain('text/plain');
		expect(response.headers.get('cache-control')).toBe('public, max-age=3600');

		const body = await response.text();
		expect(body).toContain('User-agent: *');
		expect(body).toContain('Disallow: /auth/');
		expect(body).toContain('Disallow: /_app/');
		expect(body).toContain('Sitemap: https://example.com/sitemap.xml');
	});

	it('preserves the deployed base path in the sitemap URL', async () => {
		const response = await GET({
			url: new URL('https://example.com/app/robots.txt')
		} as Parameters<typeof GET>[0]);

		const body = await response.text();
		expect(body).toContain('Sitemap: https://example.com/app/sitemap.xml');
	});
});
