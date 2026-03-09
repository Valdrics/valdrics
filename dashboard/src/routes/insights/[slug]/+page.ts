import type { PageLoad } from './$types';
import { mustGetPublicContentEntry } from '$lib/content/publicContent';

export const load: PageLoad = ({ params }) => ({
	entry: mustGetPublicContentEntry('insights', params.slug)
});
