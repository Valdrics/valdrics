import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';

import LandingLeadCaptureSection from '$lib/components/landing/LandingLeadCaptureSection.svelte';
import LandingExitIntentPrompt from '$lib/components/landing/LandingExitIntentPrompt.svelte';

describe('Landing decomposition lead capture and exit intent', () => {
	afterEach(() => {
		cleanup();
		vi.restoreAllMocks();
	});

	it('submits newsletter capture and routes CTA interactions', async () => {
		const onTrackCta = vi.fn();
		const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response(JSON.stringify({ ok: true, accepted: true }), {
				status: 202,
				headers: { 'content-type': 'application/json' }
			})
		);
		try {
			render(LandingLeadCaptureSection, {
				props: {
					subscribeApiPath: '/api/marketing/subscribe',
					startFreeHref: '/auth/login?intent=start_free',
					resourcesHref: '/resources',
					onTrackCta
				}
			});

			await fireEvent.input(screen.getByLabelText(/work email/i), {
				target: { value: 'buyer@example.com' }
			});
			const submitButton = screen.getByRole('button', { name: /send me weekly insights/i });
			const form = submitButton.closest('form');
			expect(form).toBeTruthy();
			if (!form) {
				return;
			}
			await fireEvent.submit(form);

			expect(fetchSpy).toHaveBeenCalledTimes(1);
			expect(onTrackCta).toHaveBeenCalledWith(
				'cta_click',
				'lead_capture',
				'newsletter_subscribe_success'
			);
			expect(screen.getByText(/subscribed\. check your inbox/i)).toBeTruthy();
		} finally {
			fetchSpy.mockRestore();
		}
	});

	it('opens exit intent prompt on desktop mouseout and supports dismissal', async () => {
		Object.defineProperty(window, 'matchMedia', {
			writable: true,
			value: vi.fn().mockReturnValue({ matches: false })
		});
		localStorage.clear();
		const onTrackCta = vi.fn();
		vi.spyOn(globalThis, 'fetch').mockResolvedValue(
			new Response(JSON.stringify({ ok: true, accepted: true }), {
				status: 202,
				headers: { 'content-type': 'application/json' }
			})
		);

		render(LandingExitIntentPrompt, {
			props: {
				selfServeHref: '/auth/login?intent=free_tier&plan=free',
				resourcesHref: '/resources',
				subscribeApiPath: '/api/marketing/subscribe',
				onTrackCta
			}
		});

		window.dispatchEvent(
			new MouseEvent('mouseout', {
				clientY: 0,
				relatedTarget: null
			})
		);

		expect(
			await screen.findByRole('heading', { name: /want a weekly spend-control brief instead/i })
		).toBeTruthy();
		const selfServeLink = screen.getByRole('link', { name: /start free workspace/i });
		expect(selfServeLink.getAttribute('href')).toContain('intent=free_tier');
		expect(onTrackCta).toHaveBeenCalledWith('cta_view', 'exit_prompt', 'desktop_exit_intent');

		await fireEvent.click(screen.getByRole('button', { name: /close prompt/i }));
		const dismissedUntil = Number(
			localStorage.getItem('valdrics.landing.exit_prompt.dismissed.v2')
		);
		expect(Number.isFinite(dismissedUntil)).toBe(true);
		expect(dismissedUntil).toBeGreaterThan(Date.now());
	});
});
