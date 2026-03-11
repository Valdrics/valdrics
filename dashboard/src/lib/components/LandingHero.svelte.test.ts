import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import LandingHero from './LandingHero.svelte';

vi.mock('$env/dynamic/public', () => ({
	env: {
		PUBLIC_API_URL: 'https://example.com/api/v1'
	}
}));

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({
		url: new URL('https://example.com/')
	})
}));

describe('LandingHero', () => {
	it('renders simplified hero plus progressive detail sections with telemetry and map a11y', async () => {
		const dataLayer: unknown[] = [];
		(window as Window & { dataLayer?: unknown[] }).dataLayer = dataLayer;
		const dispatchSpy = vi.spyOn(window, 'dispatchEvent');
		window.localStorage.setItem('valdrics.cookie_consent.v1', 'accepted');

		render(LandingHero);
		const landingRoot = document.querySelector('.landing');
		expect(landingRoot?.className).toContain('landing-motion-subtle');

		const mainHeading = screen.getByRole('heading', { level: 1 });
		expect(mainHeading).toBeTruthy();
		expect(mainHeading.textContent?.length).toBeGreaterThan(12);

		const primaryCandidates = screen.getAllByRole('link', {
			name: /Start Free Workspace|Book Executive Briefing/i
		});
		const primaryCta = primaryCandidates.find((element) =>
			(element.getAttribute('class') || '').includes('pulse-glow')
		);
		expect(primaryCta).toBeTruthy();
		expect(primaryCta?.getAttribute('href')).toContain('/auth/login?');
		expect(primaryCta?.getAttribute('href')).toContain('intent=engineering_control');
		if (primaryCta) {
			await fireEvent.click(primaryCta);
		}

		const heroSection = document.querySelector('#hero');
		expect(heroSection).toBeTruthy();
		const heroView = within(heroSection as HTMLElement);
		expect(heroView.getByText(/governed action for cloud, saas, and software spend/i)).toBeTruthy();
		expect(
			heroView.getByText(/detect waste\. route the owner\. approve the action\. keep the proof\./i)
		).toBeTruthy();
		expect(
			heroView.getByText(/turns cost, usage, and policy signals into owner-routed approvals/i)
		).toBeTruthy();
		const secondaryCta = heroView.getByRole('link', { name: /see enterprise path/i });
		expect(secondaryCta).toBeTruthy();
		const secondaryHref = secondaryCta?.getAttribute('href') || '';
		expect(secondaryHref).toContain('/enterprise?');
		expect(secondaryHref).toContain('source=hero_secondary');
		if (secondaryCta) {
			await fireEvent.click(secondaryCta);
		}
		expect(heroView.getByText(/cloud \+ saas \+ software in one control layer/i)).toBeTruthy();
		expect(heroView.getByText(/read-only onboarding where supported/i)).toBeTruthy();
		expect(heroView.getByText(/approval trail and exportable proof/i)).toBeTruthy();
		expect(heroView.queryByText(/verify before you commit/i)).toBeNull();
		expect(heroView.queryByText(/modeled first-quarter range:/i)).toBeNull();
		expect(heroView.queryByRole('link', { name: /technical validation/i })).toBeNull();
		expect(heroView.queryByRole('link', { name: /access checklist/i })).toBeNull();
		expect(heroView.queryByRole('link', { name: /review methodology/i })).toBeNull();
		expect(heroView.queryByRole('link', { name: /live signal map/i })).toBeNull();
		expect(heroView.queryByText(/evidence snapshot · february 28, 2026/i)).toBeNull();
		expect(heroView.queryByRole('link', { name: /view technical validation brief/i })).toBeNull();

		expect(
			screen.getByRole('heading', { name: /the operating layer after detection/i })
		).toBeTruthy();
		expect(screen.getByText(/connected inputs/i)).toBeTruthy();
		expect(screen.getAllByText(/^AWS$/i).length).toBeGreaterThanOrEqual(1);
		expect(screen.getAllByText(/^Microsoft 365$/i).length).toBeGreaterThanOrEqual(1);
		expect(document.querySelector('.landing-hook-metrics')?.getAttribute('tabindex')).toBe('0');
		expect(document.querySelector('.landing-coverage-summary')?.getAttribute('tabindex')).toBe('0');
		expect(document.querySelector('.landing-decision-ledger')?.getAttribute('tabindex')).toBe('0');
		expect(screen.getByText(/decision ledger/i)).toBeTruthy();
		expect(
			screen.getByText(/the issue lands with owner, scope, and financial context/i)
		).toBeTruthy();
		expect(screen.getByText(/policy, budget, and approval checks stay attached/i)).toBeTruthy();
		expect(screen.queryByText(/three core wins/i)).toBeNull();
		expect(screen.queryByText(/what changes after rollout/i)).toBeNull();
		expect(screen.getByRole('heading', { name: /see what happens after detection/i })).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /realtime spend scenario simulator/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /choose the plan that fits your control depth/i })
		).toBeTruthy();
		expect(
			screen.getByRole('heading', { name: /security proof and enterprise rollout/i })
		).toBeTruthy();

		expect(
			screen.queryByRole('heading', { name: /what each team gets in the first 30 days/i })
		).toBeNull();
		expect(screen.queryByRole('heading', { name: /not ready to sign up today\?/i })).toBeNull();
		expect(screen.queryByRole('button', { name: /switch to plain english/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /run the spend scenario simulator/i })).toBeNull();

		const summary = screen.getByText(/approval chain summary for snapshot a/i);
		const signalMap = summary.closest('.signal-map');
		expect(signalMap).toBeTruthy();
		const signalGraphic = signalMap?.querySelector('.approval-chain-shell');
		expect(signalGraphic).toBeTruthy();
		expect(signalGraphic?.getAttribute('aria-describedby')).toBe('signal-map-summary');
		expect(summary.getAttribute('id')).toBe('signal-map-summary');

		await fireEvent.click(screen.getByRole('button', { name: /^open approval chain$/i }));
		const snapshotButtons = screen.getAllByRole('button', { name: /snapshot [abc]/i });
		expect(snapshotButtons).toHaveLength(3);
		expect(snapshotButtons[0]?.getAttribute('aria-pressed')).toBe('true');
		await fireEvent.click(snapshotButtons[1] as HTMLButtonElement);
		expect(snapshotButtons[1]?.getAttribute('aria-pressed')).toBe('true');

		const laneTabs = screen.getAllByRole('tab');
		expect(laneTabs.length).toBeGreaterThanOrEqual(4);
		const signalScopedTab = screen.getByRole('tab', { name: /Signal Scoped/i });
		await fireEvent.click(signalScopedTab);
		expect(screen.getByText(/Current metric:/i)).toBeTruthy();

		expect(screen.getByLabelText(/reactive waste rate/i)).toBeTruthy();
		expect(screen.getByLabelText(/managed waste rate/i)).toBeTruthy();
		expect(screen.getByLabelText(/decision window \(months\)/i)).toBeTruthy();
		expect(screen.getByText(/Scenario Delta/i)).toBeTruthy();
		expect(screen.getByText(/Potential monthly recovery/i)).toBeTruthy();
		expect(screen.getByText(/12-month recovery/i)).toBeTruthy();
		expect(screen.getByRole('link', { name: /open assumptions csv/i }).getAttribute('href')).toBe(
			'/resources/valdrics-roi-assumptions.csv'
		);
		expect(screen.getByRole('link', { name: /Open Full ROI Planner/i })).toBeTruthy();

		const freePlanCta = document.querySelector(
			'.landing-free-tier-primary-cta'
		) as HTMLAnchorElement | null;
		expect(freePlanCta).toBeTruthy();
		if (!freePlanCta) {
			throw new Error('expected free tier CTA');
		}
		expect(freePlanCta.getAttribute('href') || '').toContain('plan=free');
		await fireEvent.click(freePlanCta);
		expect(screen.getByText(/monthly starting prices shown here are entry points/i)).toBeTruthy();
		expect(screen.getByText(/self-serve proof lane/i)).toBeTruthy();
		expect(
			screen.getByText(/permanent free workspace for one owner-routed savings workflow/i)
		).toBeTruthy();
		expect(
			screen.getByText(
				/free is best for proving one controlled workflow with no procurement overhead/i
			)
		).toBeTruthy();
		expect(
			screen.getByText(
				/\$49\/mo starting price\. priced for the first team that needs daily review cadence, initial cross-cloud visibility, and stronger owner routing/i
			)
		).toBeTruthy();
		expect(
			screen.getByText(
				/\$149\/mo starting price\. priced for the first cross-functional team that needs full multi-cloud coverage, owner routing, slack, jira, and sso to land together/i
			)
		).toBeTruthy();
		expect(
			screen.getByText(
				/\$299\/mo starting price\. priced for finance-grade self-serve rollout once auditability, api access, reconciliation, workflow automation, and export-ready evidence become operational requirements/i
			)
		).toBeTruthy();
		expect(screen.getAllByText(/^Best for$/i).length).toBeGreaterThanOrEqual(4);
		expect(screen.getAllByText(/^Why teams upgrade$/i).length).toBeGreaterThanOrEqual(4);
		expect(
			screen.getByText(
				/cross-functional teams need full aws, azure, and gcp coverage with owner routing/i
			)
		).toBeTruthy();
		expect(
			screen.getByText(
				/move to the enterprise lane only when scim, private deployment, procurement review/i
			)
		).toBeTruthy();
		const growthPlanCard = screen.getByRole('heading', { name: /^growth$/i }).closest('article');
		expect(growthPlanCard?.className).toContain('is-featured');

		const trustSection = document.querySelector('#trust');
		expect(trustSection).toBeTruthy();
		const trustView = within(trustSection as HTMLElement);
		const enterprisePathLink = trustView.getByRole('link', {
			name: /^open enterprise path$/i
		});
		const enterpriseHref = enterprisePathLink.getAttribute('href') || '';
		expect(enterpriseHref).toContain('/enterprise?');
		expect(enterpriseHref).toContain('source=trust_enterprise');
		const validationBriefingLink = trustView.getByRole('link', {
			name: /^book validation briefing$/i
		});
		expect(validationBriefingLink.getAttribute('href') || '').toContain('/talk-to-sales?');
		expect(validationBriefingLink.getAttribute('href') || '').toContain('source=trust_validation');
		expect(validationBriefingLink.getAttribute('href') || '').toContain(
			'intent=request_validation_briefing'
		);
		const onePagerLink = screen.getByRole('link', {
			name: /download executive one-pager/i
		});
		expect(onePagerLink.getAttribute('href')).toBe('/resources/valdrics-enterprise-one-pager.md');
		expect(trustView.getByText(/formal evaluation lane/i)).toBeTruthy();
		expect(trustView.getByText(/control and access checklist/i)).toBeTruthy();
		expect(trustView.queryByText(/current proof reflects design-partner feedback/i)).toBeNull();

		expect(dispatchSpy).toHaveBeenCalled();
		expect(dataLayer.length).toBeGreaterThan(0);
		const payload = dataLayer[dataLayer.length - 1] as Record<string, unknown>;
		expect(payload.event).toBe('valdrics_landing_event');
		expect(payload.funnelStage).toBeTruthy();
		expect(payload.experiment).toBeTruthy();

		dispatchSpy.mockRestore();
		window.localStorage.removeItem('valdrics.cookie_consent.v1');
		delete (window as Window & { dataLayer?: unknown[] }).dataLayer;
	}, 15000);

	it('shows cookie consent controls before analytics is accepted', async () => {
		window.localStorage.removeItem('valdrics.cookie_consent.v1');
		render(LandingHero);

		expect(screen.getByRole('dialog', { name: /cookie preferences/i })).toBeTruthy();
		const declineButton = screen.getByRole('button', { name: /decline analytics/i });
		await fireEvent.click(declineButton);
		expect(window.localStorage.getItem('valdrics.cookie_consent.v1')).toBe('rejected');
	});

	it('disables auto-rotation when reduced motion is preferred', () => {
		vi.useFakeTimers();
		const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
		const originalMatchMedia = window.matchMedia;
		const matchMediaStub = vi.fn().mockReturnValue({
			matches: true,
			addEventListener: vi.fn(),
			removeEventListener: vi.fn()
		});
		Object.defineProperty(window, 'matchMedia', {
			writable: true,
			value: matchMediaStub
		});

		const { unmount } = render(LandingHero);
		const intervalDurationsMs = setIntervalSpy.mock.calls.map((call) => Number(call[1]));
		expect(intervalDurationsMs).not.toContain(4400);
		expect(intervalDurationsMs).not.toContain(3200);

		unmount();
		setIntervalSpy.mockRestore();
		Object.defineProperty(window, 'matchMedia', {
			writable: true,
			value: originalMatchMedia
		});
		vi.useRealTimers();
	});

	it('cleans rotating intervals on unmount for concurrency safety', () => {
		vi.useFakeTimers();
		const setIntervalSpy = vi.spyOn(globalThis, 'setInterval');
		const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');

		const { unmount } = render(LandingHero);
		expect(setIntervalSpy).toHaveBeenCalled();

		unmount();
		expect(clearIntervalSpy).toHaveBeenCalled();

		setIntervalSpy.mockRestore();
		clearIntervalSpy.mockRestore();
		vi.useRealTimers();
	});
});
