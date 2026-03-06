<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { buildCompliancePackPath } from '$lib/compliancePack';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { buildFocusExportPath } from '$lib/focusExport';
	import { filenameFromContentDispositionHeader } from '$lib/utils';
	import type { AuditDetail, AuditLog } from './auditTypes';
	import AuditPageViewContent from './AuditPageViewContent.svelte';

	let { data } = $props();
	const AUDIT_REQUEST_TIMEOUT_MS = 8000;
	let loading = $state(true);
	let loadingDetail = $state(false);
	let exporting = $state(false);
	let exportingPack = $state(false);
	let exportingFocus = $state(false);
	let error = $state('');
	let success = $state('');

	let logs = $state<AuditLog[]>([]);
	let eventTypes = $state<string[]>([]);
	let selectedEventType = $state('');
	let limit = $state(50);
	let offset = $state(0);

	let selectedLogId = $state<string | null>(null);
	let selectedDetail = $state<AuditDetail | null>(null);

	let focusStartDate = $state(
		new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
	);
	let focusEndDate = $state(new Date().toISOString().slice(0, 10));
	let focusProvider = $state('');
	let focusIncludePreliminary = $state(false);
	let packIncludeFocus = $state(false);
	let packIncludeSavingsProof = $state(false);
	let packIncludeClosePackage = $state(false);
	let packCloseEnforceFinalized = $state(true);
	let packCloseMaxRestatements = $state(5000);

	const savingsProviderAllowed = ['aws', 'azure', 'gcp', 'saas', 'license'];

	function getHeaders() {
		return {
			Authorization: `Bearer ${data.session?.access_token}`
		};
	}

	async function getWithTimeout(url: string, headers: Record<string, string>) {
		return api.get(url, { headers, timeoutMs: AUDIT_REQUEST_TIMEOUT_MS });
	}

	function formatDate(value: string): string {
		return new Date(value).toLocaleString();
	}

	async function loadEventTypes() {
		const headers = getHeaders();
		const res = await getWithTimeout(edgeApiPath('/audit/event-types'), headers);
		if (res.ok) {
			const payload = await res.json();
			eventTypes = payload.event_types || [];
		}
	}

	async function loadLogs() {
		if (!data.user || !data.session?.access_token) {
			loading = false;
			return;
		}

		loading = true;
		error = '';
		try {
			const headers = getHeaders();
			const queryParts = [`limit=${limit}`, `offset=${offset}`, 'order=desc'];
			if (selectedEventType) {
				queryParts.push(`event_type=${encodeURIComponent(selectedEventType)}`);
			}

			const res = await getWithTimeout(edgeApiPath(`/audit/logs?${queryParts.join('&')}`), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to load audit logs.');
			}

			logs = await res.json();
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			loading = false;
		}
	}

	async function viewDetail(id: string) {
		selectedLogId = id;
		selectedDetail = null;
		loadingDetail = true;
		error = '';
		try {
			const headers = getHeaders();
			const res = await getWithTimeout(edgeApiPath(`/audit/logs/${id}`), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to load audit log detail.');
			}
			selectedDetail = await res.json();
		} catch (e) {
			const err = e as Error;
			error = err.message;
			selectedLogId = null;
		} finally {
			loadingDetail = false;
		}
	}

	function closeDetail() {
		selectedLogId = null;
		selectedDetail = null;
	}

	async function exportCsv() {
		exporting = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const query = selectedEventType ? `event_type=${encodeURIComponent(selectedEventType)}` : '';

			const res = await getWithTimeout(edgeApiPath(`/audit/export?${query}`), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to export audit logs.');
			}

			const csv = await res.text();
			const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`;
			link.click();
			URL.revokeObjectURL(url);
			success = 'Audit log export downloaded.';
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			exporting = false;
		}
	}

	async function exportCompliancePack() {
		exportingPack = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const selectedSavingsProvider =
				focusProvider && savingsProviderAllowed.includes(focusProvider) ? focusProvider : undefined;
			const path = buildCompliancePackPath({
				includeFocusExport: packIncludeFocus,
				focusProvider: focusProvider || undefined,
				focusIncludePreliminary,
				focusMaxRows: 50000,
				focusStartDate,
				focusEndDate,
				includeSavingsProof: packIncludeSavingsProof,
				savingsProvider: selectedSavingsProvider,
				savingsStartDate: focusStartDate,
				savingsEndDate: focusEndDate,
				includeClosePackage: packIncludeClosePackage,
				closeProvider: focusProvider || undefined,
				closeStartDate: focusStartDate,
				closeEndDate: focusEndDate,
				closeEnforceFinalized: packCloseEnforceFinalized,
				closeMaxRestatements: packCloseMaxRestatements
			});

			const res = await getWithTimeout(edgeApiPath(path), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(
					payload.detail ||
						payload.message ||
						(res.status === 403
							? 'Owner role required to export compliance pack.'
							: 'Failed to export compliance pack.')
				);
			}

			const buffer = await res.arrayBuffer();
			const blob = new Blob([buffer], { type: 'application/zip' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = filenameFromContentDispositionHeader(
				res.headers.get('content-disposition'),
				`compliance-pack_${new Date().toISOString().slice(0, 10)}.zip`
			);
			link.click();
			URL.revokeObjectURL(url);
			success = 'Compliance pack downloaded.';
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			exportingPack = false;
		}
	}

	async function exportFocusCsv() {
		exportingFocus = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const path = buildFocusExportPath({
				startDate: focusStartDate,
				endDate: focusEndDate,
				provider: focusProvider,
				includePreliminary: focusIncludePreliminary
			});
			const res = await getWithTimeout(edgeApiPath(path), headers);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(
					payload.detail ||
						payload.message ||
						(res.status === 403
							? 'Pro plan + admin role required to export FOCUS.'
							: 'Failed to export FOCUS CSV.')
				);
			}

			const csv = await res.text();
			const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = filenameFromContentDispositionHeader(
				res.headers.get('content-disposition'),
				`focus-v1.3-core_${focusStartDate}_${focusEndDate}.csv`
			);
			link.click();
			URL.revokeObjectURL(url);
			success = 'FOCUS export downloaded.';
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			exportingFocus = false;
		}
	}

	async function applyFilters() {
		offset = 0;
		await loadLogs();
	}

	async function previousPage() {
		offset = Math.max(0, offset - limit);
		await loadLogs();
	}

	async function nextPage() {
		offset = offset + limit;
		await loadLogs();
	}

	onMount(() => {
		void loadEventTypes();
		void loadLogs();
	});
</script>

<svelte:head>
	<title>Audit Logs | Valdrics</title>
</svelte:head>

<AuditPageViewContent
	{data}
	{loading}
	{loadingDetail}
	{exporting}
	{exportingPack}
	{exportingFocus}
	{error}
	{success}
	{logs}
	{eventTypes}
	bind:selectedEventType
	bind:limit
	{offset}
	{selectedLogId}
	{selectedDetail}
	bind:focusStartDate
	bind:focusEndDate
	bind:focusProvider
	bind:focusIncludePreliminary
	bind:packIncludeFocus
	bind:packIncludeSavingsProof
	bind:packIncludeClosePackage
	bind:packCloseEnforceFinalized
	bind:packCloseMaxRestatements
	{formatDate}
	{applyFilters}
	{previousPage}
	{nextPage}
	{exportCsv}
	{exportCompliancePack}
	{exportFocusCsv}
	{viewDetail}
	{closeDetail}
/>
