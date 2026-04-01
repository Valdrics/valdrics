import type { PageServerLoad } from './$types';
import { mustGetPublicContentEntry } from '$lib/content/publicContent';

export const load: PageServerLoad = () => ({
	operatingGuides: [
		mustGetPublicContentEntry('docs', 'connect-first-provider'),
		mustGetPublicContentEntry('docs', 'owner-routing-and-approval-path'),
		mustGetPublicContentEntry('docs', 'decision-history-and-export-records')
	]
});
