<script lang="ts">
	let {
		selectedTab = $bindable(),
		copied,
		magicLink,
		cloudformationYaml,
		terraformHcl,
		roleArn = $bindable(),
		awsAccountId = $bindable(),
		isManagementAccount = $bindable(),
		organizationId = $bindable(),
		growthTier,
		copyTemplate,
		downloadTemplate
	} = $props();
</script>

<h2>Step 2: Connect AWS Account</h2>
<p class="mb-6">We've generated a secure IAM role template for your account.</p>

{#if magicLink}
	<div
		class="magic-link-box p-6 bg-accent-950/20 border border-accent-500/30 rounded-2xl mb-8 flex flex-col items-center gap-4"
	>
		<div class="text-3xl">🧩</div>
		<div class="text-center">
			<h4 class="font-bold text-lg mb-1">Recommended: 1-Click Setup</h4>
			<p class="text-sm text-ink-400">
				Launch a CloudFormation stack with all parameters pre-filled.
			</p>
		</div>
		<a
			href={magicLink}
			target="_blank"
			rel="noopener noreferrer"
			class="primary-btn !w-auto px-8 py-3 bg-accent-500 hover:bg-accent-600"
		>
			⚡ Launch AWS Stack
		</a>
	</div>

	<div class="divider text-xs text-ink-500 mb-6 flex items-center gap-4">
		<div class="h-px flex-1 bg-ink-800"></div>
		OR USE MANUAL TEMPLATES
		<div class="h-px flex-1 bg-ink-800"></div>
	</div>
{/if}

<div class="tab-selector">
	<button
		type="button"
		class="tab"
		class:active={selectedTab === 'cloudformation'}
		onclick={() => (selectedTab = 'cloudformation')}
	>
		☁️ CloudFormation
	</button>
	<button
		type="button"
		class="tab"
		class:active={selectedTab === 'terraform'}
		onclick={() => (selectedTab = 'terraform')}
	>
		🏗️ Terraform
	</button>
</div>

<div class="manual-guide mb-8">
	<h4 class="font-bold text-ink-100 flex items-center gap-2 mb-4">
		<span class="text-accent-500">🛡️</span> Security & Deployment Guide
	</h4>

	<div class="space-y-3">
		<div
			class="flex items-start gap-4 p-4 bg-ink-900 border border-ink-800 rounded-xl transition-all hover:border-ink-700"
		>
			<div
				class="flex-shrink-0 w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 font-bold"
			>
				1
			</div>
			<div>
				<p class="text-sm font-semibold text-ink-100 mb-1">Acquire Infrastructure Template</p>
				<p class="text-xs text-ink-400">
					Select either CloudFormation or Terraform below. Use the <strong>Copy</strong> or
					<strong>Download</strong> buttons to save the configuration file to your local machine.
				</p>
			</div>
		</div>

		<div
			class="flex items-start gap-4 p-4 bg-ink-900 border border-ink-800 rounded-xl transition-all hover:border-ink-700"
		>
			<div
				class="flex-shrink-0 w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 font-bold"
			>
				2
			</div>
			<div>
				<p class="text-sm font-semibold text-ink-100 mb-1">Provision Resources in AWS</p>
				<p class="text-xs text-ink-400">
					Navigate to the
					<a
						href="https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/template"
						target="_blank"
						rel="noopener noreferrer"
						class="text-accent-400 hover:text-accent-300 underline underline-offset-4 decoration-accent-500/30"
						>AWS CloudFormation Console</a
					>. Select <strong>Create Stack</strong> and choose
					<strong>Upload a template file</strong> to begin the deployment.
				</p>
			</div>
		</div>

		<div
			class="flex items-start gap-4 p-4 bg-ink-900 border border-ink-800 rounded-xl transition-all hover:border-ink-700"
		>
			<div
				class="flex-shrink-0 w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 font-bold"
			>
				3
			</div>
			<div>
				<p class="text-sm font-semibold text-ink-100 mb-1">Finalize Deployment & Capture ARN</p>
				<p class="text-xs text-ink-400">
					Follow the AWS wizard. Once the stack status is <strong>CREATE_COMPLETE</strong>, navigate to
					the <strong>Outputs</strong> tab to find and copy your new <strong>RoleArn</strong>.
				</p>
			</div>
		</div>

		<div
			class="flex items-start gap-4 p-4 bg-ink-900 border border-ink-800 rounded-xl transition-all hover:border-ink-700"
		>
			<div
				class="flex-shrink-0 w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 font-bold"
			>
				4
			</div>
			<div>
				<p class="text-sm font-semibold text-ink-100 mb-1">Verify Connection</p>
				<p class="text-xs text-ink-400">
					Return to this page and paste the captured <strong>RoleArn</strong> into the verification field
					in Step 3 to activate your connection.
				</p>
			</div>
		</div>
	</div>
</div>

<div class="code-container">
	<div class="code-header">
		<span>{selectedTab === 'cloudformation' ? 'valdrics-role.yaml' : 'valdrics-role.tf'}</span>
		<div class="code-actions">
			<button type="button" class="icon-btn" onclick={copyTemplate}>{copied ? '✅' : '📋 Copy'}</button>
			<button type="button" class="icon-btn" onclick={downloadTemplate}>📥</button>
		</div>
	</div>
	<pre class="code-block">{selectedTab === 'cloudformation' ? cloudformationYaml : terraformHcl}</pre>
</div>

<div class="divider text-xs text-ink-500 my-8 flex items-center gap-4">
	<div class="h-px flex-1 bg-ink-800"></div>
	STEP 3: VERIFY CONNECTION
	<div class="h-px flex-1 bg-ink-800"></div>
</div>

<div class="verification-section p-6 bg-ink-900 border border-ink-800 rounded-2xl mb-8">
	<div class="form-group">
		<label for="accountId">AWS Account ID (12 digits)</label>
		<input
			type="text"
			id="accountId"
			bind:value={awsAccountId}
			placeholder="123456789012"
			maxlength="12"
			class="input"
		/>
	</div>

	<div class="form-group">
		<label for="roleArn">Role ARN (from CloudFormation Outputs)</label>
		<input
			type="text"
			id="roleArn"
			bind:value={roleArn}
			placeholder="arn:aws:iam::123456789012:role/ValdricsReadOnly"
			class="input"
		/>
	</div>

	<div class="form-group pt-4 border-t border-ink-800 relative mt-4" class:opacity-50={!growthTier}>
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
	</div>

	{#if isManagementAccount}
		<div class="form-group stagger-enter mt-4">
			<label for="org_id">Organization ID (Optional)</label>
			<input type="text" id="org_id" bind:value={organizationId} placeholder="o-xxxxxxxxxx" class="input" />
		</div>
	{/if}
</div>
