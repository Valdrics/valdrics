import { error } from '@sveltejs/kit';
import { z } from 'zod';

import { RAW_PUBLIC_CONTENT_DOCS } from './publicContent.docs';
import { RAW_PUBLIC_CONTENT_INSIGHTS } from './publicContent.insights';
import { RAW_PUBLIC_CONTENT_PROOF } from './publicContent.proof';
import { RAW_PUBLIC_CONTENT_RESOURCES } from './publicContent.resources';

const PublicContentKindSchema = z.enum(['docs', 'resources', 'insights', 'proof']);
const PublicContentAudienceSchema = z.enum([
	'engineering',
	'finance',
	'platform',
	'security',
	'procurement',
	'executive'
]);
const PublicContentStageSchema = z.enum(['learn', 'evaluate', 'validate']);

const PublicContentLinkSchema = z.object({
	label: z.string().min(1),
	href: z.string().min(1)
});

const PublicContentSectionSchema = z.object({
	title: z.string().min(1),
	body: z.array(z.string().min(1)).min(1),
	bullets: z.array(z.string().min(1)).default([])
});

const PublicContentRelatedEntrySchema = z.object({
	kind: PublicContentKindSchema,
	slug: z.string().regex(/^[a-z0-9-]+$/)
});

const PublicContentEntrySchema = z.object({
	kind: PublicContentKindSchema,
	slug: z.string().regex(/^[a-z0-9-]+$/),
	title: z.string().min(1),
	summary: z.string().min(1),
	kicker: z.string().min(1),
	seoTitle: z.string().min(1),
	seoDescription: z.string().min(1),
	updatedAt: z.string().datetime(),
	stage: PublicContentStageSchema,
	readingMinutes: z.number().int().positive(),
	audiences: z.array(PublicContentAudienceSchema).min(1),
	primaryCta: PublicContentLinkSchema,
	secondaryCta: PublicContentLinkSchema.optional(),
	downloads: z.array(PublicContentLinkSchema).default([]),
	sections: z.array(PublicContentSectionSchema).min(2),
	related: z.array(PublicContentRelatedEntrySchema).default([])
});

export type PublicContentKind = z.infer<typeof PublicContentKindSchema>;
export type PublicContentEntry = z.infer<typeof PublicContentEntrySchema>;

const RAW_PUBLIC_CONTENT = [
	...RAW_PUBLIC_CONTENT_DOCS,
	...RAW_PUBLIC_CONTENT_RESOURCES,
	...RAW_PUBLIC_CONTENT_INSIGHTS,
	...RAW_PUBLIC_CONTENT_PROOF
] as const;

const PUBLIC_CONTENT = PublicContentEntrySchema.array().parse(RAW_PUBLIC_CONTENT);

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
