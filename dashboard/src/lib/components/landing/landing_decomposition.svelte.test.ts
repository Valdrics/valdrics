import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/svelte';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import LandingHeroCopy from '$lib/components/landing/LandingHeroCopy.svelte';
import LandingRoiSimulator from '$lib/components/landing/LandingRoiSimulator.svelte';
import LandingRoiCalculator from '$lib/components/landing/LandingRoiCalculator.svelte';
import LandingRoiPlannerCta from '$lib/components/landing/LandingRoiPlannerCta.svelte';
import { calculateLandingRoi, normalizeLandingRoiInputs } from '$lib/landing/roiCalculator';
import './landing_decomposition.lead_exit.svelte.test';

vi.mock('$app/paths', () => ({
	assets: '',
	base: ''
}));

afterEach(() => {
	cleanup();
});

describe('Landing component decomposition', () => {
	it('renders hero copy, ROI cue, and CTA tracking callbacks', async () => {
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
		expect(screen.getByText(/cloud, saas, and software in one place/i)).toBeTruthy();
		expect(screen.getByText(/proof ready for finance and procurement/i)).toBeTruthy();
		await fireEvent.click(screen.getByRole('link', { name: /start free workspace/i }));
		await fireEvent.click(screen.getByRole('link', { name: /see pricing/i }));
		expect(onPrimaryCta).toHaveBeenCalledTimes(1);
		expect(onSecondaryCta).toHaveBeenCalledTimes(1);
	});

	it('updates simulator controls, currency selection, and planner CTA', async () => {
		const onTrackScenarioAdjust = vi.fn();
		const onScenarioWasteWithoutChange = vi.fn();
		const onScenarioWasteWithChange = vi.fn();
		const onScenarioWindowChange = vi.fn();
		const onTrackPlannerCta = vi.fn();
		const onCurrencyCodeChange = vi.fn();

		const view = render(LandingRoiSimulator, {
			props: {
				monthlySpendUsd: 120000,
				scenarioWasteWithoutPct: 18,
				scenarioWasteWithPct: 7,
				scenarioWindowMonths: 12,
				currencyCode: 'USD',
				localCurrencyCode: 'EUR',
				onCurrencyCodeChange,
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
		await fireEvent.click(simulatorView.getByRole('button', { name: /local eur/i }));

		expect(onScenarioWasteWithoutChange).toHaveBeenCalledWith(19);
		expect(onScenarioWasteWithChange).toHaveBeenCalledWith(8);
		expect(onScenarioWindowChange).toHaveBeenCalledWith(11);
		expect(onCurrencyCodeChange).toHaveBeenCalledWith('EUR');
		expect(onTrackScenarioAdjust).toHaveBeenCalledTimes(3);
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
		expect(view.container.querySelectorAll('progress')).toHaveLength(2);
		await fireEvent.click(ctaView.getByRole('link', { name: /open full roi planner/i }));
		expect(onTrackCta).toHaveBeenCalledTimes(1);
	});

	it('updates ROI controls, currency selector, and CTA callback from calculator component', async () => {
		const onRoiControlInput = vi.fn();
		const onRoiMonthlySpendChange = vi.fn();
		const onRoiExpectedReductionChange = vi.fn();
		const onRoiRolloutDaysChange = vi.fn();
		const onRoiTeamMembersChange = vi.fn();
		const onRoiBlendedHourlyChange = vi.fn();
		const onRoiCta = vi.fn();
		const onCurrencyCodeChange = vi.fn();

		const roiInputs = normalizeLandingRoiInputs({
			monthlySpendUsd: 120000,
			expectedReductionPct: 12,
			rolloutDays: 30,
			teamMembers: 2,
			blendedHourlyUsd: 145,
			platformAnnualCostUsd: 9600
		});
		const roiResult = calculateLandingRoi(roiInputs);

		const view = render(LandingRoiCalculator, {
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
				onRoiCta,
				localCurrencyCode: 'GBP',
				onCurrencyCodeChange
			}
		});

		const calculatorView = within(view.container);

		await fireEvent.input(calculatorView.getByLabelText(/cloud \+ software monthly spend/i), {
			target: { value: '130000' }
		});
		await fireEvent.input(calculatorView.getByLabelText(/expected reduction/i), {
			target: { value: '13' }
		});
		await fireEvent.input(calculatorView.getByLabelText(/rollout duration/i), {
			target: { value: '35' }
		});
		await fireEvent.input(calculatorView.getByLabelText(/team members/i), {
			target: { value: '3' }
		});
		await fireEvent.input(calculatorView.getByLabelText(/blended hourly rate/i), {
			target: { value: '150' }
		});
		await fireEvent.click(calculatorView.getByRole('button', { name: /local gbp/i }));
		await fireEvent.click(
			calculatorView.getByRole('link', { name: /run this in your environment/i })
		);

		expect(onRoiMonthlySpendChange).toHaveBeenCalledWith(130000);
		expect(onRoiExpectedReductionChange).toHaveBeenCalledWith(13);
		expect(onRoiRolloutDaysChange).toHaveBeenCalledWith(35);
		expect(onRoiTeamMembersChange).toHaveBeenCalledWith(3);
		expect(onRoiBlendedHourlyChange).toHaveBeenCalledWith(150);
		expect(onCurrencyCodeChange).toHaveBeenCalledWith('GBP');
		expect(onRoiControlInput).toHaveBeenCalledTimes(5);
		expect(onRoiCta).toHaveBeenCalledTimes(1);
	});

	it('keeps landing/public components free of inline style attributes', () => {
		const landingDir = resolve(process.cwd(), 'src/lib/components/landing');
		const files = [
			'LandingHeroCopy.svelte',
			'LandingHeroBelowFold.svelte',
			'LandingHeroRoiPlaceholder.svelte',
			'LandingHeroTrustSections.svelte',
			'LandingHeroView.svelte',
			'LandingHumanProofStrip.svelte',
			'LandingOutcomeBand.svelte',
			'LandingPlansSection.svelte',
			'LandingProductSection.svelte',
			'LandingRoiCalculator.svelte',
			'LandingRoiPlannerCta.svelte',
			'LandingRoiSimulator.svelte',
			'LandingSignalMapCard.svelte',
			'LandingTrustSection.svelte'
		];

		for (const file of files) {
			const contents = readFileSync(resolve(landingDir, file), 'utf8');
			expect(contents).not.toMatch(/style\s*=/);
		}
	});
});
