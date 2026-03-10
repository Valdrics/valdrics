import { createLandingHeroTelemetryController } from '$lib/landing/landingHeroTelemetryController';
import type { LandingExperimentAssignments } from '$lib/landing/landingExperiment';
import type { LandingAttribution } from '$lib/landing/landingFunnel';

type LandingHeroTelemetryBridgeArgs = {
	getTelemetryEnabled: () => boolean;
	setTelemetryEnabled: (value: boolean) => void;
	getTelemetryInitialized: () => boolean;
	setTelemetryInitialized: (value: boolean) => void;
	setCookieBannerVisible: (value: boolean) => void;
	getEngagedCaptured: () => boolean;
	setEngagedCaptured: (value: boolean) => void;
	getScenarioAdjustCaptured: () => boolean;
	setScenarioAdjustCaptured: (value: boolean) => void;
	getVisitorId: () => string;
	setVisitorId: (value: string) => void;
	getExperiments: () => LandingExperimentAssignments;
	setExperiments: (value: LandingExperimentAssignments) => void;
	getAttribution: () => LandingAttribution;
	setAttribution: (value: LandingAttribution) => void;
	getPersona: () => string;
	getPagePath: () => string;
	getReferrer: () => string;
	getStorage: () => Storage | undefined;
	getPageUrl: () => URL;
	consentStorageKey: string;
};

export function createLandingHeroTelemetryBridge(args: LandingHeroTelemetryBridgeArgs) {
	const telemetry = createLandingHeroTelemetryController(args);
	return {
		buildTelemetryContext: telemetry.buildContext,
		initialize: telemetry.initialize,
		emitLandingTelemetrySafe: telemetry.emitSafe,
		markEngaged: telemetry.markEngaged,
		setTelemetryConsent: (accepted: boolean) => telemetry.setConsent(accepted),
		trackCta: (action: string, section: string, value: string) =>
			telemetry.trackCta(action, section, value),
		trackScenarioAdjust: (control: string) => telemetry.trackScenarioAdjust(control)
	};
}
