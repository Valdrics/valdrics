<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import AuthGate from '$lib/components/AuthGate.svelte';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import OpsBacklogSection from './OpsBacklogSection.svelte';
	import OpsIntroSection from './OpsIntroSection.svelte';
	import OpsOperationalHealthSection from './OpsOperationalHealthSection.svelte';
	import OpsRemediationModal from './OpsRemediationModal.svelte';
	import OpsStatusBanners from './OpsStatusBanners.svelte';
	import OpsSummaryCards from './OpsSummaryCards.svelte';
	import type {
		JobRecord,
		JobStatus,
		PendingRequest,
		PolicyPreview,
		StrategyRecommendation
	} from './opsTypes';
	import { formatDate, formatUsd, policyDecisionClass } from './opsUtils';

	const OPS_REQUEST_TIMEOUT_MS = 10000;

	let { data } = $props();
	let loading = $state(false);
	let error = $state('');
	let success = $state('');
	let processingJobs = $state(false);
	let refreshingStrategies = $state(false);
	let actingId = $state<string | null>(null);
	let pendingRequests = $state<PendingRequest[]>([]);
	let jobStatus = $state<JobStatus | null>(null);
	let jobs = $state<JobRecord[]>([]);
	let recommendations = $state<StrategyRecommendation[]>([]);
	let remediationModalOpen = $state(false);
	let selectedRequest = $state<PendingRequest | null>(null);
	let selectedPolicyPreview = $state<PolicyPreview | null>(null);
	let policyPreviewLoading = $state(false);
	let remediationSubmitting = $state(false);
	let remediationModalError = $state('');
	let remediationModalSuccess = $state('');
	let bypassGracePeriod = $state(false);

	function getHeaders() {
		return {
			Authorization: `Bearer ${data.session?.access_token}`
		};
	}

	async function getWithTimeout(url: string, headers: Record<string, string>) {
		return api.get(url, { headers, timeoutMs: OPS_REQUEST_TIMEOUT_MS });
	}

	async function loadOpsData() {
		if (!data.user || !data.session?.access_token) {
			return;
		}

		error = '';
		try {
			const headers = getHeaders();
			const results = await Promise.allSettled([
				getWithTimeout(edgeApiPath('/zombies/pending'), headers),
				getWithTimeout(edgeApiPath('/jobs/status'), headers),
				getWithTimeout(edgeApiPath('/jobs/list?limit=20'), headers),
				getWithTimeout(edgeApiPath('/strategies/recommendations?status=open'), headers)
			]);

			const responseOrNull = (index: number): Response | null =>
				results[index]?.status === 'fulfilled'
					? (results[index] as PromiseFulfilledResult<Response>).value
					: null;

			const pendingRes = responseOrNull(0);
			const statusRes = responseOrNull(1);
			const jobsRes = responseOrNull(2);
			const recsRes = responseOrNull(3);

			pendingRequests = pendingRes?.ok ? ((await pendingRes.json()).requests ?? []) : [];
			jobStatus = statusRes?.ok ? await statusRes.json() : null;
			jobs = jobsRes?.ok ? await jobsRes.json() : [];
			recommendations = recsRes?.ok ? await recsRes.json() : [];

			const timedOutCount = results.filter(
				(result) => result.status === 'rejected' && result.reason instanceof TimeoutError
			).length;
			if (timedOutCount > 0) {
				error = `${timedOutCount} Ops widgets timed out. You can refresh individual sections.`;
			}

			if (selectedRequest) {
				selectedRequest = pendingRequests.find((req) => req.id === selectedRequest?.id) ?? null;
				if (!selectedRequest) {
					remediationModalOpen = false;
				}
			}
		} catch (e) {
			const err = e as Error;
			error = err.message || 'Failed to load operations data.';
		}
	}

	function closeRemediationModal() {
		if (remediationSubmitting) return;
		remediationModalOpen = false;
		selectedRequest = null;
		selectedPolicyPreview = null;
		policyPreviewLoading = false;
		remediationModalError = '';
		remediationModalSuccess = '';
		bypassGracePeriod = false;
	}

	async function previewSelectedPolicy() {
		if (!selectedRequest) return;
		policyPreviewLoading = true;
		remediationModalError = '';
		remediationModalSuccess = '';
		try {
			const headers = getHeaders();
			const res = await api.get(edgeApiPath(`/zombies/policy-preview/${selectedRequest.id}`), {
				headers
			});
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to preview policy decision.');
			}
			selectedPolicyPreview = await res.json();
		} catch (e) {
			const err = e as Error;
			selectedPolicyPreview = null;
			remediationModalError = err.message;
		} finally {
			policyPreviewLoading = false;
		}
	}

	async function openRemediationModal(req: PendingRequest) {
		if (policyPreviewLoading || remediationSubmitting) return;
		selectedRequest = req;
		selectedPolicyPreview = null;
		remediationModalError = '';
		remediationModalSuccess = '';
		bypassGracePeriod = false;
		remediationModalOpen = true;
		await previewSelectedPolicy();
	}

	async function approveSelectedRequest() {
		if (!selectedRequest || remediationSubmitting) return;
		const requestId = selectedRequest.id;
		actingId = requestId;
		remediationSubmitting = true;
		remediationModalError = '';
		remediationModalSuccess = '';
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const res = await api.post(
				edgeApiPath(`/zombies/approve/${requestId}`),
				{ notes: 'Approved from Ops Center' },
				{ headers }
			);
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to approve request.');
			}
			remediationModalSuccess = `Request ${requestId.slice(0, 8)} approved.`;
			success = remediationModalSuccess;
			await loadOpsData();
		} catch (e) {
			const err = e as Error;
			remediationModalError = err.message;
			error = err.message;
		} finally {
			actingId = null;
			remediationSubmitting = false;
		}
	}

	async function executeSelectedRequest() {
		if (!selectedRequest || remediationSubmitting) return;
		if (selectedRequest.status === 'pending' || selectedRequest.status === 'pending_approval') {
			remediationModalError = 'This request must be approved before it can execute.';
			return;
		}

		const requestId = selectedRequest.id;
		actingId = requestId;
		remediationSubmitting = true;
		remediationModalError = '';
		remediationModalSuccess = '';
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const url = bypassGracePeriod
				? edgeApiPath(`/zombies/execute/${requestId}?bypass_grace_period=true`)
				: edgeApiPath(`/zombies/execute/${requestId}`);
			const res = await api.post(url, undefined, { headers });
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to execute request.');
			}
			const payload = (await res.json().catch(() => ({}))) as { status?: string };
			const statusValue = (payload.status || '').toLowerCase();
			if (statusValue === 'scheduled') {
				remediationModalSuccess = `Request ${requestId.slice(0, 8)} scheduled after grace period.`;
			} else if (statusValue === 'completed') {
				remediationModalSuccess = `Request ${requestId.slice(0, 8)} completed.`;
			} else if (statusValue) {
				remediationModalSuccess = `Request ${requestId.slice(0, 8)} status: ${statusValue.replaceAll('_', ' ')}.`;
			} else {
				remediationModalSuccess = `Request ${requestId.slice(0, 8)} execution started.`;
			}
			success = remediationModalSuccess;
			await loadOpsData();
		} catch (e) {
			const err = e as Error;
			remediationModalError = err.message;
			error = err.message;
		} finally {
			actingId = null;
			remediationSubmitting = false;
		}
	}

	async function processPendingJobs() {
		processingJobs = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const res = await api.post(edgeApiPath('/jobs/process?limit=10'), undefined, { headers });
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to process jobs.');
			}
			const payload = await res.json();
			success = `Processed ${payload.processed} jobs (${payload.succeeded} succeeded, ${payload.failed} failed).`;
			await loadOpsData();
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			processingJobs = false;
		}
	}

	async function refreshRecommendations() {
		refreshingStrategies = true;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const res = await api.post(edgeApiPath('/strategies/refresh'), undefined, { headers });
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to refresh recommendations.');
			}
			const payload = await res.json();
			success = payload.message || 'Strategy refresh completed.';
			await loadOpsData();
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			refreshingStrategies = false;
		}
	}

	async function applyRecommendation(id: string) {
		actingId = id;
		error = '';
		success = '';
		try {
			const headers = getHeaders();
			const res = await api.post(edgeApiPath(`/strategies/apply/${id}`), undefined, {
				headers
			});
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(payload.detail || payload.message || 'Failed to apply recommendation.');
			}
			success = `Recommendation ${id.slice(0, 8)} marked as applied.`;
			await loadOpsData();
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			actingId = null;
		}
	}

	onMount(() => {
		void loadOpsData();
	});
</script>

<svelte:head>
	<title>Ops Center | Valdrics</title>
</svelte:head>

<div class="space-y-8">
	<OpsIntroSection {loading} />

	<AuthGate authenticated={!!data.user} action="access operations">
		{#if !loading}
			<OpsStatusBanners {error} {success} />

			<OpsSummaryCards
				pendingRequestsCount={pendingRequests.length}
				{jobStatus}
				recommendationsCount={recommendations.length}
			/>

			<OpsOperationalHealthSection {data} />

			<OpsBacklogSection
				{pendingRequests}
				{processingJobs}
				{jobs}
				{recommendations}
				{refreshingStrategies}
				{actingId}
				{formatDate}
				{formatUsd}
				onLoadOpsData={loadOpsData}
				onOpenRemediationModal={openRemediationModal}
				onProcessPendingJobs={processPendingJobs}
				onRefreshRecommendations={refreshRecommendations}
				onApplyRecommendation={applyRecommendation}
			/>
		{/if}
	</AuthGate>
</div>

<OpsRemediationModal
	open={remediationModalOpen}
	{selectedRequest}
	{selectedPolicyPreview}
	{policyPreviewLoading}
	{remediationSubmitting}
	{remediationModalError}
	{remediationModalSuccess}
	{actingId}
	bind:bypassGracePeriod
	{formatUsd}
	{formatDate}
	{policyDecisionClass}
	onClose={closeRemediationModal}
	onPreview={previewSelectedPolicy}
	onApprove={approveSelectedRequest}
	onExecute={executeSelectedRequest}
/>
