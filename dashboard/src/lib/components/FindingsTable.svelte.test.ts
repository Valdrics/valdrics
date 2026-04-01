import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
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

afterEach(() => {
	cleanup();
});

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

	it('disables remediation when persisted finding binding is missing', () => {
		render(FindingsTable, {
			resources: [
				{
					provider: 'aws',
					resource_id: 'i-1234567890',
					resource_type: 'instance',
					monthly_cost: '$25',
					confidence: 'medium',
					risk_if_deleted: 'low',
					explanation: 'Idle for 14 days'
				}
			],
			onRemediate: vi.fn()
		});

		const button = screen.getByRole('button', { name: 'Unavailable' });
		expect(button.hasAttribute('disabled')).toBe(true);
		expect(button.getAttribute('title')).toContain('Persisted finding binding missing');
	});

	it('loads the sanitized detail body when a row is expanded', async () => {
		render(FindingsTable, {
			resources: [
				{
					provider: 'aws',
					resource_id: 'i-details',
					resource_type: 'instance',
					monthly_cost: '$25',
					confidence: 'medium',
					risk_if_deleted: 'low',
					explanation: '<strong>Idle for 14 days</strong>',
					confidence_reason: 'No network traffic recorded.'
				}
			],
			onRemediate: vi.fn()
		});

		await fireEvent.click(screen.getByText('View details'));

		expect(await screen.findByText('Idle for 14 days')).toBeTruthy();
		expect(screen.getByText('No network traffic recorded.')).toBeTruthy();
	});
});
