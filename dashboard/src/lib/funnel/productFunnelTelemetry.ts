import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { readLandingAttribution, type LandingAttribution } from '$lib/landing/landingFunnel';
import type { StorageLike } from '$lib/landing/landingExperiment';

export type ProductFunnelStage =
	| 'connection_verified'
	| 'pricing_viewed'
	| 'checkout_started'
	| 'first_value_activated';

export interface ProductFunnelPayload {
	stage: ProductFunnelStage;
	provider?: string;
	source?: string;
	current_tier?: string;
	occurred_at?: string;
	attribution?: {
		persona?: string;
		intent?: string;
		page_path?: string;
		first_touch_at?: string;
		last_touch_at?: string;
		utm?: {
			source?: string;
			medium?: string;
			campaign?: string;
			term?: string;
			content?: string;
		};
	};
}

export interface ProductFunnelEventInput {
	accessToken: string;
	stage: ProductFunnelStage;
	tenantId?: string | null;
	url: URL;
	currentTier?: string | null;
	persona?: string | null;
	provider?: string | null;
	source?: string | null;
	occurredAt?: Date;
	storage?: StorageLike | undefined;
	force?: boolean;
	send?: (
		url: string,
		body?: unknown,
		options?: { headers?: Record<string, string> }
	) => Promise<Response>;
}

const PRODUCT_FUNNEL_STORAGE_KEY = 'valdrics.product.funnel.v1';
const MAX_TOKEN_LENGTH = 96;
const MAX_PATH_LENGTH = 256;

function normalizeToken(input: string | null | undefined, maxLength = MAX_TOKEN_LENGTH): string | undefined {
	const normalized = (input || '').trim().toLowerCase();
	if (!normalized) {
		return undefined;
	}
	return normalized.slice(0, maxLength);
}

function normalizePath(url: URL): string {
	return `${url.pathname}${url.search}`.slice(0, MAX_PATH_LENGTH);
}

function parseCurrentUrlUtm(url: URL): LandingAttribution['utm'] {
	return {
		source: normalizeToken(url.searchParams.get('utm_source')),
		medium: normalizeToken(url.searchParams.get('utm_medium')),
		campaign: normalizeToken(url.searchParams.get('utm_campaign')),
		term: normalizeToken(url.searchParams.get('utm_term')),
		content: normalizeToken(url.searchParams.get('utm_content'))
	};
}

function mergeAttribution(url: URL, stored: LandingAttribution): ProductFunnelPayload['attribution'] {
	const currentUrlUtm = parseCurrentUrlUtm(url);
	return {
		intent: normalizeToken(url.searchParams.get('intent'), 64),
		page_path: normalizePath(url),
		first_touch_at: stored.firstTouchAt,
		last_touch_at: stored.lastTouchAt,
		utm: {
			source: currentUrlUtm.source ?? normalizeToken(stored.utm.source),
			medium: currentUrlUtm.medium ?? normalizeToken(stored.utm.medium),
			campaign: currentUrlUtm.campaign ?? normalizeToken(stored.utm.campaign),
			term: currentUrlUtm.term ?? normalizeToken(stored.utm.term),
			content: currentUrlUtm.content ?? normalizeToken(stored.utm.content)
		}
	};
}

function readStageStore(storage: StorageLike | undefined): Record<string, true> {
	if (!storage) {
		return {};
	}
	try {
		const raw = storage.getItem(PRODUCT_FUNNEL_STORAGE_KEY);
		if (!raw) {
			return {};
		}
		const parsed = JSON.parse(raw) as Record<string, true>;
		return parsed && typeof parsed === 'object' ? parsed : {};
	} catch {
		return {};
	}
}

function writeStageStore(storage: StorageLike | undefined, store: Record<string, true>): void {
	if (!storage) {
		return;
	}
	storage.setItem(PRODUCT_FUNNEL_STORAGE_KEY, JSON.stringify(store));
}

function buildStageKey(stage: ProductFunnelStage, tenantId?: string | null): string {
	return `${tenantId || 'unknown'}:${stage}`;
}

function defaultStorage(): StorageLike | undefined {
	if (typeof window === 'undefined') {
		return undefined;
	}
	return window.localStorage;
}

export function buildProductFunnelAttributionContext(input: {
	url: URL;
	persona?: string | null;
	storage?: StorageLike | undefined;
}): NonNullable<ProductFunnelPayload['attribution']> {
	const storage = input.storage ?? defaultStorage();
	const storedAttribution = readLandingAttribution(storage);
	return {
		...mergeAttribution(input.url, storedAttribution),
		persona: normalizeToken(input.persona, 64)
	};
}

export function buildProductFunnelPayload(
	input: Omit<ProductFunnelEventInput, 'accessToken' | 'send' | 'force'>
): ProductFunnelPayload {
	const storage = input.storage ?? defaultStorage();
	return {
		stage: input.stage,
		provider: normalizeToken(input.provider, 32),
		source: normalizeToken(input.source, 64),
		current_tier: normalizeToken(input.currentTier, 20),
		occurred_at: (input.occurredAt ?? new Date()).toISOString(),
		attribution: buildProductFunnelAttributionContext({
			url: input.url,
			persona: input.persona,
			storage
		})
	};
}

export async function trackProductFunnelStage(input: ProductFunnelEventInput): Promise<boolean> {
	const storage = input.storage ?? defaultStorage();
	const stageKey = buildStageKey(input.stage, input.tenantId);
	const existing = readStageStore(storage);
	if (!input.force && existing[stageKey]) {
		return false;
	}

	const payload = buildProductFunnelPayload({
		stage: input.stage,
		tenantId: input.tenantId,
		url: input.url,
		currentTier: input.currentTier,
		persona: input.persona,
		provider: input.provider,
		source: input.source,
		occurredAt: input.occurredAt,
		storage
	});
	const send =
		input.send ??
		((requestUrl, body, options) =>
			api.post(requestUrl, body, {
				headers: {
					Authorization: `Bearer ${input.accessToken}`,
					...(options?.headers ?? {})
				}
			}));

	const response = await send(edgeApiPath('/usage/funnel'), payload, {
		headers: {
			Authorization: `Bearer ${input.accessToken}`
		}
	});
	if (!response.ok) {
		return false;
	}
	writeStageStore(storage, {
		...existing,
		[stageKey]: true
	});
	return true;
}
