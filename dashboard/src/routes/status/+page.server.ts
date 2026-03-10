import { TimeoutError, fetchWithTimeout } from '$lib/fetchWithTimeout';
import { resolveBackendOrigin } from '$lib/server/backend-origin';
import type { PageServerLoad } from './$types';
import {
	buildFallbackStatusSnapshot,
	buildStatusSnapshot,
	isBackendHealthPayload
} from './statusPage';

const STATUS_REQUEST_TIMEOUT_MS = 5000;

function isLocalBackendOrigin(origin: string): boolean {
	try {
		const parsed = new URL(origin);
		return parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1';
	} catch {
		return false;
	}
}

async function readHealthPayload(response: Response): Promise<unknown> {
	try {
		return await response.json();
	} catch {
		return null;
	}
}

export const load: PageServerLoad = async ({ fetch, setHeaders }) => {
	setHeaders({
		'Cache-Control': 'no-store'
	});

	const backendOrigin = resolveBackendOrigin();

	try {
		const response = await fetchWithTimeout(
			fetch,
			`${backendOrigin}/health`,
			{
				headers: {
					accept: 'application/json'
				}
			},
			STATUS_REQUEST_TIMEOUT_MS
		);
		const payload = await readHealthPayload(response);

		if (isBackendHealthPayload(payload)) {
			return buildStatusSnapshot(payload);
		}

		const reason = response.ok
			? 'The automated health endpoint returned an unexpected payload.'
			: `The automated health endpoint returned HTTP ${response.status}.`;
		return buildFallbackStatusSnapshot(reason);
	} catch (error) {
		const reason =
			error instanceof TimeoutError
				? 'The automated health summary timed out before it completed.'
				: isLocalBackendOrigin(backendOrigin)
					? `The local API at ${backendOrigin} is unavailable. Start the backend or update the backend origin configuration.`
				: 'The automated health summary is temporarily unavailable.';
		return buildFallbackStatusSnapshot(reason);
	}
};
