import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';

const getMock = vi.fn();

vi.mock('$env/static/public', () => ({
	PUBLIC_API_URL: 'https://api.test/api/v1'
}));

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://api.test/api/v1'
	}
}));

vi.mock('$lib/api', () => ({
	api: {
		get: (...args: unknown[]) => getMock(...args)
	}
}));

import Page from './+page.svelte';

describe('audit page access gating', () => {
	afterEach(() => {
		getMock.mockReset();
		cleanup();
	});

	it('shows an upgrade notice and skips network calls for growth workspaces', async () => {
		render(Page, {
			data: {
				user: {
					id: 'user-1',
					email: 'admin@example.com',
					app_metadata: {},
					user_metadata: {},
					aud: 'authenticated',
					created_at: '2026-03-18T00:00:00.000Z'
				},
				session: {
					access_token: 'token',
					refresh_token: 'refresh-token',
					expires_in: 3600,
					expires_at: 9999999999,
					token_type: 'bearer',
					user: {
						id: 'user-1',
						email: 'admin@example.com',
						app_metadata: {},
						user_metadata: {},
						aud: 'authenticated',
						created_at: '2026-03-18T00:00:00.000Z'
					}
				},
				subscription: { tier: 'growth', status: 'active' },
				profile: { role: 'admin', persona: 'engineering', platform_operator: false }
			}
		});

		await screen.findByText(/pro tier required/i);
		await screen.findByText(/audit logs require an admin role on a pro or enterprise workspace/i);
		await waitFor(() => {
			expect(getMock).not.toHaveBeenCalled();
		});
	});
});
