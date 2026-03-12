import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import LandingHeroCopy from '$lib/components/landing/LandingHeroCopy.svelte';
import LandingSignalMapCard from '$lib/components/landing/LandingSignalMapCard.svelte';
import LandingRoiSimulator from '$lib/components/landing/LandingRoiSimulator.svelte';
import LandingRoiCalculator from '$lib/components/landing/LandingRoiCalculator.svelte';
import LandingRoiPlannerCta from '$lib/components/landing/LandingRoiPlannerCta.svelte';
import LandingTrustSection from '$lib/components/landing/LandingTrustSection.svelte';
import { REALTIME_SIGNAL_SNAPSHOTS } from '$lib/landing/realtimeSignalMap';
import { calculateLandingRoi, normalizeLandingRoiInputs } from '$lib/landing/roiCalculator';
import './landing_decomposition.lead_exit.svelte.test';

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

describe('Landing component decomposition', () => {
	it('renders hero copy and keeps CTA tracking callbacks wired', async () => {
		const onPrimaryCta = vi.fn();
		const onSecondaryCta = vi.fn();

		render(LandingHeroCopy, {
			props: {
				heroTitle: 'Control every dollar in your cloud and software stack.',
				heroSubtitle: 'From signal to owner and approved action in one loop.',
				primaryCtaLabel: 'Start Free Workspace',
				secondaryCtaLabel: 'See Pricing',
				secondaryCtaHref: '/pricing?source=hero_secondary',
				primaryCtaHref: '/auth/login?intent=engineering_control',
				onPrimaryCta,
				onSecondaryCta
			}
		});

		expect(screen.getByRole('heading', { level: 1 })).toBeTruthy();
		await fireEvent.click(screen.getByRole('link', { name: /start free workspace/i }));
		await fireEvent.click(screen.getByRole('link', { name: /see pricing/i }));
		expect(onPrimaryCta).toHaveBeenCalledTimes(1);
		expect(onSecondaryCta).toHaveBeenCalledTimes(1);
		expect(screen.getByText(/cloud \+ saas \+ software in one control layer/i)).toBeTruthy();
		expect(screen.getByText(/read-only onboarding where supported/i)).toBeTruthy();
		expect(screen.queryByText(/verify before you commit/i)).toBeNull();
		expect(screen.queryByRole('link', { name: /technical validation/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /access checklist/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /review methodology/i })).toBeNull();
		expect(screen.queryByRole('link', { name: /live signal map/i })).toBeNull();
		expect(screen.queryByText(/evidence snapshot · february 28, 2026/i)).toBeNull();

		// Check for GreenOps Global Flip additions
		expect(screen.getByText(/Governed action for cloud, SaaS, and software spend/i)).toBeTruthy();
		expect(
			screen.getByText(/Detect waste\. Route the owner\. Approve the action\. Keep the proof\./i)
		).toBeTruthy();
	});

	it('renders signal map card and propagates interactions', async () => {
		const onSelectSignalLane = vi.fn();
		const onSelectDemoStep = vi.fn();
		const onSelectSnapshot = vi.fn();
		const onSignalMapElementChange = vi.fn();

		const snapshot = REALTIME_SIGNAL_SNAPSHOTS[0];
		const activeLane = snapshot?.lanes[0];
		expect(snapshot).toBeTruthy();
		expect(activeLane).toBeTruthy();
		if (!snapshot || !activeLane) {
			return;
		}

		render(LandingSignalMapCard, {
			props: {
				activeSnapshot: snapshot,
				activeSignalLane: activeLane,
				signalMapInView: true,
				snapshotIndex: 0,
				demoStepIndex: 0,
				onSelectSignalLane,
				onSelectDemoStep,
				onSelectSnapshot,
				onSignalMapElementChange
			}
		});

		expect(screen.getByText(/live decision loop/i)).toBeTruthy();
		await fireEvent.click(screen.getByRole('button', { name: /^open approval chain$/i }));
		const firstLaneTab = screen.getByRole('tab', { name: /signal scoped/i });
		await fireEvent.click(firstLaneTab);
		expect(onSelectSignalLane).toHaveBeenCalled();

		await fireEvent.click(screen.getByRole('button', { name: /open approval chain walkthrough/i }));
		const demoButton = screen.getByRole('button', { name: /^routed$/i });
		await fireEvent.click(demoButton);
		expect(onSelectDemoStep).toHaveBeenCalled();

		const snapshotButton = screen.getByRole('button', { name: /snapshot b/i });
		await fireEvent.click(snapshotButton);
		expect(onSelectSnapshot).toHaveBeenCalled();
		expect(onSignalMapElementChange).toHaveBeenCalled();
	});

	it('updates simulator controls through typed callbacks', async () => {
		const onTrackScenarioAdjust = vi.fn();
		const onScenarioWasteWithoutChange = vi.fn();
		const onScenarioWasteWithChange = vi.fn();
		const onScenarioWindowChange = vi.fn();
		const onTrackPlannerCta = vi.fn();

		const view = render(LandingRoiSimulator, {
			props: {
				normalizedScenarioWasteWithoutPct: 18,
				normalizedScenarioWasteWithPct: 7,
				normalizedScenarioWindowMonths: 12,
				scenarioWithoutBarPct: 100,
				scenarioWithBarPct: 40,
				scenarioWasteWithoutUsd: 21600,
				scenarioWasteWithUsd: 8400,
				scenarioWasteRecoveryMonthlyUsd: 13200,
				scenarioWasteRecoveryWindowUsd: 158400,
				monthlySpendUsd: 120000,
				scenarioWasteWithoutPct: 18,
				scenarioWasteWithPct: 7,
				scenarioWindowMonths: 12,
				formatUsd: (amount: number) => `$${amount}`,
				currencyCode: 'USD',
				plannerHref: '/auth/login?intent=roi_assessment',
				onTrackScenarioAdjust,
				onScenarioWasteWithoutChange,
				onScenarioWasteWithChange,
				onScenarioWindowChange,
				onTrackPlannerCta
			}
		});
		const simulatorView = within(view.container);

		await fireEvent.input(simulatorView.getByLabelText(/reactive waste rate/i), {
			target: { value: '19' }
		});
		await fireEvent.input(simulatorView.getByLabelText(/managed waste rate/i), {
			target: { value: '8' }
		});
		await fireEvent.input(simulatorView.getByLabelText(/decision window \(months\)/i), {
			target: { value: '11' }
		});

		expect(onScenarioWasteWithoutChange).toHaveBeenCalledWith(19);
		expect(onScenarioWasteWithChange).toHaveBeenCalledWith(8);
		expect(onScenarioWindowChange).toHaveBeenCalledWith(11);
		expect(onTrackScenarioAdjust).toHaveBeenCalledTimes(3);
		expect(
			simulatorView.getByRole('link', { name: /review methodology/i }).getAttribute('href')
		).toBe('/docs/technical-validation');
		expect(
			simulatorView.getByRole('link', { name: /open assumptions csv/i }).getAttribute('href')
		).toBe('/resources/valdrics-roi-assumptions.csv');
		await fireEvent.click(simulatorView.getByRole('link', { name: /open full roi planner/i }));
		expect(onTrackPlannerCta).toHaveBeenCalledTimes(1);
	});

	it('renders static ROI snapshot preview and tracks planner CTA', async () => {
		const onTrackCta = vi.fn();
		const view = render(LandingRoiPlannerCta, {
			props: {
				href: '/auth/login?intent=roi_assessment',
				onTrackCta
			}
		});

		const ctaView = within(view.container);
		expect(ctaView.getByText(/example 12-month model snapshot/i)).toBeTruthy();
		expect(ctaView.getByText(/projected annual spend/i)).toBeTruthy();
		expect(ctaView.getAllByText(/controllable waste opportunity/i).length).toBeGreaterThan(0);
		await fireEvent.click(ctaView.getByRole('link', { name: /open full roi planner/i }));
		expect(onTrackCta).toHaveBeenCalledTimes(1);
	});

	it('renders global trust compliance badges and regional resilience signals', async () => {
		const onTrackCta = vi.fn();
		const view = render(LandingTrustSection, {
			props: {
				aboutHref: '/about?source=trust_about',
				docsHref: '/docs?source=trust_docs',
				statusHref: '/status?source=trust_status',
				enterprisePathHref: '/enterprise?source=trust_enterprise',
				requestValidationBriefingHref:
					'/talk-to-sales?source=trust_validation&intent=request_validation_briefing',
				onePagerHref: '/resources/valdrics-enterprise-one-pager.md',
				globalComplianceWorkbookHref: '/resources/global-finops-compliance-workbook.md',
				onTrackCta
			}
		});

		expect(view.getAllByText(/Read-only cloud onboarding where supported/i).length).toBeGreaterThan(
			0
		);
		expect(view.getAllByText(/Decision history export/i).length).toBeGreaterThan(0);

		const ctaBlock = within(view.container).getByRole('generic', {
			name: 'Security proof and enterprise rollout'
		});
		expect(ctaBlock).toBeTruthy();
		if (ctaBlock) {
			const ctaView = within(ctaBlock);
			expect(ctaView.getByText(/Control and Access Checklist/i)).toBeTruthy();
			expect(ctaView.getByText(/formal evaluation lane/i)).toBeTruthy();
			await fireEvent.click(ctaView.getByRole('link', { name: /Control and Access Checklist/i }));
			expect(onTrackCta).toHaveBeenCalledWith('download_global_compliance_workbook');
		}
	});

	it('renders trust validation and one-pager collateral CTAs', async () => {
		const onTrackCta = vi.fn();
		const view = render(LandingTrustSection, {
			props: {
				aboutHref: '/about?source=trust_about',
				docsHref: '/docs?source=trust_docs',
				statusHref: '/status?source=trust_status',
				enterprisePathHref: '/enterprise?source=trust_enterprise',
				requestValidationBriefingHref:
					'/talk-to-sales?source=trust_validation&intent=request_validation_briefing',
				onePagerHref: '/resources/valdrics-enterprise-one-pager.md',
				globalComplianceWorkbookHref: '/resources/global-finops-compliance-workbook.md',
				onTrackCta
			}
		});

		const ctaBlock = within(view.container).getByRole('generic', {
			name: 'Security proof and enterprise rollout'
		});
		expect(ctaBlock).toBeTruthy();
		if (ctaBlock) {
			const ctaView = within(ctaBlock);
			await fireEvent.click(ctaView.getByRole('link', { name: /^open enterprise path$/i }));
			expect(onTrackCta).toHaveBeenCalledWith('enterprise_review');

			await fireEvent.click(ctaView.getByRole('link', { name: /^book validation briefing$/i }));
			expect(onTrackCta).toHaveBeenCalledWith('request_validation_briefing');

			await fireEvent.click(ctaView.getByRole('link', { name: /download executive one-pager/i }));
			expect(onTrackCta).toHaveBeenCalledWith('download_executive_one_pager');
		}
	});

	it('keeps trust content static and free of testimonial rotators or polling', () => {
		const fetchMock = vi.spyOn(globalThis, 'fetch');

		try {
			const trust = render(LandingTrustSection, {
				props: {
					aboutHref: '/about?source=trust_about',
					docsHref: '/docs?source=trust_docs',
					statusHref: '/status?source=trust_status',
					enterprisePathHref: '/enterprise?source=trust_enterprise',
					requestValidationBriefingHref:
						'/talk-to-sales?source=trust_validation&intent=request_validation_briefing',
					onePagerHref: '/resources/valdrics-enterprise-one-pager.md',
					globalComplianceWorkbookHref: '/resources/global-finops-compliance-workbook.md',
					onTrackCta: vi.fn()
				}
			});
			const trustView = within(trust.container);

			expect(
				trustView.getByText(/every material action keeps owner, approval, and savings evidence/i)
			).toBeTruthy();
			expect(
				trustView.getByText(/cross-functional teams work from one governed system/i)
			).toBeTruthy();
			expect(
				trustView.getByText(/the first controlled workflow lands without a services-heavy rollout/i)
			).toBeTruthy();
			expect(trustView.getByRole('link', { name: /about valdrics/i })).toBeTruthy();
			expect(trustView.getByRole('link', { name: /^open docs$/i })).toBeTruthy();
			expect(trustView.getByRole('link', { name: /view status/i })).toBeTruthy();
			expect(trustView.queryByRole('button', { name: /next comment/i })).toBeNull();
			expect(trustView.queryByRole('button', { name: /show comment/i })).toBeNull();
			expect(fetchMock).not.toHaveBeenCalled();
		} finally {
			fetchMock.mockRestore();
		}
	});

	it('updates ROI controls and CTA callback from calculator component', async () => {
		const onRoiControlInput = vi.fn();
		const onRoiMonthlySpendChange = vi.fn();
		const onRoiExpectedReductionChange = vi.fn();
		const onRoiRolloutDaysChange = vi.fn();
		const onRoiTeamMembersChange = vi.fn();
		const onRoiBlendedHourlyChange = vi.fn();
		const onRoiCta = vi.fn();

		const roiInputs = normalizeLandingRoiInputs({
			monthlySpendUsd: 120000,
			expectedReductionPct: 12,
			rolloutDays: 30,
			teamMembers: 2,
			blendedHourlyUsd: 145,
			platformAnnualCostUsd: 9600
		});
		const roiResult = calculateLandingRoi(roiInputs);

		render(LandingRoiCalculator, {
			props: {
				roiInputs,
				roiResult,
				roiMonthlySpendUsd: 120000,
				roiExpectedReductionPct: 12,
				roiRolloutDays: 30,
				roiTeamMembers: 2,
				roiBlendedHourlyUsd: 145,
				buildRoiCtaHref: '/auth/login?intent=roi_assessment',
				formatUsd: (amount: number, currency: string = 'USD') => {
					if (currency === 'EUR') return `€${amount}`;
					if (currency === 'GBP') return `£${amount}`;
					return `$${amount}`;
				},
				onRoiControlInput,
				onRoiMonthlySpendChange,
				onRoiExpectedReductionChange,
				onRoiRolloutDaysChange,
				onRoiTeamMembersChange,
				onRoiBlendedHourlyChange,
				onRoiCta
			}
		});

		await fireEvent.input(screen.getByLabelText(/cloud \+ software monthly spend/i), {
			target: { value: '130000' }
		});
		await fireEvent.input(screen.getByLabelText(/expected reduction/i), {
			target: { value: '13' }
		});
		await fireEvent.input(screen.getByLabelText(/rollout duration/i), { target: { value: '35' } });
		await fireEvent.input(screen.getByLabelText(/team members/i), { target: { value: '3' } });
		await fireEvent.input(screen.getByLabelText(/blended hourly rate/i), {
			target: { value: '150' }
		});

		await fireEvent.click(screen.getByRole('link', { name: /run this in your environment/i }));

		expect(onRoiMonthlySpendChange).toHaveBeenCalledWith(130000);
		expect(onRoiExpectedReductionChange).toHaveBeenCalledWith(13);
		expect(onRoiRolloutDaysChange).toHaveBeenCalledWith(35);
		expect(onRoiTeamMembersChange).toHaveBeenCalledWith(3);
		expect(onRoiBlendedHourlyChange).toHaveBeenCalledWith(150);
		expect(onRoiControlInput).toHaveBeenCalledTimes(5);
		expect(onRoiCta).toHaveBeenCalledTimes(1);
	});
});
