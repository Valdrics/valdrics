import {
	resolveLandingExperiments,
	resolveOrCreateLandingVisitorId,
	type LandingExperimentAssignments
} from './landingExperiment';
import {
	captureLandingAttribution,
	incrementLandingCtaValue,
	incrementLandingFunnelStage,
	type FunnelStage,
	type LandingAttribution
} from './landingFunnel';
import { emitLandingTelemetry } from './landingTelemetry';
import { buildLandingTelemetryContext, isLandingSignupIntent } from './landingHeroTelemetry';

interface TelemetryStateAccess {
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
}

export interface LandingHeroTelemetryController {
	buildContext: (stage?: FunnelStage) => Parameters<typeof emitLandingTelemetry>[3];
	initialize: () => void;
	emitSafe: (
		name: string,
		section: string,
		value?: string,
		context?: Parameters<typeof emitLandingTelemetry>[3]
	) => void;
	setConsent: (accepted: boolean) => void;
	markEngaged: () => void;
	trackCta: (action: string, section: string, value: string) => void;
	trackScenarioAdjust: (control: string) => void;
}

export function createLandingHeroTelemetryController(
	access: TelemetryStateAccess
): LandingHeroTelemetryController {
	const buildContext = (stage?: FunnelStage) =>
		buildLandingTelemetryContext({
			visitorId: access.getVisitorId(),
			persona: access.getPersona(),
			funnelStage: stage,
			pagePath: access.getPagePath(),
			referrer: access.getReferrer(),
			experiments: access.getExperiments(),
			attribution: access.getAttribution()
		});

	const getTelemetryStorage = (): Storage | undefined =>
		access.getTelemetryEnabled() ? access.getStorage() : undefined;

	const emitSafe = (
		name: string,
		section: string,
		value?: string,
		context?: Parameters<typeof emitLandingTelemetry>[3]
	): void => {
		if (!access.getTelemetryEnabled()) return;
		emitLandingTelemetry(name, section, value, context);
	};

	const initialize = (): void => {
		if (access.getTelemetryInitialized() || !access.getTelemetryEnabled()) {
			return;
		}
		const storage = access.getStorage();
		const visitorId = resolveOrCreateLandingVisitorId(storage);
		const experiments = resolveLandingExperiments(access.getPageUrl(), visitorId);
		const attribution = captureLandingAttribution(access.getPageUrl(), storage);
		access.setVisitorId(visitorId);
		access.setExperiments(experiments);
		access.setAttribution(attribution);
		access.setTelemetryInitialized(true);

		incrementLandingFunnelStage('view', storage);
		emitLandingTelemetry('landing_view', 'landing', 'public', buildContext('view'));
		emitLandingTelemetry(
			'experiment_exposure',
			'landing',
			`${experiments.heroVariant}|${experiments.ctaVariant}|${experiments.sectionOrderVariant}`,
			buildContext('view')
		);
	};

	const setConsent = (accepted: boolean): void => {
		access.setTelemetryEnabled(accepted);
		access.setCookieBannerVisible(false);
		const storage = access.getStorage();
		storage?.setItem(access.consentStorageKey, accepted ? 'accepted' : 'rejected');
		if (accepted) {
			initialize();
		}
	};

	const markEngaged = (): void => {
		if (access.getEngagedCaptured()) {
			return;
		}
		access.setEngagedCaptured(true);
		incrementLandingFunnelStage('engaged', getTelemetryStorage());
		emitSafe('landing_engaged', 'landing', 'interactive', buildContext('engaged'));
	};

	const trackCta = (action: string, section: string, value: string): void => {
		incrementLandingCtaValue(value, getTelemetryStorage());
		incrementLandingFunnelStage('cta', getTelemetryStorage());
		emitSafe(action, section, value, buildContext('cta'));
		if (!isLandingSignupIntent(value)) {
			return;
		}
		incrementLandingFunnelStage('signup_intent', getTelemetryStorage());
		emitSafe('signup_intent', section, value, buildContext('signup_intent'));
	};

	const trackScenarioAdjust = (control: string): void => {
		markEngaged();
		if (access.getScenarioAdjustCaptured()) {
			return;
		}
		access.setScenarioAdjustCaptured(true);
		emitSafe('scenario_adjust', 'simulator', control, buildContext('engaged'));
	};

	return {
		buildContext,
		initialize,
		emitSafe,
		setConsent,
		markEngaged,
		trackCta,
		trackScenarioAdjust
	};
}
