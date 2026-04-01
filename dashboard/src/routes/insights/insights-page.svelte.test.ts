import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';
import { listPublicContent } from '$lib/content/publicContent';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/insights') })
}));

const SHARED_PAGE_DATA = {
	user: null,
	session: null,
	subscription: { tier: 'starter', status: 'active' },
	profile: null
} as const;

describe('insights page', () => {
	it('renders insight cards and content CTAs', () => {
		render(Page, {
			data: {
				...SHARED_PAGE_DATA,
				insights: listPublicContent('insights')
			}
		});

		expect(screen.getByRole('heading', { level: 1, name: /insights/i })).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /start free workspace/i }).getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(
			screen.getByRole('link', { name: /enterprise review/i }).getAttribute('href') || ''
		).toContain('/enterprise?');
		expect(
			screen.getByRole('heading', {
				name: /why detection without ownership fails/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('heading', {
				name: /how to run a weekly waste review/i
			})
		).toBeTruthy();
		expect(
			screen.getByRole('heading', {
				name: /from alert to approved action/i
			})
		).toBeTruthy();

		expect(screen.getAllByRole('link', { name: /open insight/i })[0]?.getAttribute('href')).toBe(
			'/insights/why-detection-without-ownership-fails'
		);
		expect(screen.getAllByRole('link', { name: /open insight/i })[2]?.getAttribute('href')).toBe(
			'/insights/from-alert-to-approved-action'
		);
		expect(screen.getByRole('link', { name: /open resources/i }).getAttribute('href')).toBe(
			'/resources'
		);
	});
});
