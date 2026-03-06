import type { LandingExperimentAssignments } from './landingExperiment';
import type { LandingUtmParams } from './landingFunnel';

interface LandingHrefOptions {
	persona: string;
	utm: LandingUtmParams;
}

export interface LandingSignupHrefOptions extends LandingHrefOptions {
	basePath: string;
	intent: string;
	includeExperimentQueryParams: boolean;
	experiments: LandingExperimentAssignments;
	extraParams?: Record<string, string>;
}

export interface LandingSalesHrefOptions extends LandingHrefOptions {
	path: string;
	source: string;
}

function appendUtmParams(params: URLSearchParams, utm: LandingUtmParams): void {
	if (utm.source) params.set('utm_source', utm.source);
	if (utm.medium) params.set('utm_medium', utm.medium);
	if (utm.campaign) params.set('utm_campaign', utm.campaign);
	if (utm.term) params.set('utm_term', utm.term);
	if (utm.content) params.set('utm_content', utm.content);
}

export function buildLandingSignupHref(options: LandingSignupHrefOptions): string {
	const params = new URLSearchParams({
		intent: options.intent,
		persona: options.persona,
		entry: 'landing'
	});
	for (const [key, value] of Object.entries(options.extraParams || {})) {
		if (value) {
			params.set(key, value);
		}
	}
	if (options.includeExperimentQueryParams) {
		params.set('exp_hero', options.experiments.heroVariant);
		params.set('exp_cta', options.experiments.ctaVariant);
		params.set('exp_order', options.experiments.sectionOrderVariant);
	}
	appendUtmParams(params, options.utm);
	return `${options.basePath}/auth/login?${params.toString()}`;
}

export function buildLandingSalesHref(options: LandingSalesHrefOptions): string {
	const params = new URLSearchParams({
		entry: 'landing',
		source: options.source,
		persona: options.persona
	});
	appendUtmParams(params, options.utm);
	return `${options.path}?${params.toString()}`;
}
