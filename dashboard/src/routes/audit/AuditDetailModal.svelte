<script lang="ts">
	import type { AuditDetail } from './auditTypes';

	interface Props {
		selectedLogId: string | null;
		selectedDetail: AuditDetail | null;
		loadingDetail: boolean;
		closeDetail: () => void;
		formatDate: (value: string) => string;
	}

	let { selectedLogId, selectedDetail, loadingDetail, closeDetail, formatDate }: Props = $props();
</script>

{#if selectedLogId}
	<div class="fixed inset-0 z-[150] flex items-center justify-center p-4">
		<button
			type="button"
			class="absolute inset-0 bg-ink-950/70 backdrop-blur-sm border-0"
			aria-label="Close details"
			onclick={closeDetail}
		></button>
		<div
			class="relative w-full max-w-3xl max-h-[85vh] overflow-auto card border border-ink-700"
			role="dialog"
			aria-modal="true"
			aria-label="Audit log detail"
		>
			<div class="flex items-center justify-between mb-4">
				<h3 class="text-lg font-semibold">Audit Log Detail</h3>
				<button type="button" class="btn btn-secondary text-xs" onclick={closeDetail}>Close</button>
			</div>
			{#if loadingDetail}
				<div class="skeleton h-5 w-64 mb-2"></div>
				<div class="skeleton h-5 w-full mb-2"></div>
				<div class="skeleton h-5 w-full"></div>
			{:else if selectedDetail}
				<div class="space-y-3 text-sm">
					<div><strong>ID:</strong> <span class="font-mono text-xs">{selectedDetail.id}</span></div>
					<div><strong>Event:</strong> {selectedDetail.event_type}</div>
					<div><strong>Timestamp:</strong> {formatDate(selectedDetail.event_timestamp)}</div>
					<div><strong>Actor:</strong> {selectedDetail.actor_email || '-'}</div>
					<div><strong>IP:</strong> {selectedDetail.actor_ip || '-'}</div>
					<div>
						<strong>Request:</strong>
						{selectedDetail.request_method || '-'}
						{selectedDetail.request_path || '-'}
					</div>
					<div>
						<strong>Resource:</strong>
						{selectedDetail.resource_type || '-'}
						{selectedDetail.resource_id || ''}
					</div>
					<div><strong>Status:</strong> {selectedDetail.success ? 'SUCCESS' : 'FAILED'}</div>
					<div><strong>Error:</strong> {selectedDetail.error_message || '-'}</div>
					<div>
						<strong>Details JSON:</strong>
						<pre class="mt-2 p-3 rounded-lg bg-ink-900 text-xs overflow-auto">{JSON.stringify(
								selectedDetail.details || {},
								null,
								2
							)}</pre>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
