<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import IdentitySsoSection from '$lib/components/identity/IdentitySsoSection.svelte';
	import { createLazyComponent } from '$lib/lazyComponent';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import { isGrowthPlus } from '$lib/components/identity/identitySettingsHelpers';
	import {
		IDENTITY_REQUEST_TIMEOUT_MS,
		uniqueScimMappingsOrThrow
	} from '$lib/components/identity/identitySettingsModel';
	import type { IdentitySettings } from '$lib/components/identity/identitySettingsTypes';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { clientLogger } from '$lib/logging/client';
	import { formatValidationIssues } from '$lib/validation/clientZod';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();

	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let success = $state('');

	let settings = $state<IdentitySettings | null>(null);
	let domainsText = $state('');
	let advancedSectionsReady = $state(import.meta.env.MODE === 'test');

	type IdentityDiagnosticsSectionProps = {
		accessToken?: string | null;
		tier?: string | null;
	};

	type IdentityScimSectionProps = {
		accessToken?: string | null;
		tier?: string | null;
		settings: IdentitySettings;
	};

	const loadIdentityDiagnosticsSection = createLazyComponent<IdentityDiagnosticsSectionProps>(
		() => import('$lib/components/identity/IdentityDiagnosticsSection.svelte')
	);
	const loadIdentityScimSection = createLazyComponent<IdentityScimSectionProps>(
		() => import('$lib/components/identity/IdentityScimSection.svelte')
	);
	let identityRuntimePromise: Promise<
		typeof import('$lib/components/identity/identitySettingsRuntime')
	> | null = null;

	function loadIdentityRuntime() {
		if (!identityRuntimePromise) {
			identityRuntimePromise = import('$lib/components/identity/identitySettingsRuntime');
		}
		return identityRuntimePromise;
	}

	async function loadIdentitySettings() {
		loading = true;
		error = '';
		success = '';
		try {
			if (!accessToken || !isGrowthPlus(tier)) {
				settings = null;
				domainsText = '';
				return;
			}
			const { loadIdentitySettingsState } = await loadIdentityRuntime();
			const nextState = await loadIdentitySettingsState(accessToken, IDENTITY_REQUEST_TIMEOUT_MS);
			settings = nextState.settings;
			domainsText = nextState.domainsText;
		} catch (e) {
			clientLogger.error('Failed to load identity settings:', e);
			error =
				e instanceof TimeoutError
					? 'Identity settings request timed out. Try again.'
					: formatValidationIssues(e, false);
		} finally {
			loading = false;
		}
	}

	async function saveIdentitySettings() {
		if (!settings) return;
		saving = true;
		error = '';
		success = '';
		try {
			uniqueScimMappingsOrThrow(settings.scim_group_mappings ?? []);
			if (!accessToken) {
				throw new Error('Missing access token');
			}
			const { saveIdentitySettingsState } = await loadIdentityRuntime();
			const nextState = await saveIdentitySettingsState(accessToken, settings, domainsText);
			settings = nextState.settings;
			domainsText = nextState.domainsText;
			success = 'Identity settings saved.';
			setTimeout(() => (success = ''), 2500);
		} catch (e) {
			error = formatValidationIssues(e, false);
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		void loadIdentitySettings();

		if (advancedSectionsReady) {
			return;
		}

		const activateAdvancedSections = () => {
			advancedSectionsReady = true;
		};

		if (typeof window.requestIdleCallback === 'function') {
			const idleId = window.requestIdleCallback(activateAdvancedSections, { timeout: 1200 });
			return () => window.cancelIdleCallback(idleId);
		}

		const timeoutId = window.setTimeout(activateAdvancedSections, 500);
		return () => window.clearTimeout(timeoutId);
	});

	const upgradePrompt = getUpgradePrompt('growth', 'identity controls');
</script>

<div
	class="card stagger-enter relative"
	class:opacity-60={!isGrowthPlus(tier)}
	class:pointer-events-none={!isGrowthPlus(tier)}
>
	<div class="flex items-center justify-between mb-5">
		<h2 class="text-lg font-semibold flex items-center gap-2">
			<span>🔐</span> Identity (SSO/SCIM)
		</h2>

		{#if !isGrowthPlus(tier)}
			<span class="badge badge-warning text-xs">Growth Plan Required</span>
		{/if}
	</div>

	{#if !isGrowthPlus(tier)}
		<div
			class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-ink-950/55 px-6 text-center"
		>
			<div class="max-w-md space-y-3 pointer-events-auto">
				<h3 class="text-lg font-semibold text-white">{upgradePrompt.heading}</h3>
				<p class="text-sm text-ink-300">{upgradePrompt.body}</p>
				<p class="text-xs text-ink-500">{upgradePrompt.footnote}</p>
				<a href={`${base}/billing`} class="btn btn-primary shadow-lg">{upgradePrompt.cta}</a>
			</div>
		</div>
	{/if}

	{#if error}
		<div role="alert" class="mb-4 rounded-lg border border-danger-500/40 bg-danger-500/10 p-3">
			<p class="text-danger-300 text-sm">{error}</p>
		</div>
	{/if}

	{#if success}
		<div role="status" class="mb-4 rounded-lg border border-success-500/40 bg-success-500/10 p-3">
			<p class="text-success-300 text-sm">{success}</p>
		</div>
	{/if}

	{#if loading}
		<div class="skeleton h-4 w-48 mb-2"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-3/4"></div>
	{:else if !settings}
		<p class="text-sm text-ink-400">
			Identity controls are available to tenant admins on Growth, Pro, and Enterprise. If you
			expected access, confirm your account role and subscription tier.
		</p>
	{:else}
		<div class="space-y-4">
			<IdentitySsoSection bind:settings bind:domainsText />

			{#if advancedSectionsReady}
				{#await loadIdentityDiagnosticsSection()}
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<div class="skeleton mb-2 h-4 w-40"></div>
						<div class="skeleton mb-2 h-4 w-full"></div>
						<div class="skeleton h-4 w-2/3"></div>
					</div>
				{:then module}
					{@const IdentityDiagnosticsSection = module.default}
					<IdentityDiagnosticsSection {accessToken} {tier} />
				{:catch}
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500">Diagnostics are temporarily unavailable.</p>
					</div>
				{/await}

				{#await loadIdentityScimSection()}
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<div class="skeleton mb-2 h-4 w-40"></div>
						<div class="skeleton mb-2 h-4 w-full"></div>
						<div class="skeleton h-4 w-2/3"></div>
					</div>
				{:then module}
					{@const IdentityScimSection = module.default}
					<IdentityScimSection {accessToken} {tier} bind:settings />
				{:catch}
					<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
						<p class="text-xs text-ink-500">SCIM controls are temporarily unavailable.</p>
					</div>
				{/await}
			{:else}
				<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
					<div class="skeleton mb-2 h-4 w-40"></div>
					<div class="skeleton mb-2 h-4 w-full"></div>
					<div class="skeleton h-4 w-2/3"></div>
				</div>

				<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
					<div class="skeleton mb-2 h-4 w-40"></div>
					<div class="skeleton mb-2 h-4 w-full"></div>
					<div class="skeleton h-4 w-2/3"></div>
				</div>
			{/if}

			<div class="flex items-center justify-end gap-3 pt-2">
				<button
					type="button"
					class="btn btn-secondary"
					onclick={loadIdentitySettings}
					disabled={saving}
				>
					Refresh
				</button>
				<button
					type="button"
					class="btn btn-primary"
					onclick={saveIdentitySettings}
					disabled={saving}
				>
					{saving ? 'Saving…' : 'Save Identity Settings'}
				</button>
			</div>
		</div>
	{/if}
</div>
