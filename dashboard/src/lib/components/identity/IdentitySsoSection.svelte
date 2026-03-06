<script lang="ts">
	import type { IdentitySettings } from './identitySettingsTypes';

	let {
		settings = $bindable(),
		domainsText = $bindable('')
	}: {
		settings: IdentitySettings;
		domainsText: string;
	} = $props();
</script>

<div class="form-group">
	<label class="flex items-center gap-3 cursor-pointer">
		<input type="checkbox" bind:checked={settings.sso_enabled} class="toggle" />
		<span>Enable SSO enforcement (domain allowlisting)</span>
	</label>
	<p class="text-xs text-ink-500 mt-1">
		This blocks access when a user email domain is not in the allowlist.
	</p>
</div>

<div class="form-group">
	<label for="allowed_email_domains">Allowed Email Domains</label>
	<textarea
		id="allowed_email_domains"
		rows="2"
		bind:value={domainsText}
		placeholder="example.com, subsidiary.example"
	></textarea>
	<p class="text-xs text-ink-500 mt-1">
		Comma, whitespace, or newline separated. Include your current admin domain to avoid lockout.
	</p>
</div>

<div class="rounded-xl border border-ink-800/60 bg-ink-950/30 p-4">
	<div class="flex items-center justify-between gap-3">
		<div>
			<p class="font-medium">Federated SSO Login (OIDC/SAML via Supabase SSO)</p>
			<p class="text-xs text-ink-500 mt-1">
				Enables real IdP login flow on the sign-in page. Keep domain allowlisting enabled as a
				second-layer guardrail.
			</p>
		</div>
	</div>

	<div class="mt-4 space-y-3">
		<label class="flex items-center gap-3 cursor-pointer">
			<input type="checkbox" bind:checked={settings.sso_federation_enabled} class="toggle" />
			<span>Enable federated SSO login</span>
		</label>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
			<div>
				<label for="sso_federation_mode">Federation Mode</label>
				<select
					id="sso_federation_mode"
					bind:value={settings.sso_federation_mode}
					disabled={!settings.sso_federation_enabled}
				>
					<option value="domain">Domain discovery (recommended)</option>
					<option value="provider_id">Explicit provider_id</option>
				</select>
			</div>

			{#if settings.sso_federation_mode === 'provider_id'}
				<div>
					<label for="sso_federation_provider_id">Supabase provider_id</label>
					<input
						id="sso_federation_provider_id"
						bind:value={settings.sso_federation_provider_id}
						placeholder="sso_abc123"
						disabled={!settings.sso_federation_enabled}
					/>
					<p class="text-xs text-ink-500 mt-1">Required only for provider_id mode.</p>
				</div>
			{/if}
		</div>
	</div>
</div>
