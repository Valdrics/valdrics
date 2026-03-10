<script lang="ts">
	import { base } from '$app/paths';
	import type { OnboardingProvider } from './onboardingTypesUtils';

	type AsyncAction = () => void | Promise<void>;

	interface Props {
		data: {
			subscription?: {
				tier?: string;
			};
		};
		currentStep: number;
		success: boolean;
		selectedProvider: OnboardingProvider;
		awsAccountId: string;
		roleArn: string;
		isManagementAccount: boolean;
		organizationId: string;
		isVerifying: boolean;
		verifyConnection: AsyncAction;
		getProviderLabel: (provider: OnboardingProvider) => string;
	}

	let {
		data,
		currentStep = $bindable(),
		success,
		selectedProvider,
		awsAccountId = $bindable(),
		roleArn = $bindable(),
		isManagementAccount = $bindable(),
		organizationId = $bindable(),
		isVerifying,
		verifyConnection,
		getProviderLabel
	}: Props = $props();

	const growthTier = $derived(
		['growth', 'pro', 'enterprise'].includes(data?.subscription?.tier ?? '')
	);
</script>

<!-- Step 2: Verify -->
{#if currentStep === 2}
	<div class="step-content">
		<h2>Step 2: Verify Your Connection</h2>
		<p>Enter the details from your AWS CloudFormation stack outputs.</p>

		<div class="form-group">
			<label for="accountId">AWS Account ID (12 digits)</label>
			<input
				type="text"
				id="accountId"
				bind:value={awsAccountId}
				placeholder="123456789012"
				maxlength="12"
			/>
		</div>

		<div class="form-group">
			<label for="roleArn">Role ARN (from CloudFormation Outputs)</label>
			<input
				type="text"
				id="roleArn"
				bind:value={roleArn}
				placeholder="arn:aws:iam::123456789012:role/ValdricsReadOnly"
			/>
		</div>

		<div class="form-group pt-4 border-t border-ink-800 relative" class:opacity-50={!growthTier}>
			<label class="flex items-center justify-between gap-3 cursor-pointer">
				<div class="flex items-center gap-3">
					<input
						type="checkbox"
						bind:checked={isManagementAccount}
						class="toggle"
						disabled={!growthTier}
					/>
					<span class="font-bold">Register as Management Account</span>
				</div>
				{#if !growthTier}
					<span class="badge badge-warning text-xs">Growth Tier +</span>
				{/if}
			</label>
			<p class="text-xs text-ink-500 mt-2">
				Enable this if this account is the Management Account of an AWS Organization. Valdrics may
				discover likely member accounts and prefill linking suggestions for review when organization
				permissions allow.
			</p>
			{#if !growthTier}
				<p class="text-xs text-accent-400 mt-1">
					⚡ Multi-account discovery requires Growth tier or higher.
				</p>
			{/if}
		</div>

		{#if isManagementAccount}
			<div class="form-group stagger-enter">
				<label for="org_id">Organization ID (Optional)</label>
				<input
					type="text"
					id="org_id"
					bind:value={organizationId}
					placeholder="o-xxxxxxxxxx"
					class="input"
				/>
			</div>
		{/if}

		<button type="button" class="primary-btn" onclick={verifyConnection} disabled={isVerifying}>
			{isVerifying ? '⏳ Verifying...' : '✅ Verify Connection'}
		</button>

		<button type="button" class="secondary-btn" onclick={() => (currentStep = 1)}>
			← Back to Template
		</button>
	</div>
{/if}

<!-- Step 3: Success -->
{#if currentStep === 3 && success}
	<div class="step-content success">
		<div class="success-icon">🎉</div>
		<h2>Connection Successful!</h2>
		<p>
			Valdrics can now analyze your {getProviderLabel(selectedProvider)} spend. Open the dashboard to
			confirm the first live signal, owner context, and next action.
		</p>

		<a href={`${base}/`} class="primary-btn"> Open First-Value Dashboard → </a>
	</div>
{/if}
