import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import Page from './+page.svelte';

const { getTurnstileTokenMock } = vi.hoisted(() => ({
	getTurnstileTokenMock: vi.fn().mockResolvedValue(null)
}));

vi.mock('$app/environment', () => ({
	browser: true
}));

vi.mock('$app/paths', () => ({
	base: '',
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/talk-to-sales?utm_source=linkedin') })
}));

vi.mock('$lib/security/turnstile', () => ({
	getTurnstileToken: (...args: unknown[]) => getTurnstileTokenMock(...args)
}));

function jsonResponse(payload: unknown, status = 202): Response {
	return new Response(JSON.stringify(payload), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
}

describe('talk-to-sales page', () => {
	beforeEach(() => {
		cleanup();
		getTurnstileTokenMock.mockReset();
		getTurnstileTokenMock.mockResolvedValue(null);
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue(jsonResponse({ ok: true, accepted: true, inquiryId: 'inq-1' }))
		);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	it('renders the real sales inquiry form and key fallback actions', () => {
		render(Page);

		expect(screen.getByRole('heading', { level: 1, name: /talk to sales/i })).toBeTruthy();
		expect(screen.getByRole('link', { name: /start sales inquiry/i }).getAttribute('href')).toBe(
			'#sales-inquiry-form'
		);
		expect(screen.getByLabelText(/name/i)).toBeTruthy();
		expect(screen.getByLabelText(/work email/i)).toBeTruthy();
		expect(screen.getByLabelText(/company/i)).toBeTruthy();
		expect(screen.getByRole('button', { name: /send inquiry/i })).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /email instead/i }).getAttribute('href') || ''
		).toContain('mailto:enterprise@valdrics.com');
	});

	it('submits inquiries and shows inline success state', async () => {
		const fetchMock = vi
			.fn()
			.mockResolvedValue(jsonResponse({ ok: true, accepted: true, inquiryId: 'inq-42' }));
		vi.stubGlobal('fetch', fetchMock);
		getTurnstileTokenMock.mockResolvedValue('turnstile-token');

		render(Page);

		await fireEvent.input(screen.getByLabelText(/name/i), {
			target: { value: 'Buyer One' }
		});
		await fireEvent.input(screen.getByLabelText(/work email/i), {
			target: { value: 'buyer@example.com' }
		});
		await fireEvent.input(screen.getByLabelText(/company/i), {
			target: { value: 'Example Inc' }
		});
		await fireEvent.submit(document.getElementById('sales-inquiry-form') as HTMLFormElement);

		await waitFor(() => {
			expect(fetchMock).toHaveBeenCalledOnce();
		});

		const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(getTurnstileTokenMock).toHaveBeenCalledWith('public_sales_intake');
		expect(init.headers).toMatchObject({
			'content-type': 'application/json',
			'x-turnstile-token': 'turnstile-token'
		});
		await waitFor(() => {
			expect(screen.getByRole('status').textContent).toMatch(/inquiry received/i);
		});
		expect(screen.getByText(/reference: inq-42/i)).toBeTruthy();
	});

	it('shows inline error state when the inquiry service fails', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue(jsonResponse({ ok: false, error: 'delivery_failed' }, 503))
		);
		render(Page);

		await fireEvent.input(screen.getByLabelText(/name/i), {
			target: { value: 'Buyer One' }
		});
		await fireEvent.input(screen.getByLabelText(/work email/i), {
			target: { value: 'buyer@example.com' }
		});
		await fireEvent.input(screen.getByLabelText(/company/i), {
			target: { value: 'Example Inc' }
		});
		await fireEvent.submit(document.getElementById('sales-inquiry-form') as HTMLFormElement);

		await waitFor(() => {
			expect(screen.getByRole('alert').textContent).toMatch(/could not route the inquiry/i);
		});
	});
});
