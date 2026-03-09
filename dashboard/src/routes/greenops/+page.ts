import { GREENOPS_DEFAULT_REGION } from './greenopsApiPaths';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, parent, url }) => {
	await parent();
	const selectedRegion = url.searchParams.get('region') || GREENOPS_DEFAULT_REGION;
	void fetch; // keep signature stable while moving data hydration client-side
	return { selectedRegion };
};
