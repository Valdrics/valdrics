<script lang="ts">
	import type { LandingCurrencyCode } from '$lib/landing/currencyPreference';
	import { getCurrencyMetadata } from '$lib/landing/roiCalculator';

	let {
		currencyCode,
		localCurrencyCode,
		onCurrencyCodeChange = () => {},
		label = 'Display currency'
	}: {
		currencyCode: LandingCurrencyCode | string;
		localCurrencyCode: LandingCurrencyCode;
		onCurrencyCodeChange?: (value: LandingCurrencyCode) => void;
		label?: string;
	} = $props();

	let normalizedCurrencyCode = $derived(
		String(currencyCode || 'USD')
			.trim()
			.toUpperCase() || 'USD'
	);
	let localCurrency = $derived(localCurrencyCode || 'USD');
	let localCurrencyMeta = $derived(getCurrencyMetadata(localCurrency));
	let usdCurrencyMeta = $derived(getCurrencyMetadata('USD'));
	let showUsdToggle = $derived(localCurrency !== 'USD');

	function selectCurrency(nextCurrencyCode: LandingCurrencyCode): void {
		if (normalizedCurrencyCode === nextCurrencyCode) return;
		onCurrencyCodeChange(nextCurrencyCode);
	}
</script>

<div class="landing-currency-toggle" role="group" aria-label={label}>
	<span class="landing-currency-toggle__label">{label}</span>
	<div class="landing-currency-toggle__controls">
		<button
			type="button"
			class:active={normalizedCurrencyCode === localCurrency}
			aria-pressed={normalizedCurrencyCode === localCurrency}
			onclick={() => selectCurrency(localCurrency)}
		>
			{#if showUsdToggle}
				Local {localCurrencyMeta.code} ({localCurrencyMeta.symbol})
			{:else}
				{localCurrencyMeta.label}
			{/if}
		</button>
		{#if showUsdToggle}
			<button
				type="button"
				class:active={normalizedCurrencyCode === 'USD'}
				aria-pressed={normalizedCurrencyCode === 'USD'}
				onclick={() => selectCurrency('USD')}
			>
				{usdCurrencyMeta.label}
			</button>
		{/if}
	</div>
	{#if showUsdToggle}
		<p class="landing-currency-toggle__note">
			USD is the default comparison view. Local display uses indicative FX.
		</p>
	{/if}
</div>
