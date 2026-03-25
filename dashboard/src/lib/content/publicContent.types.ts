export type PublicContentKind = 'docs' | 'resources' | 'insights' | 'proof';

export type PublicContentAudience =
	| 'engineering'
	| 'finance'
	| 'platform'
	| 'security'
	| 'procurement'
	| 'executive';

export type PublicContentStage = 'learn' | 'evaluate' | 'validate';

export interface PublicContentLink {
	label: string;
	href: string;
}

export interface PublicContentSectionInput {
	title: string;
	body: string[];
	bullets?: string[];
}

export interface PublicContentSection extends Omit<PublicContentSectionInput, 'bullets'> {
	bullets: string[];
}

export interface PublicContentRelatedEntry {
	kind: PublicContentKind;
	slug: string;
}

export interface PublicContentEntryInput {
	kind: PublicContentKind;
	slug: string;
	title: string;
	summary: string;
	kicker: string;
	seoTitle: string;
	seoDescription: string;
	updatedAt: string;
	stage: PublicContentStage;
	readingMinutes: number;
	audiences: PublicContentAudience[];
	primaryCta: PublicContentLink;
	secondaryCta?: PublicContentLink;
	downloads?: PublicContentLink[];
	sections: PublicContentSectionInput[];
	related?: PublicContentRelatedEntry[];
}

export interface PublicContentEntry extends Omit<
	PublicContentEntryInput,
	'downloads' | 'related' | 'sections'
> {
	downloads: PublicContentLink[];
	sections: PublicContentSection[];
	related: PublicContentRelatedEntry[];
}
