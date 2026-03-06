export function canUseGrowthFeaturesForTier(tier: string | null | undefined): boolean {
	return ['growth', 'pro', 'enterprise'].includes(tier ?? '');
}

export function canUseCloudPlusFeaturesForTier(tier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes(tier ?? '');
}

export function canUseIdpDeepScanForTier(tier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes(tier ?? '');
}
