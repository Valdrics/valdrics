import { assets, base } from '$app/paths';
import { redirect } from '@sveltejs/kit';
import { HERO_ROLE_CONTEXT } from '$lib/landing/heroContent.core';
import { resolvePublicLandingCurrencyFromHeaders } from '$lib/landing/geoCurrency';
import type { LandingSignalSnapshot } from '$lib/landing/landingSignalSnapshots';
import { LANDING_SIGNAL_SNAPSHOTS } from '$lib/landing/landingSignalSnapshots';
import {
	resolveLandingExperiments,
	shouldIncludeExperimentQueryParams
} from '$lib/landing/landingExperiment';
import {
	DEFAULT_EXPERIMENT_ASSIGNMENTS,
	resolveLandingMotionProfile
} from '$lib/landing/landingHeroConfig';
import type { PageServerLoad } from './$types';

const MOTION_QUERY_KEY = 'motion';
const SUPPORTED_MOTION_VALUES = new Set(['subtle', 'cinematic']);
function getDefaultLandingSignalSnapshot(): LandingSignalSnapshot {
	const snapshot = LANDING_SIGNAL_SNAPSHOTS[0];
	if (!snapshot) {
		throw new Error('Landing signal snapshots require at least one snapshot.');
	}
	return snapshot;
}

const DEFAULT_SIGNAL_SNAPSHOT = getDefaultLandingSignalSnapshot();

function buildLandingHeroData(url: URL, requestHeaders: Headers) {
	const initialExperiments = resolveLandingExperiments(url, DEFAULT_EXPERIMENT_ASSIGNMENTS.seed);
	const heroContext =
		HERO_ROLE_CONTEXT[initialExperiments.buyerPersonaDefault] ?? HERO_ROLE_CONTEXT.cto;

	return {
		initialExperiments,
		includeExperimentQueryParams: shouldIncludeExperimentQueryParams(url, false),
		initialMotionProfile: resolveLandingMotionProfile(url),
		canonicalUrl: new URL(url.pathname, url.origin).toString(),
		ogImageUrl: new URL(`${assets}/og-image.png`, url.origin).toString(),
		detectedCurrencyCode: resolvePublicLandingCurrencyFromHeaders(requestHeaders),
		buyerPersonaId: initialExperiments.buyerPersonaDefault,
		heroPrimaryIntent: heroContext.primaryIntent,
		heroTitle:
			initialExperiments.heroVariant === 'from_metrics_to_control'
				? heroContext.metricsTitle
				: heroContext.controlTitle,
		heroSubtitle: heroContext.subtitle,
		initialSnapshot: DEFAULT_SIGNAL_SNAPSHOT
	};
}

export const load: PageServerLoad = async ({ url, locals, request }) => {
	const sessionResult = await locals.safeGetSession().catch(() => ({ user: null }));
	if (sessionResult.user) {
		throw redirect(307, `${base}/dashboard${url.search}`);
	}

	const rawMotion = url.searchParams.get(MOTION_QUERY_KEY);
	if (!rawMotion) {
		return {
			landingHero: buildLandingHeroData(url, request.headers)
		};
	}

	const normalizedMotion = rawMotion.trim().toLowerCase();
	const isSupportedMotion = SUPPORTED_MOTION_VALUES.has(normalizedMotion);
	const nextUrl = new URL(url);

	if (!isSupportedMotion) {
		nextUrl.searchParams.delete(MOTION_QUERY_KEY);
		throw redirect(308, `${nextUrl.pathname}${nextUrl.search}`);
	}

	if (rawMotion !== normalizedMotion) {
		nextUrl.searchParams.set(MOTION_QUERY_KEY, normalizedMotion);
		throw redirect(308, `${nextUrl.pathname}${nextUrl.search}`);
	}

	return {
		landingHero: buildLandingHeroData(url, request.headers)
	};
};
