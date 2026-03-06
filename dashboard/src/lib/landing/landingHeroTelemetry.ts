import type { LandingExperimentAssignments } from './landingExperiment';
import type { FunnelStage, LandingAttribution } from './landingFunnel';

export interface LandingTelemetryContextInput {
	visitorId: string;
	persona: string;
	funnelStage?: FunnelStage;
	pagePath: string;
	referrer: string;
	experiments: LandingExperimentAssignments;
	attribution: LandingAttribution;
}

export function buildLandingTelemetryContext(input: LandingTelemetryContextInput) {
	return {
		visitorId: input.visitorId,
		persona: input.persona,
		funnelStage: input.funnelStage,
		pagePath: input.pagePath,
		referrer: input.referrer || undefined,
		experiment: {
			hero: input.experiments.heroVariant,
			cta: input.experiments.ctaVariant,
			order: input.experiments.sectionOrderVariant
		},
		utm: input.attribution.utm
	};
}

export function normalizeLandingReferrer(referrer: string): string {
	return referrer.trim().slice(0, 200);
}

export function isLandingSignupIntent(value: string): boolean {
	return (
		value === 'start_free' ||
		value === 'book_briefing' ||
		value === 'enterprise_review' ||
		value === 'request_validation_briefing' ||
		value.includes('start_plan') ||
		value.includes('start_roi_assessment')
	);
}
