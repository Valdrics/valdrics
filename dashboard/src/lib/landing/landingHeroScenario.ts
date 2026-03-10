import { resolveGeoCurrencyHint } from '$lib/landing/landingGeoCurrency';
import { formatCurrencyAmount, SUPPORTED_CURRENCIES } from '$lib/landing/roiCalculator';

const SUPPORTED_CURRENCY_CODES = new Set(SUPPORTED_CURRENCIES.map((currency) => currency.code));

type LandingHeroScenarioArgs = {
	monthlySpendUsd: number;
	wasteWithoutPct: number;
	wasteWithPct: number;
	windowMonths: number;
};

type LandingHeroCurrencyHintArgs = {
	requestEndpoint: string;
	requestOrigin: string;
	hostname?: string;
	signal: AbortSignal;
};

export function calculateLandingHeroScenarioMetrics(args: LandingHeroScenarioArgs) {
	const normalizedScenarioWasteWithoutPct = Math.min(
		35,
		Math.max(4, Math.round(Number(args.wasteWithoutPct) || 0))
	);
	const normalizedScenarioWasteWithPct = Math.min(
		normalizedScenarioWasteWithoutPct - 1,
		Math.max(1, Math.round(Number(args.wasteWithPct) || 0))
	);
	const normalizedScenarioWindowMonths = Math.min(
		24,
		Math.max(3, Math.round(Number(args.windowMonths) || 0))
	);
	const scenarioWasteWithoutUsd = Math.round(
		(args.monthlySpendUsd * normalizedScenarioWasteWithoutPct) / 100
	);
	const scenarioWasteWithUsd = Math.round(
		(args.monthlySpendUsd * normalizedScenarioWasteWithPct) / 100
	);
	const scenarioWasteRecoveryMonthlyUsd = Math.max(
		0,
		scenarioWasteWithoutUsd - scenarioWasteWithUsd
	);
	const scenarioWasteRecoveryWindowUsd =
		scenarioWasteRecoveryMonthlyUsd * normalizedScenarioWindowMonths;
	const scenarioMaxBarUsd = Math.max(scenarioWasteWithoutUsd, scenarioWasteWithUsd, 1);

	return {
		normalizedScenarioWasteWithoutPct,
		normalizedScenarioWasteWithPct,
		normalizedScenarioWindowMonths,
		scenarioWasteWithoutUsd,
		scenarioWasteWithUsd,
		scenarioWasteRecoveryMonthlyUsd,
		scenarioWasteRecoveryWindowUsd,
		scenarioWithoutBarPct: (scenarioWasteWithoutUsd / scenarioMaxBarUsd) * 100,
		scenarioWithBarPct: (scenarioWasteWithUsd / scenarioMaxBarUsd) * 100
	};
}

export async function resolveLandingHeroCurrencyCode(
	args: LandingHeroCurrencyHintArgs
): Promise<string> {
	const currencyCode = await resolveGeoCurrencyHint({
		requestEndpoint: args.requestEndpoint,
		requestOrigin: args.requestOrigin,
		hostname: args.hostname,
		supportedCurrencyCodes: SUPPORTED_CURRENCY_CODES,
		signal: args.signal
	});
	return currencyCode ?? 'USD';
}

export function formatLandingHeroCurrencyAmount(amount: number, currency: string): string {
	return formatCurrencyAmount(amount, currency);
}
