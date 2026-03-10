<script lang="ts">
	import type { IdentitySettings } from './identitySettingsTypes';

	let {
		tier,
		settings = $bindable(),
		rotating = false,
		rotatedToken = '',
		rotatedAt = '',
		scimTokenInput = $bindable(''),
		scimTokenTesting = false,
		scimTokenTestStatus = '',
		scimBaseUrl,
		onRotateScimToken = () => {},
		onCopyToken = () => {},
		onTestScimToken = () => {},
		onAddGroupMapping = () => {},
		onRemoveGroupMapping = () => {}
	}: {
		tier?: string | null;
		settings: IdentitySettings;
		rotating?: boolean;
		rotatedToken?: string;
		rotatedAt?: string;
		scimTokenInput: string;
		scimTokenTesting?: boolean;
		scimTokenTestStatus?: string;
		scimBaseUrl: string;
		onRotateScimToken?: () => void | Promise<void>;
		onCopyToken?: () => void | Promise<void>;
		onTestScimToken?: () => void | Promise<void>;
		onAddGroupMapping?: () => void;
		onRemoveGroupMapping?: (index: number) => void;
	} = $props();

	function isEnterprise(currentTier: string | null | undefined): boolean {
		return (currentTier ?? '').toLowerCase() === 'enterprise';
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
				Enterprise-only. Base URL: <span class="font-mono">{scimBaseUrl}</span>
			</p>
		</div>
		{#if !isEnterprise(tier)}
			<span class="badge badge-warning text-xs shrink-0">Enterprise Required</span>
		{/if}
	</div>

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
				onclick={onRotateScimToken}
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
					<button type="button" class="btn btn-primary" onclick={onCopyToken}>Copy</button>
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
						onclick={onTestScimToken}
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
					<button type="button" class="btn btn-secondary" onclick={onAddGroupMapping}>
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
										onclick={() => onRemoveGroupMapping(index)}
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
