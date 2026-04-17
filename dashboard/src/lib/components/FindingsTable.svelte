<script lang="ts">
	import CloudLogo from './CloudLogo.svelte';
	import { Terminal, Check } from '@lucide/svelte';
	import { clientLogger } from '$lib/logging/client';
	import { createLazyComponent } from '$lib/lazyComponent';
	import './FindingsTable.css';

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

	type FindingsTableDetailBodyProps = {
		explanation: string;
		confidenceReason?: string;
	};

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
	let detailsModuleReady = $state(import.meta.env.MODE === 'test');
	const pageSize = 10;
	const loadFindingsTableDetailBody = createLazyComponent<FindingsTableDetailBodyProps>(
		() => import('./FindingsTableDetailBody.svelte')
	);

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

	function ensureDetailsModule(): void {
		detailsModuleReady = true;
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
								<span
									>{finding.provider === 'aws'
										? 'AWS'
										: finding.provider === 'azure'
											? 'Azure'
											: 'GCP'}</span
								>
							</div>
						</td>
						<td class="findings-table__cell">
							<div class="findings-table__resource-id" title={finding.resource_id}>
								{finding.resource_id}
							</div>
							<details
								class="findings-table__details"
								ontoggle={(event) => {
									if ((event.currentTarget as HTMLDetailsElement).open) {
										ensureDetailsModule();
									}
								}}
							>
								<summary class="findings-table__summary">View details</summary>
								{#if detailsModuleReady}
									{#await loadFindingsTableDetailBody() then module}
										{@const FindingsTableDetailBody = module.default}
										<FindingsTableDetailBody
											explanation={finding.explanation}
											confidenceReason={finding.confidence_reason}
										/>
									{:catch}
										<p class="findings-table__confidence-reason">
											Details are temporarily unavailable.
										</p>
									{/await}
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
									<span
										class={`findings-table__confidence-dot ${confidenceTone(finding.confidence)}`}
									></span>
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
