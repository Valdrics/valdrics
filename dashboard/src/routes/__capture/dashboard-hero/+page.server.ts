import { dev } from '$app/environment';
import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	if (!dev && env.TESTING !== 'true') {
		error(404, 'Not found');
	}

	return {};
};
