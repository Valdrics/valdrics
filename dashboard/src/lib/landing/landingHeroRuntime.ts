import { normalizeLandingReferrer } from '$lib/landing/landingHeroTelemetry';
import { observeReducedMotionPreference } from '$lib/landing/reducedMotion';
import { setupLandingHeroLifecycle } from '$lib/landing/landingHeroLifecycle';

type LandingHeroRuntimeArgs = {
	browserEnabled: boolean;
	windowRef: Window;
	documentRef: Document;
	signalMapElement: HTMLDivElement | null;
	geoCurrencyHintTimeoutMs: number;
	applyGeoCurrencyHint: (signal: AbortSignal) => Promise<void>;
	onReducedMotionChange: (value: boolean) => void;
	setPageReferrer: (value: string) => void;
	consentStorageKey: string;
	onConsentAccepted: () => void;
	onConsentRejected: () => void;
	onConsentUnknown: () => void;
	scrollMilestones: readonly number[];
	onDocumentVisibilityChange: (isVisible: boolean) => void;
	onSignalMapVisibilityChange: (isVisible: boolean) => void;
	onSectionView: (sectionId: string) => void;
	onScrollProgressChange: (progressPct: number) => void;
	onScrollMilestone: (milestone: number) => void;
};

export function mountLandingHeroRuntime(args: LandingHeroRuntimeArgs): () => void {
	const geoCurrencyController = new AbortController();
	const geoCurrencyTimeout = setTimeout(
		() => geoCurrencyController.abort(),
		args.geoCurrencyHintTimeoutMs
	);
	void args.applyGeoCurrencyHint(geoCurrencyController.signal).finally(() => {
		clearTimeout(geoCurrencyTimeout);
	});

	const storage = args.browserEnabled ? args.windowRef.localStorage : undefined;
	const stopReducedMotionObservation = observeReducedMotionPreference(args.windowRef, (value) => {
		args.onReducedMotionChange(value);
	});
	args.setPageReferrer(normalizeLandingReferrer(args.documentRef.referrer));

	const consent = storage?.getItem(args.consentStorageKey);
	if (consent === 'accepted') {
		args.onConsentAccepted();
	} else if (consent === 'rejected') {
		args.onConsentRejected();
	} else {
		args.onConsentUnknown();
	}

	const stopLandingLifecycle = setupLandingHeroLifecycle({
		documentRef: args.documentRef,
		windowRef: args.windowRef,
		signalMapElement: args.signalMapElement,
		scrollMilestones: args.scrollMilestones,
		onDocumentVisibilityChange: args.onDocumentVisibilityChange,
		onSignalMapVisibilityChange: args.onSignalMapVisibilityChange,
		onSectionView: args.onSectionView,
		onScrollProgressChange: args.onScrollProgressChange,
		onScrollMilestone: args.onScrollMilestone
	});

	return () => {
		geoCurrencyController.abort();
		clearTimeout(geoCurrencyTimeout);
		stopReducedMotionObservation();
		stopLandingLifecycle();
	};
}
