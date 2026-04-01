import type { PageServerLoad } from './$types';
import { listPublicContent, mustGetPublicContentEntry } from '$lib/content/publicContent';

export const load: PageServerLoad = () => ({
	proofSpotlights: [
		mustGetPublicContentEntry('proof', 'safe-access-model'),
		mustGetPublicContentEntry('proof', 'identity-and-approval-controls'),
		mustGetPublicContentEntry('proof', 'decision-history-and-export-integrity'),
		mustGetPublicContentEntry('proof', 'deployment-and-data-residency'),
		mustGetPublicContentEntry('proof', 'validation-scope-and-operational-hardening')
	]
});
