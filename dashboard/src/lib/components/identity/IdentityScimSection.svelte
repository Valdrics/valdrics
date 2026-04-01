<script lang="ts">
	import { env as publicEnv } from '$env/dynamic/public';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { formatValidationIssues } from '$lib/validation/clientZod';
	import {
		extractErrorMessage,
		RotateTokenResponseSchema,
		ScimTokenTestResponseSchema
	} from './identitySettingsModel';
	import { scimBaseUrlFromPublicApiUrl } from './identitySettingsHelpers';
	import type { IdentitySettings } from './identitySettingsTypes';

	let {
		accessToken,
		tier,
		settings = $bindable()
	}: {
		accessToken?: string | null;
		tier?: string | null;
		settings: IdentitySettings;
	} = $props();

	let rotating = $state(false);
	let rotatedToken = $state('');
	let rotatedAt = $state('');
	let scimTokenInput = $state('');
	let scimTokenTesting = $state(false);
	let scimTokenTestStatus = $state('');
	let scimFeedback = $state('');
	let scimFeedbackTone = $state<'success' | 'error'>('success');

	function isEnterprise(currentTier: string | null | undefined): boolean {
		return (currentTier ?? '').toLowerCase() === 'enterprise';
	}

	function scimBaseUrl(): string {
		const publicApiUrl = String(publicEnv.PUBLIC_API_URL || '').trim();
		return scimBaseUrlFromPublicApiUrl(publicApiUrl);
	}

	function setFeedback(message: string, tone: 'success' | 'error') {
		scimFeedback = message;
		scimFeedbackTone = tone;
	}

	async function rotateScimToken() {
		rotating = true;
		setFeedback('', 'success');
		rotatedToken = '';
		rotatedAt = '';
		try {
			if (!accessToken) {
				throw new Error('Missing access token for SCIM token rotation');
			}
			const res = await api.post(
				edgeApiPath('/settings/identity/rotate-scim-token'),
				{},
				{ headers: { Authorization: `Bearer ${accessToken}` } }
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
			const payloadResult = RotateTokenResponseSchema.safeParse(await res.json());
			if (!payloadResult.success) {
				throw payloadResult.error;
			}
			const payload = payloadResult.data;
			rotatedToken = payload.scim_token;
			rotatedAt = payload.rotated_at;
			settings.has_scim_token = true;
			settings.scim_last_rotated_at = payload.rotated_at;
			setFeedback('SCIM token rotated. Store it now; it is shown only once.', 'success');
		} catch (error) {
			setFeedback(formatValidationIssues(error, false), 'error');
		} finally {
			rotating = false;
		}
	}

	async function copyToken() {
		if (!rotatedToken) return;
		try {
			await navigator.clipboard.writeText(rotatedToken);
			setFeedback('Copied token to clipboard.', 'success');
		} catch {
			setFeedback('Failed to copy token. Copy manually.', 'error');
		}
	}

	async function testScimToken() {
		scimTokenTesting = true;
		scimTokenTestStatus = '';
		setFeedback('', 'success');
		try {
			if (!scimTokenInput.trim()) return;
			if (!accessToken) {
				throw new Error('Missing access token for SCIM token test');
			}
			const res = await api.post(
				edgeApiPath('/settings/identity/scim/test-token'),
				{ scim_token: scimTokenInput.trim() },
				{ headers: { Authorization: `Bearer ${accessToken}` } }
			);
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(extractErrorMessage(data, 'Failed to test SCIM token'));
			}
			const payloadResult = ScimTokenTestResponseSchema.safeParse(await res.json());
			if (!payloadResult.success) {
				throw payloadResult.error;
			}
			scimTokenTestStatus = payloadResult.data.token_matches
				? 'Token matches.'
				: 'Token does not match.';
		} catch (error) {
			setFeedback(formatValidationIssues(error, false), 'error');
		} finally {
			scimTokenTesting = false;
			scimTokenInput = '';
		}
	}

	function addGroupMapping() {
		settings.scim_group_mappings = [
			...(settings.scim_group_mappings ?? []),
			{ group: '', role: 'member', persona: null }
		];
	}

	function removeGroupMapping(index: number) {
		settings.scim_group_mappings = (settings.scim_group_mappings ?? []).filter(
			(_, currentIndex) => currentIndex !== index
		);
	}
</script>

<div
	class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4"
	class:opacity-60={!isEnterprise(tier)}
	class:pointer-events-none={!isEnterprise(tier)}
>
	<div class="flex items-center justify-between gap-3">
		<div>
			<p class="font-medium">SCIM Provisioning</p>
			<p class="text-xs text-ink-500 mt-1">
				Enterprise-only. Base URL: <span class="font-mono">{scimBaseUrl()}</span>
			</p>
		</div>
		{#if !isEnterprise(tier)}
			<span class="badge badge-warning text-xs shrink-0">Enterprise Required</span>
		{/if}
	</div>

	{#if scimFeedback}
		<p
			class={`mt-3 text-xs ${scimFeedbackTone === 'success' ? 'text-success-300' : 'text-danger-300'}`}
		>
			{scimFeedback}
		</p>
	{/if}

	<div class="mt-4 space-y-3">
		<label class="flex items-center gap-3 cursor-pointer">
			<input type="checkbox" bind:checked={settings.scim_enabled} class="toggle" />
			<span>Enable SCIM provisioning</span>
		</label>

		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<p class="text-xs text-ink-500">
				Token status: {settings.has_scim_token
					? 'Configured'
					: 'Not set'}{settings.scim_last_rotated_at
					? ` • last rotated ${new Date(settings.scim_last_rotated_at).toLocaleString()}`
					: ''}
			</p>
			<button
				type="button"
				class="btn btn-secondary"
				onclick={rotateScimToken}
				disabled={rotating || !settings.scim_enabled}
			>
				{rotating ? 'Rotating…' : 'Rotate SCIM Token'}
			</button>
		</div>

		{#if rotatedToken}
			<div class="rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<p class="text-xs text-ink-500 mb-2">
					New token (store now; it will not be shown again){rotatedAt
						? ` • rotated ${rotatedAt}`
						: ''}:
				</p>
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
					<input class="font-mono text-xs" readonly value={rotatedToken} aria-label="SCIM token" />
					<button type="button" class="btn btn-primary" onclick={copyToken}>Copy</button>
				</div>
			</div>
		{/if}

		{#if isEnterprise(tier) && settings.scim_enabled && settings.has_scim_token}
			<div class="rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<p class="text-xs text-ink-500 mb-2">
					Test SCIM token (verifies match without revealing stored token):
				</p>
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
					<input
						type="password"
						placeholder="Paste token from your IdP"
						bind:value={scimTokenInput}
						aria-label="SCIM token test input"
					/>
					<button
						type="button"
						class="btn btn-secondary"
						onclick={testScimToken}
						disabled={scimTokenTesting || !scimTokenInput.trim()}
					>
						{scimTokenTesting ? 'Testing…' : 'Test Token'}
					</button>
				</div>
				{#if scimTokenTestStatus}
					<p class="mt-2 text-xs text-ink-200">{scimTokenTestStatus}</p>
				{/if}
			</div>
		{/if}

		{#if isEnterprise(tier)}
			<div class="rounded-lg border border-ink-800/60 bg-ink-950/40 p-3">
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="text-sm font-medium">SCIM group mappings</p>
						<p class="text-xs text-ink-500 mt-1">
							Optional. Map IdP groups to Valdrics role/persona at provisioning time.
						</p>
					</div>
					<button type="button" class="btn btn-secondary" onclick={addGroupMapping}>
						Add mapping
					</button>
				</div>

				{#if (settings.scim_group_mappings ?? []).length === 0}
					<p class="mt-3 text-xs text-ink-500">
						No mappings configured. Users will default to <span class="font-mono">member</span>.
					</p>
				{:else}
					<div class="mt-4 space-y-3">
						{#each settings.scim_group_mappings as mapping, index (index)}
							<div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
								<div class="md:col-span-2">
									<label for={`scim-group-${index}`}>Group name</label>
									<input
										id={`scim-group-${index}`}
										placeholder="finops-admins"
										bind:value={mapping.group}
									/>
								</div>
								<div>
									<label for={`scim-role-${index}`}>Role</label>
									<select id={`scim-role-${index}`} bind:value={mapping.role}>
										<option value="member">Member</option>
										<option value="admin">Admin</option>
									</select>
								</div>
								<div>
									<label for={`scim-persona-${index}`}>Persona (optional)</label>
									<select id={`scim-persona-${index}`} bind:value={mapping.persona}>
										<option value={null}>(no default)</option>
										<option value="engineering">Engineering</option>
										<option value="finance">Finance</option>
										<option value="platform">Platform</option>
										<option value="leadership">Leadership</option>
									</select>
								</div>
								<div class="md:col-span-4 flex justify-end">
									<button
										type="button"
										class="btn btn-secondary"
										onclick={() => removeGroupMapping(index)}
									>
										Remove
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
