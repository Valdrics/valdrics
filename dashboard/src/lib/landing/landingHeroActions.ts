import { buildLandingSalesHref, buildLandingSignupHref } from '$lib/landing/landingHeroLinks';
import type { LandingExperimentAssignments } from '$lib/landing/landingExperiment';
import type { LandingAttribution } from '$lib/landing/landingFunnel';

type HeroSignupArgs = {
	basePath: string;
	intent: string;
	persona: string;
	includeExperimentQueryParams: boolean;
	experiments: LandingExperimentAssignments;
	utm: LandingAttribution['utm'];
	extraParams?: Record<string, string>;
};

type HeroSalesArgs = {
	path: string;
	source: string;
	persona: string;
	utm: LandingAttribution['utm'];
};

type LandingSelectionArgs = {
	index: number;
	size: number;
	assign: (value: number) => void;
	eventName: string;
	section: string;
	value: string | undefined;
	markEngaged: () => void;
	emitLandingTelemetrySafe: (
		action: string,
		section: string,
		value: string | undefined,
		context: Record<string, unknown>
	) => void;
	buildTelemetryContext: (funnelStage?: string) => Record<string, unknown>;
};

export function buildLandingHeroSignupPath(args: HeroSignupArgs): string {
	return buildLandingSignupHref({
		basePath: args.basePath,
		intent: args.intent,
		persona: args.persona,
		includeExperimentQueryParams: args.includeExperimentQueryParams,
		experiments: args.experiments,
		utm: args.utm,
		extraParams: args.extraParams ?? {}
	});
}

export function buildLandingHeroSalesPath(args: HeroSalesArgs): string {
	return buildLandingSalesHref(args);
}

export function trackIndexedLandingSelection(args: LandingSelectionArgs): void {
	if (args.index < 0 || args.index >= args.size) return;
	args.assign(args.index);
	args.markEngaged();
	args.emitLandingTelemetrySafe(
		args.eventName,
		args.section,
		args.value,
		args.buildTelemetryContext('engaged')
	);
}
