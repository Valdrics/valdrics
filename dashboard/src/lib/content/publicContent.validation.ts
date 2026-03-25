import { z } from 'zod';

import type { PublicContentEntryInput } from './publicContent.types';
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

const RAW_PUBLIC_CONTENT = [
	...RAW_PUBLIC_CONTENT_DOCS,
	...RAW_PUBLIC_CONTENT_RESOURCES,
	...RAW_PUBLIC_CONTENT_INSIGHTS,
	...RAW_PUBLIC_CONTENT_PROOF
] as const satisfies readonly PublicContentEntryInput[];

export function validatePublicContentRegistry(): PublicContentEntryInput[] {
	return PublicContentEntrySchema.array().parse(RAW_PUBLIC_CONTENT);
}
