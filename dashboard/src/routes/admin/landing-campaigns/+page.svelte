<script lang="ts">
	import { BarChart3, RefreshCw } from '@lucide/svelte';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { TimeoutError, fetchWithTimeout } from '$lib/fetchWithTimeout';
	import {
		buildLandingCampaignApiPath,
		extractLandingCampaignApiError,
		formatCampaignDate,
		formatCampaignDelta,
		formatCampaignPercent,
		formatCampaignRateDelta,
		getFunnelAlertTone,
		LANDING_CAMPAIGN_REQUEST_TIMEOUT_MS,
		type CampaignMetricsResponse
	} from './landingCampaignAnalytics';

	let { data } = $props();
	let days = $state(30);
	let loading = $state(false);
	let refreshing = $state(false);
	let forbidden = $state(false);
	let error = $state('');
	let metrics = $state<CampaignMetricsResponse | null>(null);
	let requestToken = 0;

	async function loadMetrics(windowDays: number): Promise<void> {
		const accessToken = data.session?.access_token;
		if (!data.user || !accessToken) {
			error = '';
			forbidden = false;
			metrics = null;
			loading = false;
			refreshing = false;
			return;
		}

		const currentToken = ++requestToken;
		loading = true;
		error = '';
		forbidden = false;

		try {
			const response = await fetchWithTimeout(
				fetch,
				buildLandingCampaignApiPath(windowDays),
				{
					headers: {
						Authorization: `Bearer ${accessToken}`
					}
				},
				LANDING_CAMPAIGN_REQUEST_TIMEOUT_MS
			);

			if (currentToken !== requestToken) return;

			if (response.status === 403) {
				forbidden = true;
				metrics = null;
				error = 'Admin role required to view campaign attribution analytics.';
				return;
			}

			if (response.status === 401) {
				metrics = null;
				error = 'Session expired. Please sign in again.';
				return;
			}

			if (!response.ok) {
				const payload = await response.json().catch(() => ({}));
				metrics = null;
				error =
					extractLandingCampaignApiError(payload) ||
					`Failed to load campaign analytics (HTTP ${response.status}).`;
				return;
			}

			metrics = (await response.json()) as CampaignMetricsResponse;
		} catch (exc) {
			if (currentToken !== requestToken) return;
			metrics = null;
			error =
				exc instanceof TimeoutError
					? 'Campaign analytics request timed out. Try again.'
					: (exc as Error).message || 'Failed to load campaign analytics.';
		} finally {
			if (currentToken === requestToken) {
				loading = false;
				refreshing = false;
			}
		}
	}

	async function refresh(): Promise<void> {
		if (refreshing) return;
		refreshing = true;
		await loadMetrics(days);
	}

	function updateDays(windowDays: number): void {
		if (windowDays === days || loading) return;
		days = windowDays;
		void loadMetrics(windowDays);
	}

	$effect(() => {
		void loadMetrics(days);
	});
</script>

<svelte:head>
	<title>Landing Campaign Analytics | Valdrics Admin</title>
</svelte:head>

<AuthGate authenticated={!!data.user} action="view landing campaign analytics">
	<section class="space-y-6">
		<header class="card border border-ink-800">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div>
					<p class="text-xs uppercase tracking-[0.14em] text-accent-300 font-bold">
						Attribution Ops
					</p>
					<h1 class="text-2xl font-semibold text-ink-100 mt-1">Landing campaign analytics</h1>
					<p class="mt-2 text-sm text-ink-400">
						Global campaign rollups from anonymous landing telemetry through authenticated activation
						and paid conversion.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="btn btn-secondary"
						onclick={() => updateDays(7)}
						aria-pressed={days === 7}
					>
						7d
					</button>
					<button
						type="button"
						class="btn btn-secondary"
						onclick={() => updateDays(30)}
						aria-pressed={days === 30}
					>
						30d
					</button>
					<button
						type="button"
						class="btn btn-secondary"
						onclick={() => updateDays(90)}
						aria-pressed={days === 90}
					>
						90d
					</button>
					<button type="button" class="btn btn-secondary" onclick={refresh} disabled={refreshing}>
						<RefreshCw class={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
						<span>{refreshing ? 'Refreshing' : 'Refresh'}</span>
					</button>
				</div>
			</div>
		</header>

		{#if loading && !metrics}
			<section class="card border border-ink-800">
				<p class="text-sm text-ink-400">Loading campaign analytics...</p>
			</section>
		{:else if forbidden}
			<section class="card border border-danger-500/40 bg-danger-500/10">
				<p class="text-sm text-danger-300">{error}</p>
			</section>
		{:else if error}
			<section class="card border border-danger-500/40 bg-danger-500/10">
				<p class="text-sm text-danger-300">{error}</p>
			</section>
		{:else if metrics}
			<section class="grid gap-4 md:grid-cols-4">
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Window</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.days} days</p>
					<p class="text-xs text-ink-500 mt-1">{metrics.window_start} to {metrics.window_end}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Total events</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_events}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Campaigns returned</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.items.length}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Paid activations</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_paid_tenants}</p>
					<p class="text-xs text-ink-500 mt-1">{metrics.total_pql_tenants} product-qualified tenants</p>
				</article>
			</section>

			<section class="grid gap-4 md:grid-cols-4">
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Onboarded</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_onboarded_tenants}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Connected</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_connected_tenants}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">First value</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_first_value_tenants}</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">Checkout started</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">{metrics.total_checkout_started_tenants}</p>
					<p class="text-xs text-ink-500 mt-1">{metrics.total_pricing_view_tenants} pricing views</p>
				</article>
			</section>

			<section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">7d signup → connection</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">
						{formatCampaignPercent(metrics.weekly_current.signup_to_connection_rate)}
					</p>
					<p class="text-xs text-ink-500 mt-1">
						{formatCampaignRateDelta(metrics.weekly_delta.signup_to_connection_rate)} vs previous 7d
					</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">7d connection → first value</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">
						{formatCampaignPercent(metrics.weekly_current.connection_to_first_value_rate)}
					</p>
					<p class="text-xs text-ink-500 mt-1">
						{formatCampaignRateDelta(metrics.weekly_delta.connection_to_first_value_rate)} vs previous 7d
					</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">7d PQL delta</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">
						{formatCampaignDelta(metrics.weekly_delta.pql_tenants)}
					</p>
					<p class="text-xs text-ink-500 mt-1">
						Current {metrics.weekly_current.pql_tenants} vs previous {metrics.weekly_previous.pql_tenants}
					</p>
				</article>
				<article class="card border border-ink-800">
					<p class="text-xs uppercase tracking-[0.08em] text-ink-500">7d paid delta</p>
					<p class="text-lg font-semibold text-ink-100 mt-1">
						{formatCampaignDelta(metrics.weekly_delta.paid_tenants)}
					</p>
					<p class="text-xs text-ink-500 mt-1">
						Current {metrics.weekly_current.paid_tenants} vs previous {metrics.weekly_previous.paid_tenants}
					</p>
				</article>
			</section>

			<section class="card border border-ink-800">
				<h2 class="text-lg font-semibold text-ink-100">Weekly funnel health alerts</h2>
				<p class="mt-2 text-sm text-ink-400">
					Operating thresholds for the last 7 days. Alerts fire when onboarding-to-connection or
					connection-to-value conversion falls below floor or deteriorates sharply week over week.
				</p>
				<div class="mt-4 grid gap-3 lg:grid-cols-2">
					{#each metrics.funnel_alerts as alert (alert.key)}
						<article class={`rounded-2xl border p-4 ${getFunnelAlertTone(alert.status)}`}>
							<div class="flex items-start justify-between gap-3">
								<div>
									<p class="text-xs uppercase tracking-[0.08em] font-semibold opacity-80">
										{alert.label}
									</p>
									<p class="mt-1 text-lg font-semibold">{formatCampaignPercent(alert.current_rate)}</p>
								</div>
								<span class="text-xs uppercase tracking-[0.08em] font-semibold">
									{alert.status.replace('_', ' ')}
								</span>
							</div>
							<p class="mt-3 text-sm opacity-90">{alert.message}</p>
							<p class="mt-3 text-xs opacity-80">
								Threshold {formatCampaignPercent(alert.threshold_rate)} · Previous {formatCampaignPercent(alert.previous_rate)}
								· Delta {formatCampaignRateDelta(alert.weekly_delta)}
							</p>
							<p class="mt-1 text-xs opacity-80">
								{alert.current_numerator}/{alert.current_denominator} tenants this week
							</p>
						</article>
					{/each}
				</div>
			</section>

			<section class="card border border-ink-800 overflow-x-auto">
				<div class="flex items-center gap-2">
					<BarChart3 class="h-4 w-4 text-accent-300" />
					<h2 class="text-lg font-semibold text-ink-100">Campaign rollup</h2>
				</div>

				{#if metrics.items.length === 0}
					<p class="text-sm text-ink-400 mt-3">
						No campaign telemetry has been ingested for this window yet.
					</p>
				{:else}
					<table class="w-full text-sm mt-4">
						<thead>
							<tr class="text-left text-ink-500 border-b border-ink-800">
								<th class="py-2 pr-3 font-medium">Source</th>
								<th class="py-2 pr-3 font-medium">Medium</th>
								<th class="py-2 pr-3 font-medium">Campaign</th>
								<th class="py-2 pr-3 font-medium">Total</th>
								<th class="py-2 pr-3 font-medium">CTA</th>
								<th class="py-2 pr-3 font-medium">Signup Intent</th>
								<th class="py-2 pr-3 font-medium">Onboarded</th>
								<th class="py-2 pr-3 font-medium">Connected</th>
								<th class="py-2 pr-3 font-medium">First Value</th>
								<th class="py-2 pr-3 font-medium">PQL</th>
								<th class="py-2 pr-3 font-medium">Checkout</th>
								<th class="py-2 pr-3 font-medium">Paid</th>
								<th class="py-2 font-medium">Last Seen</th>
							</tr>
						</thead>
						<tbody>
							{#each metrics.items as item (`${item.utm_source}-${item.utm_medium}-${item.utm_campaign}`)}
								<tr class="border-b border-ink-900/80">
									<td class="py-2 pr-3 text-ink-200">{item.utm_source}</td>
									<td class="py-2 pr-3 text-ink-300">{item.utm_medium}</td>
									<td class="py-2 pr-3 text-ink-100 font-medium">{item.utm_campaign}</td>
									<td class="py-2 pr-3 text-ink-100">{item.total_events}</td>
									<td class="py-2 pr-3 text-ink-100">{item.cta_events}</td>
									<td class="py-2 pr-3 text-ink-100">{item.signup_intent_events}</td>
									<td class="py-2 pr-3 text-ink-100">{item.onboarded_tenants}</td>
									<td class="py-2 pr-3 text-ink-100">{item.connected_tenants}</td>
									<td class="py-2 pr-3 text-ink-100">{item.first_value_tenants}</td>
									<td class="py-2 pr-3 text-ink-100">{item.pql_tenants}</td>
									<td class="py-2 pr-3 text-ink-100">{item.checkout_started_tenants}</td>
									<td class="py-2 pr-3 text-ink-100">{item.paid_tenants}</td>
									<td class="py-2 text-ink-400">{formatCampaignDate(item.last_seen_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</section>
		{/if}
	</section>
</AuthGate>
