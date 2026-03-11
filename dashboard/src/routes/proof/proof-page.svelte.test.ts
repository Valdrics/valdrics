import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/proof') })
}));

describe('proof page', () => {
	it('renders structured proof sections and navigation links', () => {
		render(Page);

		expect(
			screen.getByRole('heading', { level: 1, name: /executive and technical proof/i })
		).toBeTruthy();
		expect(
			screen.getAllByRole('link', { name: /open enterprise path/i })[0]?.getAttribute('href') || ''
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
