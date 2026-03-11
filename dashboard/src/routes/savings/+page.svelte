<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { clientLogger } from '$lib/logging/client';
	import { filenameFromContentDispositionHeader } from '$lib/utils';
	import SavingsPageViewContent from './SavingsPageViewContent.svelte';
	import type { SavingsProofDrilldownResponse, SavingsProofResponse } from './savingsTypes';

	let { data } = $props();

	const SAVINGS_REQUEST_TIMEOUT_MS = 8000;

	let loading = $state(true);
	let downloading = $state(false);
	let error = $state('');
	let success = $state('');

	let report = $state<SavingsProofResponse | null>(null);
	let drilldown = $state<SavingsProofDrilldownResponse | null>(null);
	let drilldownDimension = $state<'strategy_type' | 'remediation_action'>('strategy_type');
	let provider = $state<string>('');
	let datePreset = $state('30d');
	let dateRange = $state({ startDate: '', endDate: '' });

	function isProPlus(tierValue: string | null | undefined): boolean {
		return ['pro', 'enterprise'].includes((tierValue ?? '').toLowerCase());
	}

	function getHeaders() {
		return {
			Authorization: `Bearer ${data.session?.access_token}`
		};
	}

	async function getWithTimeout(url: string, headers: Record<string, string>) {
		return api.get(url, { headers, timeoutMs: SAVINGS_REQUEST_TIMEOUT_MS });
	}

	function formatUsd(value: number): string {
		if (!Number.isFinite(value)) return '$0.00';
		return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(value);
	}

	function formatDate(value: string): string {
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return value;
		return parsed.toLocaleString();
	}

	async function loadReport() {
		if (!data.user || !data.session?.access_token) {
			loading = false;
			return;
		}
		if (!isProPlus(data.subscription?.tier)) {
			loading = false;
			return;
		}

		loading = true;
		error = '';
		success = '';
		drilldown = null;
		try {
			const headers = getHeaders();
			const params = new SvelteURLSearchParams();
			if (dateRange.startDate) params.set('start_date', dateRange.startDate);
			if (dateRange.endDate) params.set('end_date', dateRange.endDate);
			if (provider) params.set('provider', provider);
			params.set('response_format', 'json');

			const res = await getWithTimeout(edgeApiPath(`/savings/proof?${params.toString()}`), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(
					payload.detail || payload.message || 'Failed to load savings proof report.'
				);
			}
			report = (await res.json()) as SavingsProofResponse;
			void loadDrilldown();
		} catch (e) {
			clientLogger.error('Failed to load savings proof:', e);
			error =
				e instanceof TimeoutError
					? 'Savings report request timed out. Try again.'
					: (e as Error).message;
		} finally {
			loading = false;
		}
	}

	async function loadDrilldown() {
		if (!data.user || !data.session?.access_token) return;
		if (!isProPlus(data.subscription?.tier)) return;

		error = '';
		try {
			const headers = getHeaders();
			const params = new SvelteURLSearchParams();
			if (dateRange.startDate) params.set('start_date', dateRange.startDate);
			if (dateRange.endDate) params.set('end_date', dateRange.endDate);
			if (provider) params.set('provider', provider);
			params.set('dimension', drilldownDimension);
			params.set('response_format', 'json');

			const res = await getWithTimeout(
				edgeApiPath(`/savings/proof/drilldown?${params.toString()}`),
				headers
			);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to load drilldown.');
			}
			drilldown = (await res.json()) as SavingsProofDrilldownResponse;
		} catch (e) {
			clientLogger.error('Failed to load savings drilldown:', e);
			error =
				e instanceof TimeoutError
					? 'Savings drilldown request timed out. Try again.'
					: (e as Error).message;
		}
	}

	async function downloadCsv() {
		if (!data.user || !data.session?.access_token) return;
		downloading = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const params = new SvelteURLSearchParams();
			if (dateRange.startDate) params.set('start_date', dateRange.startDate);
			if (dateRange.endDate) params.set('end_date', dateRange.endDate);
			if (provider) params.set('provider', provider);
			params.set('response_format', 'csv');

			const res = await getWithTimeout(edgeApiPath(`/savings/proof?${params.toString()}`), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to export savings report.');
			}
			const csv = await res.text();
			const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = filenameFromContentDispositionHeader(
				res.headers.get('content-disposition'),
				`savings_proof_${new Date().toISOString().slice(0, 10)}.csv`
			);
			link.click();
			URL.revokeObjectURL(url);
			success = 'Savings proof export downloaded.';
		} catch (e) {
			error = (e as Error).message;
		} finally {
			downloading = false;
		}
	}

	onMount(() => {
		void loadReport();
	});
</script>

<svelte:head>
	<title>Savings Proof | Valdrics</title>
</svelte:head>

<SavingsPageViewContent
	{data}
	{loading}
	{downloading}
	{error}
	{success}
	{report}
	{drilldown}
	bind:drilldownDimension
	bind:provider
	bind:datePreset
	bind:dateRange
	{isProPlus}
	{formatUsd}
	{formatDate}
	{loadReport}
	{loadDrilldown}
	{downloadCsv}
/>
