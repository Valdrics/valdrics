import { edgeApiPath } from '$lib/edgeProxy';
import { TimeoutError, fetchWithTimeout } from '$lib/fetchWithTimeout';
import {
	normalizeSpendProvider,
	operationalProviderParam,
	spendProviderParam
} from '$lib/spendProviderFilters';
import type { PageLoad } from './$types';

const DASHBOARD_REQUEST_TIMEOUT_MS = 8000;

function buildApiPath(
	path: string,
	params: Record<string, string | number | boolean | undefined>
): string {
	const query = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		query.set(key, String(value));
	}
	const suffix = query.toString();
	return edgeApiPath(suffix.length > 0 ? `${path}?${suffix}` : path);
}

function ledgerCostSummary(payload: unknown): { total_cost: number } | null {
	if (!payload || typeof payload !== 'object') return null;
	const candidate = payload as {
		total_cost_usd?: unknown;
		total_cost?: unknown;
		summary?: { total_cost?: unknown };
	};
	const rawTotal =
		candidate.total_cost_usd ?? candidate.total_cost ?? candidate.summary?.total_cost;
	const totalCost = typeof rawTotal === 'number' ? rawTotal : Number(String(rawTotal ?? ''));
	if (!Number.isFinite(totalCost)) return null;
	return { total_cost: totalCost };
}

export const load: PageLoad = async ({ fetch, parent, url }) => {
	const { session, user, subscription, profile } = await parent();

	const startDate = url.searchParams.get('start_date');
	const endDate = url.searchParams.get('end_date');
	const provider = normalizeSpendProvider(url.searchParams.get('provider'));
	const persona = String(profile?.persona ?? 'engineering').toLowerCase();

	if (!user || !session?.access_token || !startDate || !endDate) {
		return {
			costs: null,
			carbon: null,
			zombies: null,
			analysis: null,
			allocation: null,
			unitEconomics: null,
			freshness: null,
			startDate,
			endDate,
			provider
		};
	}

	const headers = {
		Authorization: `Bearer ${session?.access_token}`
	};
	const tier = String(subscription?.tier ?? 'free').toLowerCase();
	const hasChargeback = ['growth', 'pro', 'enterprise'].includes(tier);
	const hasUnitEconomics = ['starter', 'growth', 'pro', 'enterprise', 'free'].includes(tier);

	const getWithTimeout = (input: string) =>
		fetchWithTimeout(fetch, input, { headers }, DASHBOARD_REQUEST_TIMEOUT_MS);

	try {
		const wantsUnitEconomics = persona === 'finance' || persona === 'leadership';
		const wantsAllocation = persona === 'finance' || persona === 'leadership';
		const wantsCarbon = persona !== 'engineering';
		const wantsZombiesAnalysis = persona === 'engineering';
		const spendProvider = spendProviderParam(provider);
		const operationalProvider = operationalProviderParam(provider);
		type WidgetKey =
			| 'spendLedger'
			| 'costFreshness'
			| 'carbon'
			| 'zombies'
			| 'allocation'
			| 'unitEconomics';

		const carbonPromise = wantsCarbon
			? getWithTimeout(
					buildApiPath('/carbon', {
						start_date: startDate,
						end_date: endDate,
						provider: operationalProvider
					})
				)
			: Promise.resolve(null);

		const zombiesParams = new URLSearchParams();
		if (wantsZombiesAnalysis) zombiesParams.set('analyze', 'true');
		if (operationalProvider) zombiesParams.set('provider', operationalProvider);
		const zombiesUrl =
			zombiesParams.size > 0
				? `${edgeApiPath('/zombies')}?${zombiesParams.toString()}`
				: edgeApiPath('/zombies');

		const widgetRequests: Array<{
			key: WidgetKey;
			label: string;
			request: Promise<Response | null>;
		}> = [
			{
				key: 'spendLedger',
				label: 'spend ledger',
				request: getWithTimeout(
					buildApiPath('/costs/ledger', {
						start_date: startDate,
						end_date: endDate,
						provider: spendProvider,
						limit: 1
					})
				)
			},
			{
				key: 'costFreshness',
				label: 'cost freshness',
				request:
					provider === 'ai'
						? Promise.resolve(null)
						: getWithTimeout(
								buildApiPath('/costs', {
									start_date: startDate,
									end_date: endDate,
									provider: operationalProvider
								})
							)
			},
			{
				key: 'carbon',
				label: 'carbon',
				request: carbonPromise
			},
			{
				key: 'zombies',
				label: 'zombies',
				request: getWithTimeout(zombiesUrl)
			},
			{
				key: 'allocation',
				label: 'allocation',
				request:
					hasChargeback && wantsAllocation
						? getWithTimeout(
								buildApiPath('/costs/attribution/summary', {
									start_date: startDate,
									end_date: endDate
								})
							)
						: Promise.resolve(null)
			},
			{
				key: 'unitEconomics',
				label: 'unit economics',
				request:
					hasUnitEconomics && wantsUnitEconomics
						? getWithTimeout(
								buildApiPath('/costs/unit-economics', {
									start_date: startDate,
									end_date: endDate,
									provider: operationalProvider,
									alert_on_anomaly: false
								})
							)
						: Promise.resolve(null)
			}
		];

		const results = await Promise.allSettled(widgetRequests.map((widget) => widget.request));
		const widgetResponses = new Map<WidgetKey, Response | null>();
		let timedOutCount = 0;
		const failedWidgets: string[] = [];

		for (const [index, result] of results.entries()) {
			const widget = widgetRequests[index];
			if (!widget) continue;
			if (result.status === 'fulfilled') {
				const response = result.value ?? null;
				widgetResponses.set(widget.key, response);
				if (response && !response.ok) {
					failedWidgets.push(`${widget.label} (${response.status})`);
				}
				continue;
			}
			widgetResponses.set(widget.key, null);
			if (result.reason instanceof TimeoutError) {
				timedOutCount += 1;
			} else {
				failedWidgets.push(`${widget.label} (request failed)`);
			}
		}

		const spendLedgerRes = widgetResponses.get('spendLedger') ?? null;
		const costFreshnessRes = widgetResponses.get('costFreshness') ?? null;
		const carbonRes = widgetResponses.get('carbon') ?? null;
		const zombiesRes = widgetResponses.get('zombies') ?? null;
		const allocationRes = widgetResponses.get('allocation') ?? null;
		const unitEconomicsRes = widgetResponses.get('unitEconomics') ?? null;

		const spendLedger = spendLedgerRes?.ok ? await spendLedgerRes.json() : null;
		const costFreshness = costFreshnessRes?.ok ? await costFreshnessRes.json() : null;
		const ledgerCosts = ledgerCostSummary(spendLedger);
		const fallbackCosts = provider === 'ai' ? null : ledgerCostSummary(costFreshness);
		const costs = ledgerCosts ?? fallbackCosts;
		if (costs && !ledgerCosts && spendLedgerRes && [401, 403].includes(spendLedgerRes.status)) {
			const expectedFallbackFailure = `spend ledger (${spendLedgerRes.status})`;
			const fallbackFailureIndex = failedWidgets.indexOf(expectedFallbackFailure);
			if (fallbackFailureIndex >= 0) failedWidgets.splice(fallbackFailureIndex, 1);
		}
		const carbon = carbonRes?.ok ? await carbonRes.json() : null;
		const zombies = zombiesRes?.ok ? await zombiesRes.json() : null;
		const analysis: { analysis?: string } | null = null;
		const allocation = allocationRes && allocationRes.ok ? await allocationRes.json() : null;
		const unitEconomics =
			unitEconomicsRes && unitEconomicsRes.ok ? await unitEconomicsRes.json() : null;
		const freshness = provider === 'ai' ? null : (costFreshness?.data_quality?.freshness ?? null);
		const timedOutWarning =
			timedOutCount > 0
				? `${timedOutCount} dashboard widgets timed out. Partial data shown; refresh to retry.`
				: '';
		const failedWidgetsWarning =
			failedWidgets.length > 0 ? `Some dashboard widgets failed: ${failedWidgets.join(', ')}.` : '';
		const warningMessage = [timedOutWarning, failedWidgetsWarning].filter(Boolean).join(' ');

		return {
			costs,
			carbon,
			zombies,
			analysis,
			allocation,
			unitEconomics,
			freshness,
			startDate,
			endDate,
			provider,
			error: warningMessage.length > 0 ? warningMessage : undefined
		};
	} catch (err) {
		const e = err as Error;
		return {
			costs: null,
			carbon: null,
			zombies: null,
			analysis: null,
			allocation: null,
			unitEconomics: null,
			freshness: null,
			startDate,
			endDate,
			error: e.message
		};
	}
};
