import { resolveSessionTenantId } from '$lib/auth/sessionTenant';
import {
	canUseCloudPlusFeaturesForTier,
	canUseIdpDeepScanForTier,
	canUseMultiCloudFeaturesForTier
} from './onboardingTierAccess';

type SessionTenantInput = Parameters<typeof resolveSessionTenantId>[0];

export type OnboardingViewData =
	| (SessionTenantInput & {
			subscription?: { tier?: string | null } | null;
	  })
	| null
	| undefined;

function createModuleLoader<T>(loader: () => Promise<T>): () => Promise<T> {
	let promise: Promise<T> | null = null;

	return () => {
		if (!promise) {
			promise = loader().catch((error) => {
				promise = null;
				throw error;
			});
		}
		return promise;
	};
}

export const loadOnboardingApiModule = createModuleLoader(() => import('./onboardingApi'));
export const loadOnboardingSetupActionsModule = createModuleLoader(
	() => import('./onboardingSetupActions')
);
export const loadOnboardingFlowActionsModule = createModuleLoader(
	() => import('./onboardingFlowActions')
);
export const loadOnboardingDiscoveryActionsModule = createModuleLoader(
	() => import('./onboardingDiscoveryActions')
);
export const loadOnboardingUiActionsModule = createModuleLoader(
	() => import('./onboardingUiActions')
);
export const loadOnboardingPageViewBody = createModuleLoader(
	() => import('./OnboardingPageViewBody.svelte')
);

function resolveSubscriptionTier(data: OnboardingViewData): string | null | undefined {
	return data?.subscription?.tier;
}

export function canUseMultiCloudFeaturesForView(data: OnboardingViewData): boolean {
	return canUseMultiCloudFeaturesForTier(resolveSubscriptionTier(data));
}

export function canUseCloudPlusFeaturesForView(data: OnboardingViewData): boolean {
	return canUseCloudPlusFeaturesForTier(resolveSubscriptionTier(data));
}

export function canUseIdpDeepScanForView(data: OnboardingViewData): boolean {
	return canUseIdpDeepScanForTier(resolveSubscriptionTier(data));
}

export function resolveOnboardingTenantId(data: OnboardingViewData): string | undefined {
	return resolveSessionTenantId({ session: data?.session, user: data?.user });
}
