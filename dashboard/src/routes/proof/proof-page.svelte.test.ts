import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';
import { mustGetPublicContentEntry } from '$lib/content/publicContent';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/proof') })
}));

const SHARED_PAGE_DATA = {
	user: null,
	session: null,
	subscription: { tier: 'starter', status: 'active' },
	profile: null
} as const;

describe('proof page', () => {
	it('renders structured proof sections and navigation links', () => {
		render(Page, {
			data: {
				...SHARED_PAGE_DATA,
				proofSpotlights: [
					mustGetPublicContentEntry('proof', 'safe-access-model'),
					mustGetPublicContentEntry('proof', 'identity-and-approval-controls'),
					mustGetPublicContentEntry('proof', 'decision-history-and-export-integrity'),
					mustGetPublicContentEntry('proof', 'deployment-and-data-residency'),
					mustGetPublicContentEntry('proof', 'validation-scope-and-operational-hardening')
				]
			}
		});

		expect(
			screen.getByRole('heading', { level: 1, name: /proof surfaces for buyer diligence/i })
		).toBeTruthy();
		expect(
			screen.getAllByRole('link', { name: /enterprise review/i })[0]?.getAttribute('href') || ''
		).toContain('/enterprise?');
		expect(
			screen.getAllByRole('link', { name: /start free workspace/i })[0]?.getAttribute('href') || ''
		).toContain('/auth/login?');
		expect(screen.getByText(/safe access model/i)).toBeTruthy();
		expect(screen.getByText(/identity and approval controls/i)).toBeTruthy();
		expect(screen.getByText(/decision history and export integrity/i)).toBeTruthy();
		expect(screen.getByText(/validation scope and operational hardening/i)).toBeTruthy();

		expect(
			screen.getAllByRole('link', { name: /Open Technical Validation/i })[0]?.getAttribute('href')
		).toBe('/docs/technical-validation');
		expect(
			screen.getByRole('heading', { name: /use the proof pack in the same order buyers do/i })
		).toBeTruthy();
		expect(screen.getAllByRole('link', { name: /Documentation/i })[0]?.getAttribute('href')).toBe(
			'/docs'
		);
		expect(screen.getAllByRole('link', { name: /API Reference/i })[0]?.getAttribute('href')).toBe(
			'/docs/api'
		);
		expect(screen.getAllByRole('link', { name: /open proof page/i })[0]?.getAttribute('href')).toBe(
			'/proof/safe-access-model'
		);
	});
});
