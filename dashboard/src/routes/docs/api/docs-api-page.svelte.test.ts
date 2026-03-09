import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/docs/api') })
}));

describe('docs api page', () => {
	it('renders edge proxy guidance and endpoint groups', () => {
		render(Page);

		const heading = screen.getByRole('heading', { level: 1, name: /api reference/i });
		expect(heading).toBeTruthy();

		expect(screen.getAllByText(/\/api\/edge/i).length).toBeGreaterThan(0);
		expect(screen.getByText(/cost & carbon/i)).toBeTruthy();

		const statusLink = screen.getByRole('link', { name: /system status/i });
		expect(statusLink.getAttribute('href')).toBe('/status');
	});
});
