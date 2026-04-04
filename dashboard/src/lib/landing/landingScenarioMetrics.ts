type LandingScenarioArgs = {
	monthlySpendUsd: number;
	wasteWithoutPct: number;
	wasteWithPct: number;
	windowMonths: number;
};

export function calculateLandingScenarioMetrics(args: LandingScenarioArgs) {
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
