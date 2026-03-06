<script lang="ts">
	import { BarChart3, RefreshCw } from '@lucide/svelte';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError, fetchWithTimeout } from '$lib/fetchWithTimeout';

	type CampaignRow = {
		utm_source: string;
		utm_medium: string;
		utm_campaign: string;
		total_events: number;
		cta_events: number;
		signup_intent_events: number;
		first_seen_at: string | null;
		last_seen_at: string | null;
	};

	type CampaignMetricsResponse = {
		window_start: string;
		window_end: string;
		days: number;
		total_events: number;
		items: CampaignRow[];
	};

	let { data } = $props();
	const REQUEST_TIMEOUT_MS = 10000;
	const QUERY_LIMIT = 100;

	let days = $state(30);
	let loading = $state(false);
	let refreshing = $state(false);
	let forbidden = $state(false);
	let error = $state('');
	let metrics = $state<CampaignMetricsResponse | null>(null);
	let requestToken = 0;

	function formatDate(value: string | null): string {
		if (!value) return 'n/a';
		return new Date(value).toLocaleString();
	}

	function buildApiPath(windowDays: number): string {
		const params = new URLSearchParams({
			days: String(windowDays),
			limit: String(QUERY_LIMIT)
		});
		return edgeApiPath(`/admin/landing/campaigns?${params.toString()}`);
	}

	function extractApiError(payload: unknown): string | null {
		if (!payload || typeof payload !== 'object') return null;
		const body = payload as Record<string, unknown>;
		if (typeof body.detail === 'string' && body.detail.trim()) return body.detail;
		if (typeof body.error === 'string' && body.error.trim()) return body.error;
		if (typeof body.message === 'string' && body.message.trim()) return body.message;
		return null;
	}

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
				buildApiPath(windowDays),
				{
					headers: {
						Authorization: `Bearer ${accessToken}`
					}
				},
				REQUEST_TIMEOUT_MS
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
					extractApiError(payload) ||
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
						Global campaign rollups from landing telemetry ingestion.
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
			<section class="grid gap-4 md:grid-cols-3">
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
									<td class="py-2 text-ink-400">{formatDate(item.last_seen_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</section>
		{/if}
	</section>
</AuthGate>
