import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import type { Snippet } from 'svelte';
import Layout from './+layout.svelte';

type PageState = { url: URL };

function createPageStore(initial: PageState) {
	let value = initial;
	const subscribers = new Set<(next: PageState) => void>();
	return {
		subscribe(run: (next: PageState) => void) {
			run(value);
			subscribers.add(run);
			return () => subscribers.delete(run);
		},
		set(next: PageState) {
			value = next;
			for (const subscriber of subscribers) {
				subscriber(next);
			}
		}
	};
}

const mocks = vi.hoisted(() => {
	const pageStore = createPageStore({ url: new URL('https://example.com/') });
	const authSubscription = { unsubscribe: vi.fn() };
	const onAuthStateChange = vi.fn((_callback: (event: string) => void) => ({
		data: {
			subscription: authSubscription
		}
	}));
	return {
		pageStore,
		uiState: {
			toasts: [],
			isSidebarOpen: true,
			isCommandPaletteOpen: false,
			toggleSidebar: vi.fn()
		},
		jobStore: {
			activeJobsCount: 0,
			init: vi.fn().mockResolvedValue(undefined),
			disconnect: vi.fn()
		},
		invalidate: vi.fn(),
		authSubscription,
		onAuthStateChange
	};
});

vi.mock('$app/stores', () => ({
	page: mocks.pageStore
}));

vi.mock('$app/paths', () => ({
	base: ''
}));

vi.mock('$app/navigation', () => ({
	invalidate: mocks.invalidate
}));

vi.mock('$app/environment', () => ({
	browser: true
}));

vi.mock('$lib/supabase.browser', () => ({
	createSupabaseBrowserClient: () => ({
		auth: {
			onAuthStateChange: mocks.onAuthStateChange
		}
	})
}));

vi.mock('$lib/stores/ui.svelte', () => ({
	uiState: mocks.uiState
}));

vi.mock('$lib/stores/jobs.svelte', () => ({
	jobStore: mocks.jobStore
}));

describe('public layout mobile menu', () => {
	const emptySnippet = (() => '') as unknown as Snippet;

	afterEach(() => {
		cleanup();
	});

	beforeEach(() => {
		mocks.pageStore.set({ url: new URL('https://example.com/') });
		mocks.jobStore.init.mockClear();
		mocks.jobStore.disconnect.mockClear();
		mocks.invalidate.mockClear();
		mocks.onAuthStateChange.mockClear();
		mocks.authSubscription.unsubscribe.mockClear();
		Object.defineProperty(window, 'matchMedia', {
			configurable: true,
			value: vi.fn().mockReturnValue({
				matches: false,
				addEventListener: vi.fn(),
				removeEventListener: vi.fn()
			})
		});
		window.localStorage.clear();
	});

	function getMenuToggle(): HTMLButtonElement {
		return screen.getAllByRole('button', { name: /toggle menu/i })[0] as HTMLButtonElement;
	}

	async function renderPublicLayout() {
		mocks.pageStore.set({ url: new URL('https://example.com/') });
		const result = render(Layout, {
			data: {
				user: null,
				session: null,
				profile: null,
				subscription: { tier: 'free', status: 'active' }
			},
			children: emptySnippet
		});
		await screen.findAllByRole('link', { name: /^start free$/i });
		return result;
	}

	async function renderAuthenticatedLayout() {
		mocks.pageStore.set({ url: new URL('https://example.com/dashboard') });
		const result = render(Layout, {
			data: {
				user: {
					id: 'user-1',
					email: 'engineer@example.com',
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
						email: 'engineer@example.com',
						app_metadata: {},
						user_metadata: {},
						aud: 'authenticated',
						created_at: '2026-03-18T00:00:00.000Z'
					}
				},
				profile: { persona: 'engineering', role: 'member' },
				subscription: { tier: 'pro', status: 'active' }
			} as never,
			children: emptySnippet
		});
		await screen.findByRole('button', { name: /open command palette/i });
		return result;
	}

	it('opens, traps focus, and closes with escape/backdrop', async () => {
		await renderPublicLayout();

		const toggle = getMenuToggle();
		await fireEvent.click(toggle);

		const dialog = await screen.findByRole('dialog', { name: /public navigation menu/i });
		expect(dialog).toBeTruthy();
		expect(document.body.style.overflow).toBe('hidden');

		await waitFor(() => {
			const active = document.activeElement as HTMLElement | null;
			expect(active?.textContent?.trim()).toMatch(/dark mode|light mode|enterprise review/i);
		});

		await fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
		await waitFor(() => {
			const active = document.activeElement as HTMLElement | null;
			expect(active?.textContent?.trim()).toMatch(/enterprise|resources/i);
		});

		await fireEvent.keyDown(window, { key: 'Tab' });
		await waitFor(() => {
			const active = document.activeElement as HTMLElement | null;
			expect(active?.textContent?.trim()).toMatch(/dark mode|light mode|enterprise review/i);
		});

		await fireEvent.keyDown(window, { key: 'Escape' });
		await waitFor(() => {
			expect(screen.queryByRole('dialog', { name: /public navigation menu/i })).toBeNull();
		});
		expect(document.body.style.overflow).toBe('');

		await fireEvent.click(toggle);
		await screen.findByRole('dialog', { name: /public navigation menu/i });
		const backdropClose = screen.getByRole('button', { name: /close navigation menu/i });
		await fireEvent.click(backdropClose);
		await waitFor(() => {
			expect(screen.queryByRole('dialog', { name: /public navigation menu/i })).toBeNull();
		});
	});

	it('closes when route changes', async () => {
		await renderPublicLayout();

		await fireEvent.click(getMenuToggle());
		await screen.findByRole('dialog', { name: /public navigation menu/i });

		mocks.pageStore.set({ url: new URL('https://example.com/pricing') });
		await waitFor(() => {
			expect(screen.queryByRole('dialog', { name: /public navigation menu/i })).toBeNull();
		});
	});

	it('keeps desktop conversion actions in the public header', async () => {
		await renderPublicLayout();

		expect(screen.getAllByRole('link', { name: /^enterprise review$/i }).length).toBeGreaterThan(0);
		expect(screen.getAllByRole('link', { name: /^start free$/i }).length).toBeGreaterThan(0);
	});

	it('persists the public theme toggle state', async () => {
		const { container } = await renderPublicLayout();
		const shell = container.querySelector('.public-site-shell');
		expect(shell?.getAttribute('data-public-theme')).toBe('light');

		const toggle = screen.getAllByRole('button', { name: /switch to dark mode/i })[0];
		await fireEvent.click(toggle);

		await waitFor(() => {
			expect(shell?.getAttribute('data-public-theme')).toBe('dark');
		});
		expect(window.localStorage.getItem('valdrics.public.theme.v1')).toBe('dark');
		expect(screen.getAllByRole('button', { name: /switch to light mode/i }).length).toBeGreaterThan(
			0
		);
	});

	it('uses landing tone on the home page and default tone on other public routes', async () => {
		const { container, unmount } = await renderPublicLayout();
		const homeShell = container.querySelector('.public-site-shell');
		expect(homeShell?.getAttribute('data-public-tone')).toBe('landing');

		unmount();
		mocks.pageStore.set({ url: new URL('https://example.com/pricing') });
		const pricingRender = render(Layout, {
			data: {
				user: null,
				session: null,
				profile: null,
				subscription: { tier: 'free', status: 'active' }
			},
			children: emptySnippet
		});
		await screen.findAllByRole('link', { name: /^start free$/i });
		const pricingShell = pricingRender.container.querySelector('.public-site-shell');
		expect(pricingShell?.getAttribute('data-public-tone')).toBe('default');
	});

	it('surfaces concise conversion-safe contact channels in footer', async () => {
		await renderPublicLayout();

		expect(screen.getAllByRole('link', { name: /sales@valdrics\.com/i }).length).toBeGreaterThan(0);
		expect(screen.getAllByRole('link', { name: /support@valdrics\.com/i }).length).toBeGreaterThan(
			0
		);
		expect(screen.getAllByRole('link', { name: /security@valdrics\.com/i }).length).toBeGreaterThan(
			0
		);
		expect(screen.queryByRole('link', { name: /enterprise@valdrics\.com/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /billing@valdrics\.com/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /hello@valdrics\.com/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /abuse@valdrics\.com/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /privacy@valdrics\.com/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /postmaster@valdrics\.com/i })).toBeNull();
	});

	it('opens desktop resources dropdown and closes with escape or outside click', async () => {
		await renderPublicLayout();

		const resourcesTrigger = screen.getAllByRole('button', { name: /^resources$/i })[0];
		expect(resourcesTrigger).toBeTruthy();
		if (!resourcesTrigger) {
			return;
		}
		await fireEvent.click(resourcesTrigger);
		expect(await screen.findByRole('menu', { name: /^resources$/i })).toBeTruthy();
		expect(screen.getByRole('menuitem', { name: /resource hub/i })).toBeTruthy();
		expect(screen.getByRole('menuitem', { name: /docs/i })).toBeTruthy();
		expect(screen.getByRole('menuitem', { name: /proof pack/i })).toBeTruthy();
		expect(screen.getByRole('menuitem', { name: /insights/i })).toBeTruthy();

		await fireEvent.keyDown(window, { key: 'Escape' });
		await waitFor(() => {
			expect(screen.queryByRole('menu', { name: /^resources$/i })).toBeNull();
		});

		await fireEvent.click(resourcesTrigger);
		expect(await screen.findByRole('menu', { name: /^resources$/i })).toBeTruthy();
		await fireEvent.pointerDown(document.body);
		await waitFor(() => {
			expect(screen.queryByRole('menu', { name: /^resources$/i })).toBeNull();
		});
	});

	it('loads auth listeners and job streaming only for authenticated layouts', async () => {
		await renderAuthenticatedLayout();

		await waitFor(() => {
			expect(mocks.onAuthStateChange).toHaveBeenCalledTimes(1);
			expect(mocks.jobStore.init).toHaveBeenCalledTimes(1);
		});

		const authCallback = mocks.onAuthStateChange.mock.calls[0]?.[0] as
			| ((event: string) => void)
			| undefined;
		expect(authCallback).toBeTypeOf('function');
		authCallback?.('SIGNED_IN');

		await waitFor(() => {
			expect(mocks.invalidate).toHaveBeenCalledWith('supabase:auth');
		});
	});

	it('closes when user scrolls after opening the menu', async () => {
		await renderPublicLayout();

		await fireEvent.click(getMenuToggle());
		await screen.findByRole('dialog', { name: /public navigation menu/i });

		Object.defineProperty(window, 'scrollY', {
			value: 96,
			writable: true,
			configurable: true
		});
		await fireEvent.scroll(window);

		await waitFor(() => {
			expect(screen.queryByRole('dialog', { name: /public navigation menu/i })).toBeNull();
		});
	});
});
