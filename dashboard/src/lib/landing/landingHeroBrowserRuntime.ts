import { mountLandingHeroRuntime } from '$lib/landing/landingHeroRuntime';
import type { FunnelStage } from '$lib/landing/landingFunnel';
import type { LandingTelemetryContext } from '$lib/landing/landingTelemetry';

type LandingHeroBrowserRuntimeArgs = {
	browserEnabled: boolean;
	windowRef: Window;
	documentRef: Document;
	signalMapElement: HTMLDivElement | null;
	geoCurrencyHintTimeoutMs: number;
	applyGeoCurrencyHint: (signal: AbortSignal) => Promise<void>;
	consentStorageKey: string;
	scrollMilestones: readonly number[];
	initializeTelemetry: () => void;
	markEngaged: () => void;
	buildTelemetryContext: (funnelStage?: FunnelStage) => LandingTelemetryContext;
	emitLandingTelemetrySafe: (
		action: string,
		section: string,
		value: string | undefined,
		context: LandingTelemetryContext
	) => void;
	setPrefersReducedMotion: (value: boolean) => void;
	setPageReferrer: (value: string) => void;
	setTelemetryEnabled: (value: boolean) => void;
	setCookieBannerVisible: (value: boolean) => void;
	setDocumentVisible: (value: boolean) => void;
	setSignalMapInView: (value: boolean) => void;
	setLandingScrollProgressPct: (value: number) => void;
};

export function mountLandingHeroBrowserRuntime(args: LandingHeroBrowserRuntimeArgs): () => void {
	return mountLandingHeroRuntime({
		browserEnabled: args.browserEnabled,
		windowRef: args.windowRef,
		documentRef: args.documentRef,
		signalMapElement: args.signalMapElement,
		geoCurrencyHintTimeoutMs: args.geoCurrencyHintTimeoutMs,
		applyGeoCurrencyHint: args.applyGeoCurrencyHint,
		onReducedMotionChange: args.setPrefersReducedMotion,
		setPageReferrer: args.setPageReferrer,
		consentStorageKey: args.consentStorageKey,
		onConsentAccepted: () => {
			args.setTelemetryEnabled(true);
			args.initializeTelemetry();
		},
		onConsentRejected: () => args.setTelemetryEnabled(false),
		onConsentUnknown: () => args.setCookieBannerVisible(true),
		scrollMilestones: args.scrollMilestones,
		onDocumentVisibilityChange: args.setDocumentVisible,
		onSignalMapVisibilityChange: args.setSignalMapInView,
		onSectionView: (sectionId) => {
			args.markEngaged();
			args.emitLandingTelemetrySafe(
				'section_view',
				'landing_section',
				sectionId,
				args.buildTelemetryContext('engaged')
			);
		},
		onScrollProgressChange: args.setLandingScrollProgressPct,
		onScrollMilestone: (milestone) => {
			if (milestone >= 50) {
				args.markEngaged();
			}
			args.emitLandingTelemetrySafe(
				'scroll_depth',
				'landing',
				`${milestone}`,
				args.buildTelemetryContext('engaged')
			);
		}
	});
}
