<script lang="ts">
	import { base } from '$app/paths';
	import CloudLogo from '$lib/components/CloudLogo.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';

	let {
		data,
		selectedProvider = $bindable(),
		discoveryEmail = $bindable(),
		discoveryDomain,
		discoveryIdpProvider = $bindable(),
		discoveryCandidates,
		discoveryWarnings,
		discoveryLoadingStageA,
		discoveryLoadingStageB,
		discoveryActionCandidateId,
		discoveryError,
		discoveryInfo,
		isLoading,
		canUseMultiCloudFeatures,
		canUseCloudPlusFeatures,
		canUseIdpDeepScan,
		getDiscoveryCategoryLabel,
		formatDiscoveryConfidence,
		runDiscoveryStageA,
		runDiscoveryStageB,
		connectDiscoveryCandidate,
		ignoreDiscoveryCandidate,
		markDiscoveryCandidateConnected,
		handleContinueToSetup
	} = $props();

	const starterUpgradePrompt = getUpgradePrompt('starter', 'Azure and GCP coverage');
	const proUpgradePrompt = getUpgradePrompt('pro', 'Cloud+ connectors');
	const idpDeepScanPrompt = getUpgradePrompt('pro', 'IdP deep scan');
	const selectedProviderUpgradePrompt = $derived(
		(selectedProvider === 'azure' || selectedProvider === 'gcp') &&
		!canUseMultiCloudFeatures()
			? starterUpgradePrompt
			: (selectedProvider === 'saas' || selectedProvider === 'license') &&
				  !canUseCloudPlusFeatures()
				? proUpgradePrompt
				: null
	);
</script>

<div class="step-content">
	<h2>Choose Your Cloud Provider</h2>
	<p class="text-muted mb-8">
		Valdrics uses read-only access to analyze your infrastructure and find waste.
	</p>

	<div class="provider-grid">
		<button
			type="button"
			class="provider-card"
			class:selected={selectedProvider === 'aws'}
			onclick={() => (selectedProvider = 'aws')}
		>
			<div class="logo-circle">
				<CloudLogo provider="aws" size={32} />
			</div>
			<h3>Amazon Web Services</h3>
			<p>Standard across all tiers</p>
		</button>

		<button
			type="button"
			class="provider-card"
			class:selected={selectedProvider === 'azure'}
			onclick={() => (selectedProvider = 'azure')}
		>
			<div class="logo-circle">
				<CloudLogo provider="azure" size={32} />
			</div>
			<h3>Microsoft Azure</h3>
			<span class="badge">Starter Plan+</span>
		</button>

		<button
			type="button"
			class="provider-card"
			class:selected={selectedProvider === 'gcp'}
			onclick={() => (selectedProvider = 'gcp')}
		>
			<div class="logo-circle">
				<CloudLogo provider="gcp" size={32} />
			</div>
			<h3>Google Cloud</h3>
			<span class="badge">Starter Plan+</span>
		</button>

		<button
			type="button"
			class="provider-card"
			class:selected={selectedProvider === 'saas'}
			onclick={() => (selectedProvider = 'saas')}
		>
			<div class="logo-circle">
				<CloudLogo provider="saas" size={32} />
			</div>
			<h3>SaaS Spend Connector</h3>
			<span class="badge">Pro Plan+</span>
		</button>

		<button
			type="button"
			class="provider-card"
			class:selected={selectedProvider === 'license'}
			onclick={() => (selectedProvider = 'license')}
		>
			<div class="logo-circle">
				<CloudLogo provider="license" size={32} />
			</div>
			<h3>License / ITAM Connector</h3>
			<span class="badge">Pro Plan+</span>
		</button>
	</div>

	<div class="discovery-panel mt-8">
		<div class="discovery-header">
			<h3>Discovery Wizard (Prefill)</h3>
			<p class="text-xs text-ink-400">
				Best-effort signals to find likely providers first, then choose what to connect.
			</p>
		</div>

		<div class="discovery-stage-a">
			<div class="form-group">
				<label for="discoveryEmail">Work Email</label>
				<input
					type="email"
					id="discoveryEmail"
					bind:value={discoveryEmail}
					placeholder="you@company.com"
				/>
			</div>
			<div class="discovery-actions">
				<button
					type="button"
					class="secondary-btn !w-auto px-4"
					onclick={runDiscoveryStageA}
					disabled={discoveryLoadingStageA || isLoading}
				>
					{discoveryLoadingStageA ? '⏳ Running Stage A...' : 'Run Stage A'}
				</button>
				{#if discoveryDomain}
					<span class="text-xs text-ink-400">Domain: {discoveryDomain}</span>
				{/if}
			</div>
		</div>

		<div class="discovery-stage-b">
			<div class="form-group">
				<label for="idpProvider">IdP Deep Scan (Stage B)</label>
				<select id="idpProvider" bind:value={discoveryIdpProvider}>
					<option value="microsoft_365">microsoft_365</option>
					<option value="google_workspace">google_workspace</option>
				</select>
			</div>
			<div class="discovery-actions">
				<button
					type="button"
					class="secondary-btn !w-auto px-4"
					onclick={runDiscoveryStageB}
					disabled={discoveryLoadingStageB || isLoading || !canUseIdpDeepScan()}
				>
					{discoveryLoadingStageB ? '⏳ Running Stage B...' : 'Run Stage B'}
				</button>
				{#if !canUseIdpDeepScan()}
					<span class="text-xs text-ink-500">{idpDeepScanPrompt.badge}</span>
				{/if}
			</div>
		</div>

		{#if discoveryError}
			<p class="discovery-error">{discoveryError}</p>
		{/if}
		{#if discoveryInfo}
			<p class="discovery-info">{discoveryInfo}</p>
		{/if}
		{#if discoveryWarnings.length > 0}
			<div class="discovery-warnings">
				<p class="text-xs text-ink-400 mb-2">Warnings</p>
				<ul>
					{#each discoveryWarnings.slice(0, 3) as warning (warning)}
						<li>{warning}</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if discoveryCandidates.length > 0}
			<div class="candidate-list">
				{#each discoveryCandidates as candidate (candidate.id)}
					<div class="candidate-row">
						<div class="candidate-main">
							<div class="candidate-title">
								<strong>{candidate.provider}</strong>
								<span class="candidate-pill">{getDiscoveryCategoryLabel(candidate.category)}</span>
								<span class="candidate-pill status">{candidate.status}</span>
							</div>
							<p class="candidate-meta">
								Confidence: {formatDiscoveryConfidence(candidate.confidence_score)} · Source: {candidate.source}
								{#if candidate.connection_target}
									· Target: {candidate.connection_target}
								{/if}
							</p>
						</div>
						<div class="candidate-actions">
							<button
								type="button"
								class="secondary-btn !w-auto px-3 py-1.5 text-xs"
								onclick={() => connectDiscoveryCandidate(candidate)}
								disabled={discoveryActionCandidateId === candidate.id ||
									candidate.status === 'connected'}
							>
								{candidate.status === 'connected' ? 'Connected' : 'Connect'}
							</button>
							<button
								type="button"
								class="secondary-btn !w-auto px-3 py-1.5 text-xs"
								onclick={() => ignoreDiscoveryCandidate(candidate)}
								disabled={discoveryActionCandidateId === candidate.id ||
									candidate.status === 'ignored'}
							>
								Ignore
							</button>
							<button
								type="button"
								class="secondary-btn !w-auto px-3 py-1.5 text-xs"
								onclick={() => markDiscoveryCandidateConnected(candidate)}
								disabled={discoveryActionCandidateId === candidate.id ||
									candidate.status === 'connected'}
							>
								Mark Connected
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	{#if selectedProviderUpgradePrompt}
		<div class="mt-8 rounded-2xl border border-ink-800 bg-ink-950/40 p-5 space-y-3">
			<span class="badge badge-warning">{selectedProviderUpgradePrompt.badge}</span>
			<h3 class="text-lg font-semibold text-white">{selectedProviderUpgradePrompt.heading}</h3>
			<p class="text-sm text-ink-300">{selectedProviderUpgradePrompt.body}</p>
			<p class="text-xs text-ink-500">{selectedProviderUpgradePrompt.footnote}</p>
			<a href={`${base}/billing`} class="primary-btn mt-2">{selectedProviderUpgradePrompt.cta}</a>
		</div>
	{:else}
		<button type="button" class="primary-btn mt-8" onclick={handleContinueToSetup}
			>Continue to Setup →</button
		>
	{/if}
</div>
