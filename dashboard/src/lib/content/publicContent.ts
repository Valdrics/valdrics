import { error } from '@sveltejs/kit';

import type {
	PublicContentEntry,
	PublicContentEntryInput,
	PublicContentKind
} from './publicContent.types';
import { RAW_PUBLIC_CONTENT_DOCS } from './publicContent.docs';
import { RAW_PUBLIC_CONTENT_INSIGHTS } from './publicContent.insights';
import { RAW_PUBLIC_CONTENT_PROOF } from './publicContent.proof';
import { RAW_PUBLIC_CONTENT_RESOURCES } from './publicContent.resources';

const RAW_PUBLIC_CONTENT = [
	...RAW_PUBLIC_CONTENT_DOCS,
	...RAW_PUBLIC_CONTENT_RESOURCES,
	...RAW_PUBLIC_CONTENT_INSIGHTS,
	...RAW_PUBLIC_CONTENT_PROOF
] as const satisfies readonly PublicContentEntryInput[];

function normalizePublicContentEntry(entry: PublicContentEntryInput): PublicContentEntry {
	return {
		...entry,
		downloads: [...(entry.downloads ?? [])],
		sections: entry.sections.map((section) => ({
			...section,
			bullets: [...(section.bullets ?? [])]
		})),
		related: [...(entry.related ?? [])]
	};
}

const PUBLIC_CONTENT = RAW_PUBLIC_CONTENT.map(normalizePublicContentEntry);

const byKey = new Map<string, PublicContentEntry>();

for (const entry of PUBLIC_CONTENT) {
	const key = `${entry.kind}:${entry.slug}`;
	if (byKey.has(key)) {
		throw new Error(`Duplicate public content entry: ${key}`);
	}
	byKey.set(key, entry);
}

for (const entry of PUBLIC_CONTENT) {
	for (const related of entry.related) {
		if (!byKey.has(`${related.kind}:${related.slug}`)) {
			throw new Error(`Unknown related public content entry: ${related.kind}:${related.slug}`);
		}
	}
}

export function listPublicContent(kind: PublicContentKind): PublicContentEntry[] {
	return PUBLIC_CONTENT.filter((entry) => entry.kind === kind);
}

export function getPublicContentEntry(
	kind: PublicContentKind,
	slug: string
): PublicContentEntry | undefined {
	return byKey.get(`${kind}:${slug}`);
}

export function mustGetPublicContentEntry(
	kind: PublicContentKind,
	slug: string
): PublicContentEntry {
	const entry = getPublicContentEntry(kind, slug);
	if (!entry) {
		throw error(404, `Unknown public content entry: ${kind}/${slug}`);
	}
	return entry;
}

export function listRelatedPublicContent(entry: PublicContentEntry): PublicContentEntry[] {
	return entry.related
		.map((related) => getPublicContentEntry(related.kind, related.slug))
		.filter((relatedEntry): relatedEntry is PublicContentEntry => Boolean(relatedEntry));
}

export function listPublicSitemapEntries(): Array<{
	path: string;
	changefreq: 'weekly' | 'monthly';
	priority: number;
	lastmod: string;
}> {
	return PUBLIC_CONTENT.map((entry) => ({
		path: `/${entry.kind}/${entry.slug}`,
		changefreq: entry.kind === 'insights' ? 'weekly' : 'monthly',
		priority: entry.kind === 'docs' ? 0.72 : entry.kind === 'proof' ? 0.74 : 0.7,
		lastmod: entry.updatedAt
	}));
}

export type { PublicContentEntry, PublicContentEntryInput, PublicContentKind };
