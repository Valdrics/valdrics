<script lang="ts">
	import type { PendingRequest, PolicyPreview } from './opsTypes';

	let {
		open = false,
		selectedRequest = null,
		selectedPolicyPreview = null,
		policyPreviewLoading = false,
		remediationSubmitting = false,
		remediationModalError = '',
		remediationModalSuccess = '',
		actingId = null,
		bypassGracePeriod = $bindable(false),
		formatUsd,
		formatDate,
		policyDecisionClass,
		onClose,
		onPreview,
		onApprove,
		onExecute
	}: {
		open?: boolean;
		selectedRequest?: PendingRequest | null;
		selectedPolicyPreview?: PolicyPreview | null;
		policyPreviewLoading?: boolean;
		remediationSubmitting?: boolean;
		remediationModalError?: string;
		remediationModalSuccess?: string;
		actingId?: string | null;
		bypassGracePeriod: boolean;
		formatUsd: (value: number) => string;
		formatDate: (value: string | null) => string;
		policyDecisionClass: (decision: string | undefined) => string;
		onClose: () => void | Promise<void>;
		onPreview: () => void | Promise<void>;
		onApprove: () => void | Promise<void>;
		onExecute: () => void | Promise<void>;
	} = $props();
</script>

{#if open && selectedRequest}
	<div class="fixed inset-0 z-[150] flex items-center justify-center p-4">
		<button
			type="button"
			class="absolute inset-0 bg-ink-950/70 backdrop-blur-sm border-0"
			aria-label="Close remediation modal"
			onclick={onClose}
		></button>
		<div
			class="relative w-full max-w-2xl card border border-ink-700"
			role="dialog"
			aria-modal="true"
			aria-label="Remediation review"
		>
			<div class="flex items-center justify-between mb-4">
				<div>
					<h3 class="text-lg font-semibold">Remediation Request Review</h3>
					<p class="text-xs text-ink-400 mt-1 font-mono">{selectedRequest.id}</p>
				</div>
				<button type="button" class="btn btn-secondary text-xs" onclick={onClose}>Close</button>
			</div>

			<div class="space-y-3 text-sm">
				<div class="text-ink-300">
					<span class="text-ink-500">Resource:</span>
					{selectedRequest.resource_type} ({selectedRequest.resource_id})
				</div>
				{#if selectedRequest.provider}
					<div class="text-ink-300">
						<span class="text-ink-500">Provider:</span>
						{selectedRequest.provider.toUpperCase()}
					</div>
				{/if}
				{#if selectedRequest.region}
					<div class="text-ink-300">
						<span class="text-ink-500">Region:</span>
						{selectedRequest.region}
					</div>
				{/if}
				<div class="text-ink-300">
					<span class="text-ink-500">Action:</span>
					{selectedRequest.action.replaceAll('_', ' ')}
				</div>
				<div class="text-ink-300">
					<span class="text-ink-500">Estimated savings:</span>
					{formatUsd(selectedRequest.estimated_savings)}
				</div>
				<div class="text-ink-300 capitalize">
					<span class="text-ink-500">Status:</span>
					{selectedRequest.status.replaceAll('_', ' ')}
				</div>
				{#if selectedRequest.status === 'scheduled'}
					<div class="text-ink-300">
						<span class="text-ink-500">Scheduled for:</span>
						{formatDate(selectedRequest.scheduled_execution_at || null)}
					</div>
				{/if}
				{#if selectedRequest.escalation_required}
					<div class="badge badge-warning">
						Escalated: {selectedRequest.escalation_reason || 'Owner approval required'}
					</div>
				{/if}

				{#if policyPreviewLoading}
					<div class="card border border-ink-700">
						<div class="skeleton h-4 w-44 mb-2"></div>
						<div class="skeleton h-4 w-full"></div>
					</div>
				{:else if selectedPolicyPreview}
					<div class="flex items-center gap-2">
						<span class={policyDecisionClass(selectedPolicyPreview.decision)}>
							{selectedPolicyPreview.decision.toUpperCase()}
						</span>
						<span class="text-xs text-ink-500 uppercase">{selectedPolicyPreview.tier}</span>
					</div>
					<p class="text-ink-300">{selectedPolicyPreview.summary}</p>
					{#if selectedPolicyPreview.rule_hits.length > 0}
						<div class="rounded-lg border border-ink-700 p-3">
							<p class="text-xs uppercase tracking-wide text-ink-500 mb-2">Rule Hits</p>
							<ul class="space-y-1 text-xs text-ink-300">
								{#each selectedPolicyPreview.rule_hits as hit (hit.rule_id)}
									<li>
										<span class="font-semibold">{hit.rule_id}</span>
										{#if hit.message}
											: {hit.message}
										{/if}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				{/if}

				{#if remediationModalError}
					<div class="card border-danger-500/50 bg-danger-500/10">
						<p class="text-danger-400 text-xs">{remediationModalError}</p>
					</div>
				{/if}

				{#if remediationModalSuccess}
					<div class="card border-success-500/50 bg-success-500/10">
						<p class="text-success-400 text-xs">{remediationModalSuccess}</p>
					</div>
				{/if}
			</div>

			<div class="mt-5 flex items-center justify-end gap-2">
				{#if selectedRequest.status === 'approved' || selectedRequest.status === 'scheduled'}
					<label class="flex items-center gap-2 text-xs text-ink-400 mr-auto">
						<input type="checkbox" bind:checked={bypassGracePeriod} />
						Bypass grace period
					</label>
				{/if}
				<button
					type="button"
					class="btn btn-secondary text-xs"
					onclick={onPreview}
					disabled={policyPreviewLoading || remediationSubmitting}
				>
					{policyPreviewLoading ? 'Refreshing...' : 'Re-run Preview'}
				</button>
				<button
					type="button"
					class="btn btn-secondary text-xs"
					onclick={onApprove}
					disabled={remediationSubmitting ||
						policyPreviewLoading ||
						!(
							selectedRequest.status === 'pending' || selectedRequest.status === 'pending_approval'
						)}
				>
					{remediationSubmitting && actingId === selectedRequest.id ? 'Approving...' : 'Approve'}
				</button>
				<button
					type="button"
					class="btn btn-primary text-xs"
					onclick={onExecute}
					disabled={remediationSubmitting ||
						policyPreviewLoading ||
						selectedRequest.status === 'pending' ||
						selectedRequest.status === 'pending_approval'}
				>
					{#if remediationSubmitting && actingId === selectedRequest.id}
						Executing...
					{:else if selectedRequest.status === 'pending'}
						Approve First
					{:else if selectedRequest.status === 'pending_approval'}
						Awaiting Approval
					{:else}
						Execute
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
