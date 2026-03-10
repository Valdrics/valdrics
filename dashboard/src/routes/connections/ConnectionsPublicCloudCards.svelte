<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';

	let {
		data,
		loadingAWS,
		loadingAzure,
		loadingGCP,
		awsConnections,
		azureConnections,
		gcpConnections,
		deleteConnection
	} = $props();

	const growthUpgradePrompt = getUpgradePrompt('growth', 'Azure and GCP coverage');
</script>

<!-- AWS -->
<div class="glass-panel stagger-enter" style="animation-delay: 0ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="aws" size={40} />
			<div>
				<h3 class="font-bold text-lg">AWS</h3>
				<p class="text-xs text-ink-500">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingAWS}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if awsConnections.length > 0}
			<span class="badge badge-success">Active ({awsConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if awsConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each awsConnections as conn (conn.id)}
				<div
					class="p-3 rounded-xl bg-ink-900/50 border border-ink-800 group relative overflow-hidden"
				>
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs text-ink-500 font-mono">ID: {conn.aws_account_id}</span>
								<span
									class="badge {conn.is_management_account
										? 'badge-accent'
										: 'badge-default'} text-xs px-1.5 py-0.5"
								>
									{conn.is_management_account ? 'Management' : 'Member'}
								</span>
							</div>
						</div>

						<button
							type="button"
							class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
							onclick={() => deleteConnection('aws', conn.id)}
							title="Delete Connection"
						>
							<span class="text-xs">🗑️</span>
						</button>
					</div>

					{#if conn.organization_id}
						<div class="flex justify-between text-xs">
							<span class="text-ink-500">Organization:</span>
							<span class="text-ink-300 font-mono">{conn.organization_id}</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
		<a
			href={`${base}/onboarding`}
			class="btn btn-ghost text-xs w-full border-dashed border-ink-800 hover:border-accent-500/50"
		>
			<span>➕</span> Add Another Account
		</a>
	{:else if !loadingAWS}
		<p class="text-xs text-ink-400 mb-6">
			Establish a secure connection using our 1-click CloudFormation template.
		</p>
		<a href={`${base}/onboarding`} class="btn btn-primary text-xs w-full">Connect AWS</a>
	{/if}
</div>

<!-- Azure -->
<div class="glass-panel stagger-enter" style="animation-delay: 100ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="azure" size={40} />
			<div>
				<h3 class="font-bold text-lg">Azure</h3>
				<p class="text-xs text-ink-500">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingAzure}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if azureConnections.length > 0}
			<span class="badge badge-accent">Secure ({azureConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if azureConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each azureConnections as conn (conn.id)}
				<div
					class="p-3 rounded-xl bg-ink-900/50 border border-ink-800 group relative overflow-hidden"
				>
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs text-ink-500 font-mono"
									>Sub ID: {conn.subscription_id
										? `${conn.subscription_id.slice(0, 8)}...`
										: 'N/A'}</span
								>
							</div>
						</div>

						<button
							type="button"
							class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
							onclick={() => deleteConnection('azure', conn.id)}
							title="Delete Connection"
						>
							<span class="text-xs">🗑️</span>
						</button>
					</div>
					<div class="flex justify-between text-xs">
						<span class="text-ink-500">Auth Strategy:</span>
						<span class="text-accent-400">Identity Federation</span>
					</div>
				</div>
			{/each}
		</div>
		<a
			href={`${base}/onboarding`}
			class="btn btn-ghost text-xs w-full border-dashed border-ink-800 hover:border-accent-500/50"
		>
			<span>➕</span> Add Another Subscription
		</a>
	{:else if !loadingAzure}
		<p class="text-xs text-ink-400 mb-6">
			Connect via Workload Identity Federation for secret-less security.
		</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full">
				{growthUpgradePrompt.cta}
			</a>
			<span class="badge badge-warning text-xs w-full justify-center"
				>{growthUpgradePrompt.badge}</span
			>
			<p class="text-[11px] leading-relaxed text-ink-500">{growthUpgradePrompt.body}</p>
		</div>
	{/if}
</div>

<!-- GCP -->
<div class="glass-panel stagger-enter" style="animation-delay: 200ms;">
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<CloudLogo provider="gcp" size={40} />
			<div>
				<h3 class="font-bold text-lg">GCP</h3>
				<p class="text-xs text-ink-500">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingGCP}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if gcpConnections.length > 0}
			<span class="badge badge-accent">Secure ({gcpConnections.length})</span>
		{:else}
			<span class="badge badge-default">Disconnected</span>
		{/if}
	</div>

	{#if gcpConnections.length > 0}
		<div class="space-y-4 mb-6">
			{#each gcpConnections as conn (conn.id)}
				<div
					class="p-3 rounded-xl bg-ink-900/50 border border-ink-800 group relative overflow-hidden"
				>
					<div class="flex justify-between items-start mb-2">
						<div>
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs text-ink-500 font-mono">Project: {conn.project_id}</span>
							</div>
						</div>

						<button
							type="button"
							class="p-1.5 rounded-lg bg-danger-500/10 text-danger-400 hover:bg-danger-500 hover:text-white transition-all shadow-sm"
							onclick={() => deleteConnection('gcp', conn.id)}
							title="Delete Connection"
						>
							<span class="text-xs">🗑️</span>
						</button>
					</div>
					<div class="flex justify-between text-xs">
						<span class="text-ink-500">Auth Method:</span>
						<span class="text-accent-400 capitalize"
							>{conn.auth_method ? conn.auth_method.replace('_', ' ') : 'unknown'}</span
						>
					</div>
				</div>
			{/each}
		</div>
		<a
			href={`${base}/onboarding`}
			class="btn btn-ghost text-xs w-full border-dashed border-ink-800 hover:border-accent-500/50"
		>
			<span>➕</span> Add Another Project
		</a>
	{:else if !loadingGCP}
		<p class="text-xs text-ink-400 mb-6">Seamless integration using GCP Workload Identity pools.</p>
		<div class="flex flex-col gap-2">
			<a href={`${base}/billing`} class="btn btn-secondary text-xs w-full">
				{growthUpgradePrompt.cta}
			</a>
			<span class="badge badge-warning text-xs w-full justify-center"
				>{growthUpgradePrompt.badge}</span
			>
			<p class="text-[11px] leading-relaxed text-ink-500">{growthUpgradePrompt.body}</p>
		</div>
	{/if}
</div>
