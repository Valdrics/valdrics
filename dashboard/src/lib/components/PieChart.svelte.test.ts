import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import PieChart from './PieChart.svelte';

describe('PieChart', () => {
	const data = [
		{ label: 'AWS', value: 5000, color: '#f97316' },
		{ label: 'Azure', value: 3000, color: '#3b82f6' },
		{ label: 'GCP', value: 2000, color: '#facc15' }
	];

	it('renders an SVG donut chart and updates the active segment from the legend', async () => {
		const { container, getByRole } = render(PieChart, {
			props: { data, title: 'Spend mix' }
		});

		expect(getByRole('img', { name: /Spend mix chart/i })).toBeTruthy();
		expect(container.querySelectorAll('.chart-segment')).toHaveLength(3);
		expect(container.querySelector('.chart-center-copy span')?.textContent).toBe('AWS');
		expect(container.querySelector('.chart-center-copy strong')?.textContent).toBe('$5,000');

		const buttons = container.querySelectorAll('.chart-legend button');
		expect(buttons).toHaveLength(3);

		await fireEvent.click(buttons[1]);

		expect(container.querySelector('.chart-center-copy span')?.textContent).toBe('Azure');
		expect(container.querySelector('.chart-center-copy strong')?.textContent).toBe('$3,000');
	});

	it('renders an empty state when no chart data is available', () => {
		const { queryByRole, getByText } = render(PieChart, {
			props: { data: [], title: 'Empty chart' }
		});

		expect(queryByRole('img', { name: /Empty chart/i })).toBeNull();
		expect(getByText('No data available')).toBeTruthy();
	});
});
