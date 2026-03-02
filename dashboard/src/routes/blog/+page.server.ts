import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ url }) => {
	const search = url.search || '';
	throw redirect(308, `/insights${search}`);
};
