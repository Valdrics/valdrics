<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import { env as publicEnv } from '$env/dynamic/public';
	import { base } from '$app/paths';
	import { api } from '$lib/api';
	import IdentityDiagnosticsSection from '$lib/components/identity/IdentityDiagnosticsSection.svelte';
	import IdentityScimSection from '$lib/components/identity/IdentityScimSection.svelte';
	import IdentitySsoSection from '$lib/components/identity/IdentitySsoSection.svelte';
	import { getUpgradePrompt } from '$lib/pricing/upgradePrompt';
	import {
		isGrowthPlus,
		parseDomains,
		scimBaseUrlFromPublicApiUrl
	} from '$lib/components/identity/identitySettingsHelpers';
	import {
		extractErrorMessage,
		IDENTITY_REQUEST_TIMEOUT_MS,
		IdentityDiagnosticsSchema,
		IdentitySettingsResponseSchema,
		IdentitySettingsUpdateSchema,
		RotateTokenResponseSchema,
		ScimTokenTestResponseSchema,
		uniqueScimMappingsOrThrow
	} from '$lib/components/identity/identitySettingsModel';
	import type {
		IdentityDiagnostics,
		IdentitySettings
	} from '$lib/components/identity/identitySettingsTypes';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { clientLogger } from '$lib/logging/client';
	import { z } from 'zod';

	let {
		accessToken,
		tier
	}: {
		accessToken?: string | null;
		tier?: string | null;
	} = $props();

	let loading = $state(true);
	let saving = $state(false);
	let rotating = $state(false);
	let diagnosticsLoading = $state(false);
	let scimTokenTesting = $state(false);
	let error = $state('');
	let success = $state('');

	let settings = $state<IdentitySettings | null>(null);
	let domainsText = $state('');
	let rotatedToken = $state<string>('');
	let rotatedAt = $state<string>('');
	let diagnostics = $state<IdentityDiagnostics | null>(null);
	let scimTokenInput = $state('');
	let scimTokenTestStatus = $state<string>('');

	function scimBaseUrl(): string {
		const publicApiUrl = String(publicEnv.PUBLIC_API_URL || '').trim();
		return scimBaseUrlFromPublicApiUrl(publicApiUrl);
	}

	async function getHeaders() {
		return {
			Authorization: `Bearer ${accessToken}`
		};
	}

	async function getWithTimeout(url: string, headers?: Record<string, string>) {
		return api.get(url, {
			...(headers ? { headers } : {}),
			timeoutMs: IDENTITY_REQUEST_TIMEOUT_MS
		});
	}

	async function loadIdentitySettings() {
		loading = true;
		error = '';
		success = '';
		rotatedToken = '';
		rotatedAt = '';
		try {
			if (!accessToken) {
				settings = null;
				return;
			}
			if (!isGrowthPlus(tier)) {
				settings = null;
				return;
			}
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/identity'), headers);
			if (res.status === 403) {
				settings = null;
				return;
			}
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to load identity settings'));
			}
			const loaded = IdentitySettingsResponseSchema.parse(await res.json());
			settings = {
				...(loaded as IdentitySettings),
				sso_federation_provider_id: loaded.sso_federation_provider_id ?? ''
			};
			domainsText = (loaded.allowed_email_domains ?? []).join(', ');
			await loadDiagnostics();
		} catch (e) {
			clientLogger.error('Failed to load identity settings:', e);
			error =
				e instanceof TimeoutError
					? 'Identity settings request timed out. Try again.'
					: (e as Error).message;
		} finally {
			loading = false;
		}
	}

	async function loadDiagnostics() {
		diagnosticsLoading = true;
		scimTokenTestStatus = '';
		try {
			if (!accessToken) {
				diagnostics = null;
				return;
			}
			if (!isGrowthPlus(tier)) {
				diagnostics = null;
				return;
			}
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/identity/diagnostics'), headers);
			if (res.status === 403) {
				diagnostics = null;
				return;
			}
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to load identity diagnostics'));
			}
			const parsed = IdentityDiagnosticsSchema.parse(await res.json());
			diagnostics = parsed as IdentityDiagnostics;
		} catch (e) {
			clientLogger.error('Failed to load identity diagnostics:', e);
			error =
				e instanceof TimeoutError
					? 'Identity diagnostics request timed out. Try again.'
					: (e as Error).message;
			diagnostics = null;
		} finally {
			diagnosticsLoading = false;
		}
	}

	async function testScimToken() {
		scimTokenTesting = true;
		scimTokenTestStatus = '';
		error = '';
		try {
			if (!scimTokenInput.trim()) return;
			const headers = await getHeaders();
			const res = await api.post(
				edgeApiPath('/settings/identity/scim/test-token'),
				{ scim_token: scimTokenInput.trim() },
				{ headers }
			);
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to test SCIM token'));
			}
			const payload = ScimTokenTestResponseSchema.parse(await res.json());
			scimTokenTestStatus = payload.token_matches ? 'Token matches.' : 'Token does not match.';
		} catch (e) {
			if (e instanceof z.ZodError) {
				error = e.issues.map((err: z.ZodIssue) => err.message).join(', ');
			} else {
				error = (e as Error).message;
			}
		} finally {
			scimTokenTesting = false;
			// Never keep tokens in UI state longer than needed.
			scimTokenInput = '';
		}
	}

	async function saveIdentitySettings() {
		if (!settings) return;
		saving = true;
		error = '';
		success = '';
		try {
			uniqueScimMappingsOrThrow(settings.scim_group_mappings ?? []);
			const payload = {
				sso_enabled: settings.sso_enabled,
				allowed_email_domains: parseDomains(domainsText),
				sso_federation_enabled: settings.sso_federation_enabled,
				sso_federation_mode: settings.sso_federation_mode,
				sso_federation_provider_id:
					settings.sso_federation_mode === 'provider_id'
						? (settings.sso_federation_provider_id?.trim() ?? null)
						: null,
				scim_enabled: settings.scim_enabled,
				scim_group_mappings: (settings.scim_group_mappings ?? []).map((mapping) => ({
					group: mapping.group.trim().toLowerCase(),
					role: mapping.role,
					persona: mapping.persona || null
				}))
			};
			const validated = IdentitySettingsUpdateSchema.parse(payload);

			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/identity'), validated, { headers });
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to save identity settings'));
			}
			const updated = IdentitySettingsResponseSchema.parse(await res.json());
			settings = {
				...(updated as IdentitySettings),
				sso_federation_provider_id: updated.sso_federation_provider_id ?? ''
			};
			domainsText = (updated.allowed_email_domains ?? []).join(', ');
			success = 'Identity settings saved.';
			setTimeout(() => (success = ''), 2500);
			await loadDiagnostics();
		} catch (e) {
			if (e instanceof z.ZodError) {
				error = e.issues.map((err: z.ZodIssue) => err.message).join(', ');
			} else {
				error = (e as Error).message;
			}
		} finally {
			saving = false;
		}
	}

	async function rotateScimToken() {
		rotating = true;
		error = '';
		success = '';
		rotatedToken = '';
		rotatedAt = '';
		try {
			const headers = await getHeaders();
			const res = await api.post(
				edgeApiPath('/settings/identity/rotate-scim-token'),
				{},
				{ headers }
			);
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(
					extractErrorMessage(
						data,
						res.status === 403
							? 'SCIM token rotation requires Enterprise tier and admin access.'
							: 'Failed to rotate SCIM token'
					)
				);
			}
			const payload = RotateTokenResponseSchema.parse(await res.json());
			rotatedToken = payload.scim_token;
			rotatedAt = payload.rotated_at;
			success = 'SCIM token rotated. Store it now; it is shown only once.';
			await loadIdentitySettings();
		} catch (e) {
			if (e instanceof z.ZodError) {
				error = e.issues.map((err: z.ZodIssue) => err.message).join(', ');
			} else {
				error = (e as Error).message;
			}
		} finally {
			rotating = false;
		}
	}

	async function copyToken() {
		if (!rotatedToken) return;
		try {
			await navigator.clipboard.writeText(rotatedToken);
			success = 'Copied token to clipboard.';
			setTimeout(() => (success = ''), 2000);
		} catch {
			error = 'Failed to copy token. Copy manually.';
		}
	}

	onMount(() => {
		void loadIdentitySettings();
	});

	function addGroupMapping() {
		if (!settings) return;
		settings.scim_group_mappings = [
			...(settings.scim_group_mappings ?? []),
			{ group: '', role: 'member', persona: null }
		];
	}

	function removeGroupMapping(index: number) {
		if (!settings) return;
		settings.scim_group_mappings = (settings.scim_group_mappings ?? []).filter(
			(_, i) => i !== index
		);
	}

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

			<IdentityDiagnosticsSection {diagnosticsLoading} {diagnostics} onRefresh={loadDiagnostics} />

			<IdentityScimSection
				{tier}
				bind:settings
				{rotating}
				{rotatedToken}
				{rotatedAt}
				bind:scimTokenInput
				{scimTokenTesting}
				{scimTokenTestStatus}
				scimBaseUrl={scimBaseUrl()}
				onRotateScimToken={rotateScimToken}
				onCopyToken={copyToken}
				onTestScimToken={testScimToken}
				onAddGroupMapping={addGroupMapping}
				onRemoveGroupMapping={removeGroupMapping}
			/>

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
