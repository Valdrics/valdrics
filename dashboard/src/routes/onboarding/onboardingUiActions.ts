import { trackProductFunnelStage } from '$lib/funnel/productFunnelTelemetry';
import {
	parseCloudPlusConnectorConfig as parseCloudPlusConnectorConfigHelper,
	parseCloudPlusFeed as parseCloudPlusFeedHelper
} from './onboardingCloudPlusHelpers';
import type {
	CloudPlusAuthMethod,
	NativeConnectorMeta,
	OnboardingProvider
} from './onboardingTypesUtils';

export function getOnboardingSetupAccessError(args: {
	selectedProvider: OnboardingProvider;
	canUseGrowthFeatures: boolean;
	canUseCloudPlusFeatures: boolean;
	getProviderLabel: (provider: OnboardingProvider) => string;
}): string | null {
	const { selectedProvider, canUseGrowthFeatures, canUseCloudPlusFeatures, getProviderLabel } = args;
	if ((selectedProvider === 'azure' || selectedProvider === 'gcp') && !canUseGrowthFeatures) {
		return `${getProviderLabel(selectedProvider)} onboarding requires Growth tier or higher.`;
	}
	if (
		(selectedProvider === 'saas' || selectedProvider === 'license') &&
		!canUseCloudPlusFeatures
	) {
		return `${getProviderLabel(selectedProvider)} onboarding requires Pro tier or higher.`;
	}
	return null;
}

export async function copyOnboardingTemplate(template: string): Promise<void> {
	await navigator.clipboard.writeText(template);
}

export function downloadOnboardingTemplate(template: string, filename: string): void {
	const blob = new Blob([template], { type: 'text/plain' });
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = filename;
	anchor.click();
	URL.revokeObjectURL(url);
}

export function parseOnboardingCloudPlusFeed(feedInput: string): Array<Record<string, unknown>> {
	return parseCloudPlusFeedHelper(feedInput);
}

export function parseOnboardingCloudPlusConnectorConfig(args: {
	connectorConfigInput: string;
	selectedConnector: NativeConnectorMeta | null;
	isNativeAuthMethod: boolean;
	requiredConfigValues: Record<string, string>;
}): Record<string, unknown> {
	return parseCloudPlusConnectorConfigHelper(args);
}

export function trackOnboardingConnectionVerified(args: {
	accessToken: string | null | undefined;
	tenantId: string | undefined;
	url: URL;
	currentTier: string | undefined;
	persona: string;
	provider: OnboardingProvider;
}): void {
	if (!args.accessToken) return;
	void trackProductFunnelStage({
		accessToken: args.accessToken,
		stage: 'connection_verified',
		tenantId: args.tenantId,
		url: args.url,
		currentTier: args.currentTier,
		persona: args.persona,
		provider: args.provider,
		source: 'onboarding_verify_success'
	});
}

export function getCloudPlusTemplateForTab(args: {
	selectedTab: 'cloudformation' | 'terraform';
	cloudformationYaml: string;
	terraformHcl: string;
}): { template: string; filename: string } {
	if (args.selectedTab === 'cloudformation') {
		return {
			template: args.cloudformationYaml,
			filename: 'valdrics-role.yaml'
		};
	}
	return {
		template: args.terraformHcl,
		filename: 'valdrics-role.tf'
	};
}
