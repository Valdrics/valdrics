export interface ResolveGeoCurrencyHintOptions {
	requestEndpoint: string;
	requestOrigin: string;
	hostname?: string;
	supportedCurrencyCodes: ReadonlySet<string>;
	signal: AbortSignal;
	fetchFn?: typeof fetch;
}

export async function resolveGeoCurrencyHint(
	options: ResolveGeoCurrencyHintOptions
): Promise<string | null> {
	const host = options.hostname?.toLowerCase();
	if (host === 'localhost' || host === '127.0.0.1' || host === '::1') {
		return null;
	}

	let requestUrl: string;
	try {
		requestUrl = new URL(options.requestEndpoint, options.requestOrigin).toString();
	} catch {
		return null;
	}

	const executeFetch = options.fetchFn || fetch;
	try {
		const response = await executeFetch(requestUrl, {
			method: 'GET',
			headers: { accept: 'application/json' },
			cache: 'no-store',
			signal: options.signal
		});
		if (!response.ok) {
			return null;
		}
		const payload = (await response.json()) as { currencyCode?: string };
		const currencyCode = String(payload.currencyCode ?? '')
			.trim()
			.toUpperCase();
		if (!options.supportedCurrencyCodes.has(currencyCode)) {
			return null;
		}
		return currencyCode;
	} catch {
		return null;
	}
}
