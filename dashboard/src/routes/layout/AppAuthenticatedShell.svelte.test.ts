import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import type { Snippet } from 'svelte';
import AppAuthenticatedShell from './AppAuthenticatedShell.svelte';
import { uiState } from '$lib/stores/ui.svelte';

const mocks = vi.hoisted(() => ({
	invalidate: vi.fn(),
	onAuthStateChange: vi.fn((_callback: (event: string) => void) => ({
		data: {
			subscription: {
				unsubscribe: vi.fn()
			}
		}
	})),
	jobStore: {
		activeJobsCount: 0,
		init: vi.fn().mockResolvedValue(undefined),
		disconnect: vi.fn()
	}
}));

vi.mock('$app/environment', () => ({
	browser: true
}));

vi.mock('$app/navigation', () => ({
	invalidate: mocks.invalidate
}));

vi.mock('$lib/supabase.browser', () => ({
	createSupabaseBrowserClient: () => ({
		auth: {
			onAuthStateChange: mocks.onAuthStateChange
		}
	})
}));

vi.mock('$lib/stores/jobs.svelte', () => ({
	jobStore: mocks.jobStore
}));

const emptySnippet = (() => '') as unknown as Snippet;

describe('AppAuthenticatedShell', () => {
	beforeEach(() => {
		Object.defineProperty(window, 'matchMedia', {
			configurable: true,
			value: vi.fn().mockReturnValue({
				matches: false,
				addEventListener: vi.fn(),
				removeEventListener: vi.fn()
			})
		});
		window.localStorage.clear();
		mocks.invalidate.mockClear();
		mocks.onAuthStateChange.mockClear();
		mocks.jobStore.init.mockClear();
		mocks.jobStore.disconnect.mockClear();
	});

	afterEach(() => {
		cleanup();
		uiState.isCommandPaletteOpen = false;
		uiState.isSidebarOpen = true;
		uiState.toasts = [];
	});

	it('lazy-loads and opens the command palette on demand', async () => {
		render(AppAuthenticatedShell, {
			props: {
				user: { email: 'operator@example.com' },
				role: 'owner',
				platformOperator: false,
				subscription: { tier: 'growth' },
				primaryNavItems: [{ href: '/dashboard', label: 'Dashboard', icon: '📊' }],
				secondaryNavItems: [{ href: '/llm', label: 'LLM Usage', icon: '🤖' }],
				activeSecondaryNavItems: [],
				persona: 'finops',
				toAppPath: (path: string) => path,
				isActive: (href: string) => href === '/dashboard',
				children: emptySnippet
			}
		});

		await fireEvent.click(screen.getByRole('button', { name: /open command palette/i }));

		expect(
			await screen.findByRole('dialog', {
				name: /command palette/i
			})
		).toBeTruthy();
		expect(screen.getByPlaceholderText(/search actions, routes, or documentation/i)).toBeTruthy();
	});
});
