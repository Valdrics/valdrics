import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import ROAChart from './ROAChart.svelte';

describe('ROAChart', () => {
	it('renders the projection as SVG and updates the highlighted point on hover', async () => {
		const { container, getByRole } = render(ROAChart);

		expect(getByRole('img', { name: /12-month return on automation projection/i })).toBeTruthy();
		expect(container.querySelectorAll('.point-core')).toHaveLength(12);
		expect(container.querySelector('.chart-summary strong')?.textContent).toBe('Dec');

		const points = container.querySelectorAll('.point-core');
		await fireEvent.pointerEnter(points[0]);

		const summaryValues = container.querySelectorAll('.chart-summary strong');
		expect(summaryValues[0]?.textContent).toBe('Jan');
		expect(summaryValues[1]?.textContent).toBe('$1,200');
	});
});
