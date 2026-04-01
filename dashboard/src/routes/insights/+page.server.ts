import type { PageServerLoad } from './$types';
import { listPublicContent } from '$lib/content/publicContent';

export const load: PageServerLoad = () => ({
	insights: listPublicContent('insights')
});
