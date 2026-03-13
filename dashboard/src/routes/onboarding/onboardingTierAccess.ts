export function canUseMultiCloudFeaturesForTier(tier: string | null | undefined): boolean {
	return ['starter', 'growth', 'pro', 'enterprise'].includes(tier ?? '');
}

export function canUseCloudPlusFeaturesForTier(tier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes(tier ?? '');
}

export function canUseIdpDeepScanForTier(tier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes(tier ?? '');
}
