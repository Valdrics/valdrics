import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import FindingsTable from './FindingsTable.svelte';

vi.mock('dompurify', () => ({
	default: {
		sanitize: (value: string) => value
	}
}));

vi.mock('$lib/logging/client', () => ({
	clientLogger: {
		error: vi.fn()
	}
}));

describe('FindingsTable', () => {
	it('shows growth-plan lock state when owner attribution is tier-gated', () => {
		render(FindingsTable, {
			resources: [
				{
					provider: 'aws',
					resource_id: 'i-1234567890',
					resource_type: 'instance',
					monthly_cost: '$25',
					confidence: 'medium',
					risk_if_deleted: 'low',
					explanation: 'Idle for 14 days',
					owner: 'Growth Plan Required'
				}
			],
			onRemediate: vi.fn()
		});

		expect(screen.getByText('LOCKED')).toBeTruthy();
		expect(screen.getByTitle('Owner Attribution requires Growth tier')).toBeTruthy();
	});
});
