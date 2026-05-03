export type SpendProviderOption = {
	id: string;
	name: string;
};

export const SPEND_PROVIDER_OPTIONS: readonly SpendProviderOption[] = [
	{ id: '', name: 'All Providers' },
	{ id: 'aws', name: 'AWS' },
	{ id: 'azure', name: 'Azure' },
	{ id: 'gcp', name: 'GCP' },
	{ id: 'saas', name: 'SaaS' },
	{ id: 'license', name: 'License' },
	{ id: 'platform', name: 'Platform' },
	{ id: 'hybrid', name: 'Hybrid' },
	{ id: 'ai', name: 'AI' }
] as const;

const SPEND_PROVIDER_VALUES = new Set(SPEND_PROVIDER_OPTIONS.map((provider) => provider.id));
const OPERATIONAL_PROVIDER_VALUES = new Set(
	SPEND_PROVIDER_OPTIONS.map((provider) => provider.id).filter((provider) => provider !== 'ai')
);

export function normalizeSpendProvider(value: string | null | undefined): string {
	const provider = String(value ?? '')
		.trim()
		.toLowerCase();
	return SPEND_PROVIDER_VALUES.has(provider) ? provider : '';
}

export function spendProviderParam(value: string | null | undefined): string | undefined {
	const provider = normalizeSpendProvider(value);
	return provider || undefined;
}

export function operationalProviderParam(value: string | null | undefined): string | undefined {
	const provider = normalizeSpendProvider(value);
	return provider && OPERATIONAL_PROVIDER_VALUES.has(provider) ? provider : undefined;
}
