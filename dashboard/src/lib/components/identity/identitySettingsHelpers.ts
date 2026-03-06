export function isProPlus(currentTier: string | null | undefined): boolean {
	return ['pro', 'enterprise'].includes((currentTier ?? '').toLowerCase());
}

export function apiRootFromPublicApiUrl(publicApiUrl: string): string {
	const cleaned = publicApiUrl.replace(/\/+$/, '');
	return cleaned.replace(/\/api\/v1$/, '');
}

export function scimBaseUrlFromPublicApiUrl(publicApiUrl: string): string {
	return `${apiRootFromPublicApiUrl(publicApiUrl)}/scim/v2`;
}

function normalizeDomain(value: string): string {
	let domain = value.trim().toLowerCase();
	if (!domain) return '';
	if (domain.includes('@')) domain = domain.split('@').pop()?.trim().toLowerCase() ?? '';
	domain = domain.replace(/^\.+/, '').replace(/\.+$/, '');
	return domain;
}

export function parseDomains(raw: string): string[] {
	const tokens = raw
		.split(/[,\n\s]+/g)
		.map((t) => normalizeDomain(t))
		.filter(Boolean);
	const unique: string[] = [];
	for (const domain of tokens) {
		if (!unique.includes(domain)) unique.push(domain);
	}
	return unique;
}
