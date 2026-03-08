import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Page from './+page.svelte';

vi.mock('$app/paths', () => ({
	base: ''
}));

describe('proof page', () => {
	it('renders structured proof sections and navigation links', () => {
		render(Page);

		expect(
			screen.getByRole('heading', { level: 1, name: /executive and technical proof/i })
		).toBeTruthy();
		expect(screen.getByText(/Economic Control Integrity/i)).toBeTruthy();
		expect(screen.getByText(/Deterministic Execution/i)).toBeTruthy();
		expect(screen.getByText(/Funnel and Attribution Telemetry/i)).toBeTruthy();
		expect(screen.getByText(/Operational Resilience and Accessibility/i)).toBeTruthy();

			expect(screen.getAllByRole('link', { name: /Documentation/i })[0]?.getAttribute('href')).toBe('/docs');
			expect(screen.getAllByRole('link', { name: /API Reference/i })[0]?.getAttribute('href')).toBe(
				'/docs/api'
			);
		expect(screen.getAllByRole('link', { name: /Back to Landing/i })[0]?.getAttribute('href')).toBe(
			'/'
		);
	});
});
