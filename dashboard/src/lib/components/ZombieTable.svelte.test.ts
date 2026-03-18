import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ZombieTable from './ZombieTable.svelte';

describe('ZombieTable', () => {
	it('disables review when persisted finding binding is missing', () => {
		render(ZombieTable, {
			zombies: {
				idle_instances: [
					{
						resource_id: 'i-zombie-1',
						resource_type: 'EC2 Instance',
						provider: 'aws',
						monthly_cost: '$18.00'
					}
				]
			},
			zombieCount: 1,
			onRemediate: vi.fn()
		});

		const button = screen.getByRole('button', { name: 'Unavailable' });
		expect(button.hasAttribute('disabled')).toBe(true);
		expect(button.getAttribute('title')).toContain('Persisted finding binding missing');
	});
});
