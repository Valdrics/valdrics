<script lang="ts">
	import CloudLogo from './CloudLogo.svelte';
	import DOMPurify from 'dompurify';
	import { Terminal, Check } from '@lucide/svelte';
	import { clientLogger } from '$lib/logging/client';

	interface ZombieFinding {
		provider: 'aws' | 'azure' | 'gcp';
		finding_id?: string;
		resource_id: string;
		resource_type?: string;
		monthly_cost?: string | number;
		confidence?: 'high' | 'medium' | 'low';
		risk_if_deleted?: 'high' | 'medium' | 'low';
		explanation: string;
		confidence_reason?: string;
		recommended_action?: string;
		connection_id?: string;
		owner?: string;
		is_gpu?: boolean;
	}

	let {
		resources = [],
		onRemediate,
		remediating = null
	}: {
		resources: ZombieFinding[];
		onRemediate: (finding: ZombieFinding) => void | Promise<void>;
		remediating?: string | null;
	} = $props();

	let currentPage = $state(0);
	let copiedId = $state<string | null>(null);
	const pageSize = 10;

	let totalPages = $derived(Math.ceil(resources.length / pageSize));
	let paginatedResources = $derived(
		resources.slice(currentPage * pageSize, (currentPage + 1) * pageSize)
	);

	function providerTone(provider: ZombieFinding['provider']): string {
		return `findings-table__provider-pill findings-table__provider-pill--${provider}`;
	}

	function confidenceTone(confidence: ZombieFinding['confidence']): string {
		if (confidence === 'high') return 'findings-table__confidence-dot--high';
		if (confidence === 'medium') return 'findings-table__confidence-dot--medium';
		return 'findings-table__confidence-dot--low';
	}

	function riskTone(risk: ZombieFinding['risk_if_deleted']): string {
		if (risk === 'high') return 'findings-table__risk--high';
		if (risk === 'medium') return 'findings-table__risk--medium';
		return 'findings-table__risk--low';
	}

	function generateSniperCommand(finding: ZombieFinding): string {
		const id = finding.resource_id;
		const type = finding.resource_type?.toLowerCase() || '';

		if (finding.provider === 'aws') {
			if (type.includes('volume') || type.includes('ebs')) {
				return `aws ec2 delete-volume --volume-id ${id}`;
			}
			if (type.includes('instance')) {
				return `aws ec2 terminate-instances --instance-ids ${id}`;
			}
			if (type.includes('snapshot')) {
				return `aws ec2 delete-snapshot --snapshot-id ${id}`;
			}
			if (type.includes('eip') || type.includes('address')) {
				return `aws ec2 release-address --allocation-id ${id}`;
			}
			return `# AWS Snipe: ${id}\naws resourcegroupstaggingapi untag-resources --resource-arn-list ${id}`;
		}

		if (finding.provider === 'azure') {
			return `az resource delete --ids ${id}`;
		}

		if (finding.provider === 'gcp') {
			return `gcloud compute instances delete ${id} --quiet`;
		}

		return `# Sniper Command for ${id} not generated`;
	}

	async function copyToClipboard(text: string, id: string) {
		try {
			await navigator.clipboard.writeText(text);
			copiedId = id;
			setTimeout(() => {
				if (copiedId === id) copiedId = null;
			}, 2000);
		} catch (err) {
			clientLogger.error('Failed to copy: ', err);
		}
	}
</script>

<div class="card stagger-enter findings-table">
	<div class="findings-table__header">
		<h3 class="findings-table__title">🧟 Zombie Resources ({resources.length})</h3>
		<div class="findings-table__meta">
			<span>Page {currentPage + 1} of {totalPages}</span>
		</div>
	</div>

	<div class="findings-table__scroller">
		<table class="findings-table__table">
			<thead>
				<tr class="findings-table__row findings-table__row--head">
					<th class="findings-table__cell findings-table__cell--head">Provider</th>
					<th class="findings-table__cell findings-table__cell--head">Resource</th>
					<th class="findings-table__cell findings-table__cell--head">Type</th>
					<th class="findings-table__cell findings-table__cell--head">Cost</th>
					<th class="findings-table__cell findings-table__cell--head">Confidence</th>
					<th class="findings-table__cell findings-table__cell--head">Owner</th>
					<th class="findings-table__cell findings-table__cell--head">Risk</th>
					<th class="findings-table__cell findings-table__cell--head findings-table__cell--actions">
						Action
					</th>
				</tr>
			</thead>
			<tbody>
				{#each paginatedResources as finding (finding.resource_id)}
					<tr class="findings-table__row">
						<td class="findings-table__cell">
							<div class={providerTone(finding.provider)}>
								<CloudLogo provider={finding.provider} size={10} />
								<span>{finding.provider === 'aws' ? 'AWS' : finding.provider === 'azure' ? 'Azure' : 'GCP'}</span>
							</div>
						</td>
						<td class="findings-table__cell">
							<div class="findings-table__resource-id" title={finding.resource_id}>
								{finding.resource_id}
							</div>
							<details class="findings-table__details">
								<summary class="findings-table__summary">View details</summary>
								<p class="findings-table__explanation">
									<!-- eslint-disable-next-line svelte/no-at-html-tags -->
									{@html DOMPurify.sanitize(finding.explanation, {
										ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'br', 'p', 'ul', 'li', 'code'],
										ALLOWED_ATTR: []
									})}
								</p>
								{#if finding.confidence_reason}
									<p class="findings-table__confidence-reason">{finding.confidence_reason}</p>
								{/if}
							</details>
						</td>
						<td class="findings-table__cell">
							<span class="badge badge-default findings-table__type-pill">
								{finding.resource_type || 'Resource'}
							</span>
							{#if finding.is_gpu}
								<span class="findings-table__gpu-pill">GPU</span>
							{/if}
						</td>
						<td class="findings-table__cell findings-table__cost">
							{finding.monthly_cost || '$0'}
						</td>
						<td class="findings-table__cell">
							{#if finding.confidence}
								<span class="findings-table__confidence">
									<span class={`findings-table__confidence-dot ${confidenceTone(finding.confidence)}`}></span>
									<span class="findings-table__confidence-label">{finding.confidence}</span>
								</span>
							{:else}
								<span class="findings-table__muted">N/A</span>
							{/if}
						</td>
						<td class="findings-table__cell">
							<div class="findings-table__owner">
								{#if finding.owner === 'Growth Plan Required'}
									<span
										class="findings-table__owner-locked"
										title="Owner Attribution requires Growth tier"
									>
										<span class="findings-table__owner-locked-dot"></span>
										LOCKED
									</span>
								{:else}
									<span class="findings-table__owner-value" title={finding.owner || 'unknown'}>
										{finding.owner || 'unknown'}
									</span>
								{/if}
							</div>
						</td>
						<td class="findings-table__cell">
							<span class={`findings-table__risk ${riskTone(finding.risk_if_deleted)}`}>
								{finding.risk_if_deleted || 'low'}
							</span>
						</td>
						<td class="findings-table__cell findings-table__cell--actions">
							<div class="findings-table__actions">
								<button
									type="button"
									class="btn btn-ghost findings-table__icon-button"
									onclick={() =>
										copyToClipboard(generateSniperCommand(finding), finding.resource_id)}
									title="Copy Sniper Command"
								>
									{#if copiedId === finding.resource_id}
										<Check size={14} class="findings-table__copy-success" />
									{:else}
										<Terminal size={14} />
									{/if}
								</button>
								<button
									type="button"
									class="btn btn-ghost findings-table__action-button"
									onclick={() => onRemediate(finding)}
									disabled={remediating === finding.resource_id || !finding.finding_id}
									title={!finding.finding_id
										? 'Persisted finding binding missing. Use the latest scan output before remediation.'
										: undefined}
								>
									{#if remediating === finding.resource_id}
										<span class="findings-table__action-pending">...</span>
									{:else}
										{finding.finding_id ? finding.recommended_action || 'Review' : 'Unavailable'}
									{/if}
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if totalPages > 1}
		<div class="findings-table__pagination">
			<button
				type="button"
				class="btn btn-ghost findings-table__pagination-button"
				disabled={currentPage === 0}
				onclick={() => (currentPage = Math.max(0, currentPage - 1))}
			>
				← Previous
			</button>

			<div class="findings-table__pagination-pages">
				<!-- eslint-disable-next-line @typescript-eslint/no-unused-vars -->
				{#each Array(Math.min(totalPages, 5)) as _, p (p)}
					{@const pageNum =
						totalPages <= 5
							? p
							: currentPage < 3
								? p
								: currentPage > totalPages - 3
									? totalPages - 5 + p
									: currentPage - 2 + p}
					<button
						type="button"
						class="findings-table__page-button"
						class:findings-table__page-button--active={currentPage === pageNum}
						onclick={() => (currentPage = pageNum)}
					>
						{pageNum + 1}
					</button>
				{/each}
			</div>

			<button
				type="button"
				class="btn btn-ghost findings-table__pagination-button"
				disabled={currentPage >= totalPages - 1}
				onclick={() => (currentPage = Math.min(totalPages - 1, currentPage + 1))}
			>
				Next →
			</button>
		</div>
	{/if}
</div>

<style>
	.findings-table {
		animation-delay: 250ms;
	}

	.findings-table__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		margin-bottom: var(--space-4);
	}

	.findings-table__title {
		margin: 0;
		font-size: var(--text-lg);
		font-weight: 600;
	}

	.findings-table__meta {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--text-xs);
		color: var(--color-ink-400);
	}

	.findings-table__scroller {
		overflow-x: auto;
	}

	.findings-table__table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}

	.findings-table__row {
		border-bottom: 1px solid var(--color-ink-800);
		transition: background var(--duration-fast) var(--ease-out);
	}

	.findings-table__row:hover {
		background: rgb(33 47 68 / 0.5);
	}

	.findings-table__row--head {
		border-bottom-color: var(--color-ink-700);
		text-align: left;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-ink-400);
	}

	.findings-table__cell {
		padding: 0.75rem 1rem 0.75rem 0;
		vertical-align: top;
	}

	.findings-table__cell--head {
		padding-bottom: 0.75rem;
		font-size: var(--text-xs);
		font-weight: 600;
	}

	.findings-table__cell--actions {
		text-align: right;
	}

	.findings-table__provider-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.25rem 0.5rem;
		border-radius: var(--radius-full);
		border: 1px solid transparent;
		font-size: var(--text-xs);
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: -0.02em;
	}

	.findings-table__provider-pill--aws {
		border-color: rgb(249 115 22 / 0.2);
		background: rgb(249 115 22 / 0.1);
		color: #fb923c;
	}

	.findings-table__provider-pill--azure {
		border-color: rgb(59 130 246 / 0.2);
		background: rgb(59 130 246 / 0.1);
		color: #60a5fa;
	}

	.findings-table__provider-pill--gcp {
		border-color: rgb(234 179 8 / 0.2);
		background: rgb(234 179 8 / 0.1);
		color: #facc15;
	}

	.findings-table__resource-id {
		max-width: 9.375rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: var(--text-xs);
		font-family: var(--font-mono);
	}

	.findings-table__details {
		margin-top: 0.25rem;
	}

	.findings-table__summary {
		cursor: pointer;
		font-size: var(--text-xs);
		color: var(--color-ink-500);
	}

	.findings-table__summary:hover {
		color: var(--color-accent-400);
	}

	.findings-table__explanation {
		max-width: 20rem;
		margin: 0.25rem 0 0;
		font-size: var(--text-xs);
		color: var(--color-ink-400);
	}

	.findings-table__confidence-reason {
		margin: 0.25rem 0 0;
		font-size: var(--text-xs);
		font-style: italic;
		color: var(--color-ink-500);
	}

	.findings-table__type-pill {
		font-size: var(--text-xs);
	}

	.findings-table__gpu-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.125rem 0.375rem;
		border-radius: var(--radius-full);
		background: rgb(239 68 68 / 0.16);
		color: var(--color-danger-400);
		font-size: var(--text-xs);
		font-weight: 700;
		text-transform: uppercase;
		animation: findings-table-pulse 1.4s ease-in-out infinite;
	}

	.findings-table__cost {
		font-weight: 600;
		color: var(--color-success-400);
	}

	.findings-table__confidence {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	.findings-table__confidence-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 999px;
	}

	.findings-table__confidence-dot--high {
		background: var(--color-danger-400);
	}

	.findings-table__confidence-dot--medium {
		background: var(--color-warning-400);
	}

	.findings-table__confidence-dot--low {
		background: var(--color-success-400);
	}

	.findings-table__confidence-label {
		font-size: var(--text-xs);
		text-transform: capitalize;
	}

	.findings-table__muted {
		font-size: var(--text-xs);
		font-style: italic;
		color: var(--color-ink-500);
	}

	.findings-table__owner {
		display: flex;
		flex-direction: column;
	}

	.findings-table__owner-locked {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: var(--text-xs);
		font-weight: 700;
		color: var(--color-warning-400);
	}

	.findings-table__owner-locked-dot {
		width: 0.25rem;
		height: 0.25rem;
		border-radius: 999px;
		background: var(--color-warning-400);
		animation: findings-table-ping 1.2s ease-in-out infinite;
	}

	.findings-table__owner-value {
		max-width: 7.5rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: var(--text-xs);
		color: var(--color-ink-300);
	}

	.findings-table__risk {
		font-size: var(--text-xs);
	}

	.findings-table__risk--high {
		color: var(--color-danger-400);
	}

	.findings-table__risk--medium {
		color: var(--color-warning-400);
	}

	.findings-table__risk--low {
		color: var(--color-ink-400);
	}

	.findings-table__actions {
		display: inline-flex;
		align-items: center;
		justify-content: flex-end;
		gap: 0.5rem;
	}

	.findings-table__icon-button {
		padding: 0.25rem 0.5rem;
		color: var(--color-ink-400);
	}

	.findings-table__icon-button:hover:not(:disabled) {
		color: var(--color-accent-400);
	}

	.findings-table__action-button {
		padding: 0.375rem 0.625rem;
		font-size: var(--text-xs);
	}

	.findings-table__action-button:hover:not(:disabled) {
		background: rgb(6 182 212 / 0.2);
		color: var(--color-accent-400);
	}

	.findings-table__copy-success {
		color: var(--color-success-400);
	}

	.findings-table__action-pending {
		animation: findings-table-pulse 1.2s ease-in-out infinite;
	}

	.findings-table__pagination {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		margin-top: var(--space-4);
		padding-top: var(--space-4);
		border-top: 1px solid var(--color-ink-800);
	}

	.findings-table__pagination-button {
		font-size: var(--text-xs);
	}

	.findings-table__pagination-pages {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	.findings-table__page-button {
		width: 2rem;
		height: 2rem;
		border: none;
		border-radius: var(--radius-md);
		background: transparent;
		color: var(--color-ink-300);
		font-size: var(--text-xs);
		cursor: pointer;
	}

	.findings-table__page-button:hover {
		background: var(--color-ink-700);
	}

	.findings-table__page-button--active {
		background: var(--color-accent-500);
		color: white;
	}

	@media (max-width: 900px) {
		.findings-table__header,
		.findings-table__pagination {
			flex-direction: column;
			align-items: flex-start;
		}

		.findings-table__cell {
			min-width: 7rem;
		}

		.findings-table__cell--actions {
			min-width: 10rem;
		}
	}

	@keyframes findings-table-pulse {
		0%,
		100% {
			opacity: 1;
		}

		50% {
			opacity: 0.5;
		}
	}

	@keyframes findings-table-ping {
		0% {
			transform: scale(1);
			opacity: 1;
		}

		100% {
			transform: scale(1.8);
			opacity: 0;
		}
	}
</style>
