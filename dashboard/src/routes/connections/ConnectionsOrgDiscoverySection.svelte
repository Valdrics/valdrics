<script lang="ts">
	import { base } from '$app/paths';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';

	interface CloudConnection {
		is_management_account?: boolean;
		organization_id?: string;
	}

	interface DiscoveredAccount {
		id: string;
		account_id: string;
		name: string;
		email: string;
		status: 'discovered' | 'linked';
	}

	type AsyncAction = () => void | Promise<void>;
	type AccountAction = (discoveredId: string) => void | Promise<void>;

	interface Props extends Record<string, unknown> {
		data: {
			subscription?: {
				tier?: string;
			};
		};
		awsConnection: CloudConnection | null;
		syncingOrg: boolean;
		discoveredAccounts: DiscoveredAccount[];
		loadingDiscovered: boolean;
		linkingAccount: string | null;
		syncAWSOrg: AsyncAction;
		linkDiscoveredAccount: AccountAction;
	}

	let {
		data,
		awsConnection,
		syncingOrg,
		discoveredAccounts,
		loadingDiscovered,
		linkingAccount,
		syncAWSOrg,
		linkDiscoveredAccount
	}: Props = $props();

	const growthTier = $derived(
		['growth', 'pro', 'enterprise'].includes(data.subscription?.tier ?? '')
	);
	const linkedCount = $derived(
		discoveredAccounts.filter((account) => account.status === 'linked').length
	);
	const pendingCount = $derived(
		discoveredAccounts.filter((account) => account.status === 'discovered').length
	);
	const growthUpgradePrompt = getUpgradePrompt('growth', 'AWS organization discovery');
</script>

{#if awsConnection?.is_management_account}
	<div class="card stagger-enter connections-org" class:connections-org--locked={!growthTier}>
		<div class="connections-org__halo">🏢</div>

		<div class="connections-org__content">
			<div class="connections-org__header">
				<div>
					<h2 class="connections-org__title">
						<span>🏢</span> AWS Organizations Hub
					</h2>
					<p class="connections-org__subtitle">
						Managing Organization:
						<span class="connections-org__org-id">{awsConnection.organization_id || 'Global'}</span>
					</p>
				</div>

				<div>
					{#if !growthTier}
						<span class="badge badge-warning">{growthUpgradePrompt.badge}</span>
					{:else}
						<button
							type="button"
							class="btn btn-primary connections-org__sync-button"
							onclick={syncAWSOrg}
							disabled={syncingOrg}
						>
							{#if syncingOrg}
								<div class="spinner"></div>
								<span>Syncing...</span>
							{:else}
								<span>🔄</span>
								<span>Sync Accounts</span>
							{/if}
						</button>
					{/if}
				</div>
			</div>

			{#if !growthTier}
				<div class="glass-panel connections-org__locked-panel">
					<div class="connections-org__locked-icon">🔒</div>
					<h3 class="connections-org__locked-title">{growthUpgradePrompt.heading}</h3>
					<p class="connections-org__locked-copy">{growthUpgradePrompt.body}</p>
					<p class="connections-org__locked-footnote">{growthUpgradePrompt.footnote}</p>
					<a href={`${base}/billing`} class="btn btn-primary connections-org__locked-cta">
						{growthUpgradePrompt.cta}
					</a>
				</div>
			{:else}
				<div class="connections-org__metrics">
					<div class="card connections-org__metric">
						<p class="connections-org__metric-label">Total Discovered</p>
						<p class="connections-org__metric-value">{discoveredAccounts.length}</p>
					</div>
					<div class="card connections-org__metric">
						<p class="connections-org__metric-label">Linked Accounts</p>
						<p class="connections-org__metric-value connections-org__metric-value--success">
							{linkedCount}
						</p>
					</div>
					<div class="card connections-org__metric">
						<p class="connections-org__metric-label">Pending Link</p>
						<p class="connections-org__metric-value connections-org__metric-value--warning">
							{pendingCount}
						</p>
					</div>
					<div class="card connections-org__metric">
						<p class="connections-org__metric-label">Org Status</p>
						<p class="connections-org__metric-value connections-org__metric-value--accent">
							Synced
						</p>
					</div>
				</div>

				{#if loadingDiscovered}
					<div class="space-y-4">
						<div class="skeleton h-12 w-full"></div>
						<div class="skeleton h-12 w-full"></div>
						<div class="skeleton h-12 w-full"></div>
					</div>
				{:else if discoveredAccounts.length > 0}
					<div class="connections-org__table-wrap">
						<table class="connections-org__table">
							<thead>
								<tr>
									<th>Account Details</th>
									<th>Email</th>
									<th>Status</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody>
								{#each discoveredAccounts as acc (acc.id)}
									<tr>
										<td>
											<div class="connections-org__account-name">
												{acc.name || 'Unnamed Account'}
											</div>
											<div class="connections-org__account-id">{acc.account_id}</div>
										</td>
										<td class="connections-org__email">{acc.email || '-'}</td>
										<td>
											<div
												class="connections-org__status-pill"
												class:connections-org__status-pill--linked={acc.status === 'linked'}
											>
												<span
													class="connections-org__status-dot"
													class:connections-org__status-dot--linked={acc.status === 'linked'}
												></span>
												{acc.status}
											</div>
										</td>
										<td>
											{#if acc.status === 'discovered'}
												<button
													type="button"
													class="btn btn-ghost connections-org__action"
													onclick={() => linkDiscoveredAccount(acc.id)}
													disabled={linkingAccount === acc.id}
												>
													{linkingAccount === acc.id ? 'Connecting...' : 'Link Account →'}
												</button>
											{:else}
												<span class="connections-org__linked-copy">✓ Linked</span>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="connections-org__empty-state">
						<div class="connections-org__empty-icon">🔍</div>
						<h3 class="connections-org__empty-title">No Member Accounts Found</h3>
						<p class="connections-org__empty-copy">
							We couldn't find any member accounts. Run a sync to scan your Organization.
						</p>
						<button
							type="button"
							class="btn btn-primary connections-org__empty-cta"
							onclick={syncAWSOrg}
						>
							Start Organizational Scan
						</button>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
