import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const MOTION_QUERY_KEY = 'motion';
const SUPPORTED_MOTION_VALUES = new Set(['subtle', 'cinematic']);

export const load: PageServerLoad = ({ url }) => {
	const rawMotion = url.searchParams.get(MOTION_QUERY_KEY);
	if (!rawMotion) {
		return {};
	}

	const normalizedMotion = rawMotion.trim().toLowerCase();
	const isSupportedMotion = SUPPORTED_MOTION_VALUES.has(normalizedMotion);
	const nextUrl = new URL(url);

	if (!isSupportedMotion) {
		nextUrl.searchParams.delete(MOTION_QUERY_KEY);
		throw redirect(308, `${nextUrl.pathname}${nextUrl.search}`);
	}

	if (rawMotion !== normalizedMotion) {
		nextUrl.searchParams.set(MOTION_QUERY_KEY, normalizedMotion);
		throw redirect(308, `${nextUrl.pathname}${nextUrl.search}`);
	}

	return {};
};
