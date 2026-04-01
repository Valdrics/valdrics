import type { PageServerLoad } from './$types';
import { listRelatedPublicContent, mustGetPublicContentEntry } from '$lib/content/publicContent';

export const load: PageServerLoad = ({ params }) => {
	const entry = mustGetPublicContentEntry('proof', params.slug);
	return {
		entry,
		relatedEntries: listRelatedPublicContent(entry)
	};
};
