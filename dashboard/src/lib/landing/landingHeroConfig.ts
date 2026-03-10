import type { LandingExperimentAssignments } from '$lib/landing/landingExperiment';

export type LandingMotionProfile = 'subtle' | 'cinematic';

export const DEFAULT_EXPERIMENT_ASSIGNMENTS: LandingExperimentAssignments = Object.freeze({
	buyerPersonaDefault: 'cto',
	heroVariant: 'control_every_dollar',
	ctaVariant: 'start_free',
	sectionOrderVariant: 'problem_first',
	seed: 'default'
});

export const SNAPSHOT_ROTATION_MS = 4400;
export const DEMO_ROTATION_MS = 3200;
export const LANDING_SCROLL_MILESTONES = Object.freeze([25, 50, 75, 95]);
export const LANDING_CONSENT_KEY = 'valdrics.cookie_consent.v1';
export const GEO_CURRENCY_HINT_TIMEOUT_MS = 1200;

export function resolveLandingMotionProfile(url: URL): LandingMotionProfile {
	const value = url.searchParams.get('motion')?.trim().toLowerCase();
	return value === 'cinematic' ? 'cinematic' : 'subtle';
}
