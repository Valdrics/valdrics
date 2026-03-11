<script lang="ts">
	let { selectedProvider, isVerifying, onBack, verifyConnection, proceedToVerify } = $props();
</script>

<div class="flex gap-4 mt-8">
	<button type="button" class="secondary-btn !w-auto px-6" onclick={onBack}>← Back</button>
	{#if selectedProvider === 'aws'}
		<button
			type="button"
			class="primary-btn !flex-1"
			onclick={verifyConnection}
			disabled={isVerifying}
		>
			{isVerifying ? '⏳ Verifying...' : '✅ Verify Connection'}
		</button>
	{:else}
		<button
			type="button"
			class="primary-btn !flex-1"
			onclick={proceedToVerify}
			disabled={isVerifying}
		>
			{#if isVerifying}
				⏳ Verifying...
			{:else if selectedProvider === 'saas' || selectedProvider === 'license'}
				✅ Create & Verify Connector
			{:else}
				Next: Verify Connection →
			{/if}
		</button>
	{/if}
</div>
