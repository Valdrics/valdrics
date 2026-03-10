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

	interface Props {
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
	<div
		class="card stagger-enter mt-12 border-accent-500/30 bg-accent-500/5 relative overflow-hidden"
		class:opacity-60={!growthTier}
	>
		<div class="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
			<span class="text-9xl">🏢</span>
		</div>

		<div class="relative z-10">
			<div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
				<div>
					<h2 class="text-2xl font-bold flex items-center gap-2 mb-1">
						<span>🏢</span> AWS Organizations Hub
					</h2>
					<p class="text-sm text-ink-400">
						Managing Organization: <span class="text-accent-400 font-mono"
							>{awsConnection.organization_id || 'Global'}</span
						>
					</p>
				</div>

				<div class="flex items-center gap-3">
					{#if !growthTier}
						<span class="badge badge-warning">{growthUpgradePrompt.badge}</span>
					{:else}
						<button
							type="button"
							class="btn btn-primary !w-auto flex items-center gap-2"
							onclick={syncAWSOrg}
							disabled={syncingOrg}
						>
							{#if syncingOrg}
								<div
									class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
								></div>
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
				<div class="py-20 text-center glass-panel bg-black/20 border-white/5">
					<div class="mb-6 text-5xl">🔒</div>
					<h3 class="text-xl font-bold mb-2">{growthUpgradePrompt.heading}</h3>
					<p class="text-ink-400 max-w-xl mx-auto mb-3">{growthUpgradePrompt.body}</p>
					<p class="text-xs text-ink-500 max-w-xl mx-auto mb-8">
						{growthUpgradePrompt.footnote}
					</p>
					<a href={`${base}/billing`} class="btn btn-primary !w-auto px-8 py-3">
						{growthUpgradePrompt.cta}
					</a>
				</div>
			{:else}
				<div class="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
					<div class="card bg-ink-900/50 p-4 border-ink-800">
						<p class="text-xs text-ink-500 mb-1">Total Discovered</p>
						<p class="text-2xl font-bold">{discoveredAccounts.length}</p>
					</div>
					<div class="card bg-ink-900/50 p-4 border-ink-800">
						<p class="text-xs text-ink-500 mb-1">Linked Accounts</p>
						<p class="text-2xl font-bold text-success-400">{linkedCount}</p>
					</div>
					<div class="card bg-ink-900/50 p-4 border-ink-800">
						<p class="text-xs text-ink-500 mb-1">Pending Link</p>
						<p class="text-2xl font-bold text-warning-400">{pendingCount}</p>
					</div>
					<div class="card bg-ink-900/50 p-4 border-ink-800">
						<p class="text-xs text-ink-500 mb-1">Org Status</p>
						<p class="text-2xl font-bold text-accent-400">Synced</p>
					</div>
				</div>

				{#if loadingDiscovered}
					<div class="space-y-4">
						<div class="skeleton h-12 w-full"></div>
						<div class="skeleton h-12 w-full"></div>
						<div class="skeleton h-12 w-full"></div>
					</div>
				{:else if discoveredAccounts.length > 0}
					<div class="overflow-x-auto rounded-xl border border-ink-800">
						<table class="w-full text-sm text-left">
							<thead class="bg-ink-900/80 text-ink-400 uppercase text-xs tracking-wider">
								<tr>
									<th class="px-6 py-4 font-semibold uppercase">Account Details</th>
									<th class="px-6 py-4 font-semibold uppercase">Email</th>
									<th class="px-6 py-4 font-semibold uppercase">Status</th>
									<th class="px-6 py-4 font-semibold uppercase text-right">Action</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-ink-800">
								{#each discoveredAccounts as acc (acc.id)}
									<tr class="hover:bg-accent-500/5 transition-colors">
										<td class="px-6 py-4">
											<div class="font-bold mb-0.5">{acc.name || 'Unnamed Account'}</div>
											<div class="text-xs font-mono text-ink-500">{acc.account_id}</div>
										</td>
										<td class="px-6 py-4 text-ink-400">{acc.email || '-'}</td>
										<td class="px-6 py-4">
											<div
												class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium
                          {acc.status === 'linked'
													? 'bg-success-500/10 text-success-400 border border-success-500/20'
													: 'bg-ink-800 text-ink-400 border border-ink-700'}"
											>
												<span
													class="w-1.5 h-1.5 rounded-full {acc.status === 'linked'
														? 'bg-success-400'
														: 'bg-ink-500'}"
												></span>
												{acc.status}
											</div>
										</td>
										<td class="px-6 py-4 text-right">
											{#if acc.status === 'discovered'}
												<button
													type="button"
													class="btn btn-ghost btn-sm text-accent-400 hover:text-accent-300 hover:bg-accent-400/10"
													onclick={() => linkDiscoveredAccount(acc.id)}
													disabled={linkingAccount === acc.id}
												>
													{linkingAccount === acc.id ? 'Connecting...' : 'Link Account →'}
												</button>
											{:else}
												<span class="text-success-400 font-medium">✓ Linked</span>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div
						class="py-16 text-center border-2 border-dashed border-ink-800 rounded-3xl bg-ink-900/20"
					>
						<div class="text-5xl mb-4">🔍</div>
						<h3 class="text-xl font-bold mb-2">No Member Accounts Found</h3>
						<p class="text-ink-500 max-w-sm mx-auto mb-6">
							We couldn't find any member accounts. Run a sync to scan your Organization.
						</p>
						<button type="button" class="btn btn-primary !w-auto px-8" onclick={syncAWSOrg}>
							Start Organizational Scan
						</button>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
