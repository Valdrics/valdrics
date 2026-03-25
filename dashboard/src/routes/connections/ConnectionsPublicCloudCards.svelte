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

	const canUseMultiCloudFeatures = $derived(
		['starter', 'growth', 'pro', 'enterprise'].includes(data?.subscription?.tier ?? '')
	);
	const starterUpgradePrompt = getUpgradePrompt('starter', 'Azure and GCP coverage');
</script>

<!-- AWS -->
<div class="glass-panel stagger-enter connections-provider-card connections-card-delay-0">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="aws" size={40} />
			<div>
				<h3 class="connections-card__title">AWS</h3>
				<p class="connections-card__subtitle">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingAWS}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if awsConnections.length > 0}
			<span class="badge badge-success connections-card__status"
				>Active ({awsConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if awsConnections.length > 0}
		<div class="connections-list">
			{#each awsConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__eyebrow">
								<span class="connections-record__mono">ID: {conn.aws_account_id}</span>
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
							class="connections-delete-button"
							onclick={() => deleteConnection('aws', conn.id)}
							title="Delete Connection"
						>
							<span>🗑️</span>
						</button>
					</div>

					{#if conn.organization_id}
						<div class="connections-record__detail">
							<span class="connections-record__label">Organization:</span>
							<span class="connections-record__value connections-record__value--mono">
								{conn.organization_id}
							</span>
						</div>
					{/if}
				</div>
			{/each}
		</div>
		<a href={`${base}/onboarding`} class="btn btn-ghost connections-card__secondary-link">
			<span>➕</span> Add Another Account
		</a>
	{:else if !loadingAWS}
		<p class="connections-card__empty-copy">
			Establish a secure connection using our 1-click CloudFormation template.
		</p>
		<a href={`${base}/onboarding`} class="btn btn-primary connections-submit">Connect AWS</a>
	{/if}
</div>

<!-- Azure -->
<div class="glass-panel stagger-enter connections-provider-card connections-card-delay-1">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="azure" size={40} />
			<div>
				<h3 class="connections-card__title">Azure</h3>
				<p class="connections-card__subtitle">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingAzure}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if azureConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Secure ({azureConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if azureConnections.length > 0}
		<div class="connections-list">
			{#each azureConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__secondary">
								<span class="connections-record__mono"
									>Sub ID: {conn.subscription_id
										? `${conn.subscription_id.slice(0, 8)}...`
										: 'N/A'}</span
								>
							</div>
						</div>

						<button
							type="button"
							class="connections-delete-button"
							onclick={() => deleteConnection('azure', conn.id)}
							title="Delete Connection"
						>
							<span>🗑️</span>
						</button>
					</div>
					<div class="connections-record__detail">
						<span class="connections-record__label">Auth Strategy:</span>
						<span class="connections-record__value connections-record__value--accent">
							Identity Federation
						</span>
					</div>
				</div>
			{/each}
		</div>
		<a href={`${base}/onboarding`} class="btn btn-ghost connections-card__secondary-link">
			<span>➕</span> Add Another Subscription
		</a>
	{:else if !loadingAzure}
		<p class="connections-card__empty-copy">
			Connect via Workload Identity Federation for secret-less security.
		</p>
		{#if canUseMultiCloudFeatures}
			<a href={`${base}/onboarding`} class="btn btn-primary connections-submit">Connect Azure</a>
		{:else}
			<div class="connections-upgrade-stack">
				<a href={`${base}/billing`} class="btn btn-secondary connections-submit">
					{starterUpgradePrompt.cta}
				</a>
				<span class="badge badge-warning connections-upgrade-badge"
					>{starterUpgradePrompt.badge}</span
				>
				<p class="connections-upgrade-copy">{starterUpgradePrompt.body}</p>
			</div>
		{/if}
	{/if}
</div>

<!-- GCP -->
<div class="glass-panel stagger-enter connections-provider-card connections-card-delay-2">
	<div class="connections-card__header">
		<div class="connections-card__identity">
			<CloudLogo provider="gcp" size={40} />
			<div>
				<h3 class="connections-card__title">GCP</h3>
				<p class="connections-card__subtitle">Public Cloud Provider</p>
			</div>
		</div>
		{#if loadingGCP}
			<div class="skeleton w-4 h-4 rounded-full"></div>
		{:else if gcpConnections.length > 0}
			<span class="badge badge-accent connections-card__status"
				>Secure ({gcpConnections.length})</span
			>
		{:else}
			<span class="badge badge-default connections-card__status">Disconnected</span>
		{/if}
	</div>

	{#if gcpConnections.length > 0}
		<div class="connections-list">
			{#each gcpConnections as conn (conn.id)}
				<div class="connections-record">
					<div class="connections-record__header">
						<div class="connections-record__meta">
							<div class="connections-record__secondary">
								<span class="connections-record__mono">Project: {conn.project_id}</span>
							</div>
						</div>

						<button
							type="button"
							class="connections-delete-button"
							onclick={() => deleteConnection('gcp', conn.id)}
							title="Delete Connection"
						>
							<span>🗑️</span>
						</button>
					</div>
					<div class="connections-record__detail">
						<span class="connections-record__label">Auth Method:</span>
						<span
							class="connections-record__value connections-record__value--accent connections-record__value--capitalize"
						>
							{conn.auth_method ? conn.auth_method.replace('_', ' ') : 'unknown'}
						</span>
					</div>
				</div>
			{/each}
		</div>
		<a href={`${base}/onboarding`} class="btn btn-ghost connections-card__secondary-link">
			<span>➕</span> Add Another Project
		</a>
	{:else if !loadingGCP}
		<p class="connections-card__empty-copy">
			Seamless integration using GCP Workload Identity pools.
		</p>
		{#if canUseMultiCloudFeatures}
			<a href={`${base}/onboarding`} class="btn btn-primary connections-submit">Connect GCP</a>
		{:else}
			<div class="connections-upgrade-stack">
				<a href={`${base}/billing`} class="btn btn-secondary connections-submit">
					{starterUpgradePrompt.cta}
				</a>
				<span class="badge badge-warning connections-upgrade-badge"
					>{starterUpgradePrompt.badge}</span
				>
				<p class="connections-upgrade-copy">{starterUpgradePrompt.body}</p>
			</div>
		{/if}
	{/if}
</div>
