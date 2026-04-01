<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { clientLogger } from '$lib/logging/client';
	import { formatValidationIssues } from '$lib/validation/clientZod';
	import { isGrowthPlus } from './identitySettingsHelpers';
	import {
		extractErrorMessage,
		IDENTITY_REQUEST_TIMEOUT_MS,
		IdentityDiagnosticsSchema
	} from './identitySettingsModel';
	import type { IdentityDiagnostics } from './identitySettingsTypes';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();

	let diagnosticsLoading = $state(false);
	let diagnostics = $state<IdentityDiagnostics | null>(null);
	let diagnosticsError = $state('');

	async function loadDiagnostics() {
		diagnosticsLoading = true;
		diagnosticsError = '';
		try {
			if (!accessToken || !isGrowthPlus(tier)) {
				diagnostics = null;
				return;
			}
			const res = await api.get(edgeApiPath('/settings/identity/diagnostics'), {
				headers: { Authorization: `Bearer ${accessToken}` },
				timeoutMs: IDENTITY_REQUEST_TIMEOUT_MS
			});
			if (res.status === 403) {
				diagnostics = null;
				return;
			}
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to load identity diagnostics'));
			}
			const parsedResult = IdentityDiagnosticsSchema.safeParse(await res.json());
			if (!parsedResult.success) {
				throw parsedResult.error;
			}
			diagnostics = parsedResult.data as IdentityDiagnostics;
		} catch (error) {
			clientLogger.error('Failed to load identity diagnostics:', error);
			diagnosticsError =
				error instanceof TimeoutError
					? 'Identity diagnostics request timed out. Try again.'
					: formatValidationIssues(error, false);
			diagnostics = null;
		} finally {
			diagnosticsLoading = false;
		}
	}

	onMount(() => {
		void loadDiagnostics();
	});
</script>

<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
	<div class="flex items-center justify-between gap-3">
		<div>
			<p class="font-medium">Onboarding Diagnostics</p>
			<p class="text-xs text-ink-500 mt-1">
				Validates SSO enforcement and SCIM readiness for this tenant.
			</p>
		</div>
		<button
			type="button"
			class="btn btn-secondary shrink-0"
			onclick={loadDiagnostics}
			disabled={diagnosticsLoading}
		>
			{diagnosticsLoading ? 'Refreshing…' : 'Refresh Diagnostics'}
		</button>
	</div>

	{#if diagnosticsError}
		<p class="mt-3 text-xs text-danger-300">{diagnosticsError}</p>
	{/if}

	{#if diagnosticsLoading}
		<div class="mt-4 space-y-2">
			<div class="skeleton h-4 w-48"></div>
			<div class="skeleton h-4 w-full"></div>
			<div class="skeleton h-4 w-3/4"></div>
		</div>
	{:else if diagnostics}
		<div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
			<div class="rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<p class="text-xs text-ink-500 mb-2">SSO</p>
				<p class="text-sm">
					{diagnostics.sso.enforcement_active ? 'Enforcement active' : 'Enforcement inactive'}
				</p>
				<p class="text-xs text-ink-500 mt-2">
					Allowed domains: {diagnostics.sso.allowed_email_domains.length}
					{#if diagnostics.sso.current_admin_domain}
						• admin domain: <span class="font-mono">{diagnostics.sso.current_admin_domain}</span>
					{/if}
				</p>
				<p class="text-xs text-ink-500 mt-1">
					Federation: {diagnostics.sso.federation_enabled
						? diagnostics.sso.federation_ready
							? `${diagnostics.sso.federation_mode} configured`
							: `${diagnostics.sso.federation_mode} misconfigured`
						: 'disabled'}
				</p>
				{#if diagnostics.sso.issues.length}
					<ul class="mt-2 text-xs text-danger-300 list-disc pl-5 space-y-1">
						{#each diagnostics.sso.issues as issue (issue)}
							<li>{issue}</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<p class="text-xs text-ink-500 mb-2">SCIM</p>
				<p class="text-sm">
					{#if diagnostics.scim.available}
						{diagnostics.scim.enabled ? 'Enabled' : 'Disabled'}
					{:else}
						Enterprise tier required
					{/if}
				</p>
				<p class="text-xs text-ink-500 mt-2">
					Token: {diagnostics.scim.has_token ? 'Configured' : 'Missing'}
					{#if diagnostics.scim.rotation_overdue}
						• rotation overdue
					{/if}
				</p>
				{#if diagnostics.scim.issues.length}
					<ul class="mt-2 text-xs text-danger-300 list-disc pl-5 space-y-1">
						{#each diagnostics.scim.issues as issue (issue)}
							<li>{issue}</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>

		{#if diagnostics.recommendations.length}
			<div class="mt-4 rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<p class="text-xs text-ink-500 mb-2">Recommendations</p>
				<ul class="text-xs text-ink-200 list-disc pl-5 space-y-1">
					{#each diagnostics.recommendations as rec (rec)}
						<li>{rec}</li>
					{/each}
				</ul>
			</div>
		{/if}
	{:else}
		<p class="text-xs text-ink-500 mt-3">
			Diagnostics are not available yet. Click refresh to validate tenant readiness.
		</p>
	{/if}
</div>
