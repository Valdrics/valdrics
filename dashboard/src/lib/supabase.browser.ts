import { createBrowserClient } from '@supabase/ssr';
import { env as publicEnv } from '$env/dynamic/public';

function readSupabasePublicConfig(): { url: string; anonKey: string } {
	const url = String(publicEnv.PUBLIC_SUPABASE_URL || '').trim();
	const anonKey = String(publicEnv.PUBLIC_SUPABASE_ANON_KEY || '').trim();

	if (!url || !anonKey) {
		throw new Error(
			'Supabase public environment is not configured. Set PUBLIC_SUPABASE_URL and PUBLIC_SUPABASE_ANON_KEY.'
		);
	}

	return { url, anonKey };
}

export function createSupabaseBrowserClient() {
	const { url, anonKey } = readSupabasePublicConfig();
	return createBrowserClient(url, anonKey);
}
