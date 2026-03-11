export type PublicBuyerPersona = 'cto' | 'finops' | 'security' | 'cfo';
export type PublicBuyingMotion = 'self_serve_first' | 'enterprise_first';

interface PublicPathOptions {
	entry: string;
	source?: string;
	persona?: PublicBuyerPersona;
	extraParams?: Record<string, string | undefined>;
}

interface PublicSignupHrefOptions extends PublicPathOptions {
	intent?: string;
	mode?: 'login' | 'signup';
}

interface PublicSalesHrefOptions extends PublicPathOptions {
	intent?: string;
}

const UTM_QUERY_KEYS = Object.freeze([
	'utm_source',
	'utm_medium',
	'utm_campaign',
	'utm_term',
	'utm_content'
]);

const ENTERPRISE_SIGNAL_PATTERNS = Object.freeze([
	'enterprise',
	'procurement',
	'security',
	'compliance',
	'risk',
	'privacy',
	'scim',
	'private',
	'diligence',
	'executive',
	'leadership',
	'legal',
	'board',
	'abm',
	'rfp',
	'rfi'
]);

const SELF_SERVE_SIGNAL_PATTERNS = Object.freeze([
	'docs',
	'documentation',
	'resource',
	'insight',
	'guide',
	'playbook',
	'roi',
	'simulator',
	'pricing',
	'trial',
	'developer',
	'self serve',
	'self_serve'
]);

function normalizeToken(value: string | null | undefined): string {
	return (value || '').trim().toLowerCase();
}

function normalizeOptionalToken(value: string | null | undefined): string | undefined {
	const token = normalizeToken(value);
	return token || undefined;
}

function mapPersonaToken(value: string | null | undefined): PublicBuyerPersona | undefined {
	const token = normalizeToken(value);
	if (!token) {
		return undefined;
	}

	switch (token) {
		case 'cto':
		case 'engineering':
		case 'engineer':
		case 'platform':
		case 'operator':
		case 'ops':
		case 'devops':
		case 'infra':
			return 'cto';
		case 'finops':
		case 'finance':
		case 'financeops':
		case 'fpanda':
			return 'finops';
		case 'security':
		case 'compliance':
		case 'risk':
		case 'privacy':
		case 'identity':
			return 'security';
		case 'cfo':
		case 'executive':
		case 'leadership':
		case 'procurement':
		case 'board':
		case 'legal':
			return 'cfo';
		default:
			return undefined;
	}
}

function collectSignalValues(url: URL): string[] {
	return [
		url.searchParams.get('buyer'),
		url.searchParams.get('persona'),
		url.searchParams.get('entry'),
		url.searchParams.get('source'),
		url.searchParams.get('intent'),
		url.searchParams.get('utm_source'),
		url.searchParams.get('utm_medium'),
		url.searchParams.get('utm_campaign'),
		url.searchParams.get('utm_term'),
		url.searchParams.get('utm_content')
	]
		.map((value) => normalizeOptionalToken(value))
		.filter((value): value is string => Boolean(value));
}

function inferPersonaFromSignals(signalValues: string[]): PublicBuyerPersona | undefined {
	for (const signal of signalValues) {
		const directMatch = mapPersonaToken(signal);
		if (directMatch) {
			return directMatch;
		}
	}

	const joinedSignals = signalValues.join(' ');
	if (/(security|compliance|risk|privacy|identity|scim)/.test(joinedSignals)) {
		return 'security';
	}
	if (/(procurement|executive|leadership|board|legal|cfo)/.test(joinedSignals)) {
		return 'cfo';
	}
	if (/(finops|financeops|cloud cost|cost review|allocation|chargeback)/.test(joinedSignals)) {
		return 'finops';
	}
	if (/(engineering|platform|developer|docs|api|operator|workload)/.test(joinedSignals)) {
		return 'cto';
	}
	return undefined;
}

function hasAnySignal(signalValues: string[], patterns: readonly string[]): boolean {
	const joinedSignals = signalValues.join(' ');
	return patterns.some((pattern) => joinedSignals.includes(pattern));
}

function setParams(
	params: URLSearchParams,
	values: Record<string, string | undefined>,
	overwriteExisting = false
): void {
	for (const [key, value] of Object.entries(values)) {
		if (!value) {
			continue;
		}
		if (!overwriteExisting && params.has(key)) {
			continue;
		}
		params.set(key, value);
	}
}

function preserveUtmParams(params: URLSearchParams, currentUrl: URL): void {
	for (const key of UTM_QUERY_KEYS) {
		if (params.has(key)) {
			continue;
		}
		const value = normalizeOptionalToken(currentUrl.searchParams.get(key));
		if (value) {
			params.set(key, value);
		}
	}
}

export function resolvePublicBuyerPersona(url: URL): PublicBuyerPersona | undefined {
	return (
		mapPersonaToken(url.searchParams.get('buyer')) ||
		mapPersonaToken(url.searchParams.get('persona')) ||
		inferPersonaFromSignals(collectSignalValues(url))
	);
}

export function resolvePublicBuyingMotion(
	url: URL,
	defaultMotion: PublicBuyingMotion = 'self_serve_first'
): PublicBuyingMotion {
	const signalValues = collectSignalValues(url);
	const persona = resolvePublicBuyerPersona(url);

	if (persona === 'security' || persona === 'cfo') {
		return 'enterprise_first';
	}
	if (persona === 'cto' || persona === 'finops') {
		return 'self_serve_first';
	}
	if (hasAnySignal(signalValues, ENTERPRISE_SIGNAL_PATTERNS)) {
		return 'enterprise_first';
	}
	if (hasAnySignal(signalValues, SELF_SERVE_SIGNAL_PATTERNS)) {
		return 'self_serve_first';
	}
	return defaultMotion;
}

export function appendPublicAttribution(
	href: string,
	currentUrl: URL,
	options: PublicPathOptions
): string {
	if (/^(https?:|mailto:)/i.test(href)) {
		return href;
	}

	const parsed = new URL(href, currentUrl.origin);
	const persona = options.persona || resolvePublicBuyerPersona(currentUrl);

	setParams(parsed.searchParams, {
		entry: options.entry,
		source: options.source || options.entry,
		persona,
		...(options.extraParams || {})
	});
	preserveUtmParams(parsed.searchParams, currentUrl);

	return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

export function buildPublicSignupHref(
	basePath: string,
	currentUrl: URL,
	options: PublicSignupHrefOptions
): string {
	return appendPublicAttribution(`${basePath}/auth/login`, currentUrl, {
		entry: options.entry,
		source: options.source,
		persona: options.persona,
		extraParams: {
			mode: options.mode || 'signup',
			intent: options.intent,
			...(options.extraParams || {})
		}
	});
}

export function buildPublicEnterpriseHref(
	basePath: string,
	currentUrl: URL,
	options: PublicPathOptions
): string {
	return appendPublicAttribution(`${basePath}/enterprise`, currentUrl, options);
}

export function buildPublicSalesHref(
	basePath: string,
	currentUrl: URL,
	options: PublicSalesHrefOptions
): string {
	return appendPublicAttribution(`${basePath}/talk-to-sales`, currentUrl, {
		entry: options.entry,
		source: options.source,
		persona: options.persona,
		extraParams: {
			intent: options.intent,
			...(options.extraParams || {})
		}
	});
}
