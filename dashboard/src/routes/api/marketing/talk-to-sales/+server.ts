import { createHash } from 'node:crypto';
import { json } from '@sveltejs/kit';
import { resolveBackendOrigin } from '$lib/server/backend-origin';
import { serverLogger } from '$lib/logging/server';
import type { RequestHandler } from './$types';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LENGTH = 254;
const TEAM_SIZES = new Set(['1-5', '6-20', '21-50', '51-200', '201-1000', '1000+']);
const TIMELINES = new Set(['this_month', 'this_quarter', 'next_quarter', 'evaluating']);
const INTEREST_AREAS = new Set([
	'plan_fit',
	'security_review',
	'procurement',
	'multi_cloud',
	'greenops',
	'saas_governance',
	'executive_briefing'
]);

type TalkToSalesBody = {
	name: string;
	email: string;
	company: string;
	role?: string;
	teamSize?: string;
	deploymentScope?: string;
	timeline?: string;
	interestArea?: string;
	message?: string;
	referrer?: string;
	source?: string;
	utmSource?: string;
	utmMedium?: string;
	utmCampaign?: string;
	honey?: string;
};

function hashEmail(email: string): string {
	return createHash('sha256').update(email).digest('hex');
}

function normalizeOptionalString(value: unknown): string | undefined {
	const text = String(value ?? '').trim();
	return text.length > 0 ? text : undefined;
}

function normalizeBody(payload: unknown): TalkToSalesBody | null {
	if (!payload || typeof payload !== 'object') return null;
	const candidate = payload as Record<string, unknown>;
	const name = String(candidate.name ?? '').trim();
	const email = String(candidate.email ?? '')
		.trim()
		.toLowerCase();
	const company = String(candidate.company ?? '').trim();
	const role = normalizeOptionalString(candidate.role);
	const teamSize = normalizeOptionalString(candidate.teamSize);
	const deploymentScope = normalizeOptionalString(candidate.deploymentScope);
	const timeline = normalizeOptionalString(candidate.timeline);
	const interestArea = normalizeOptionalString(candidate.interestArea);
	const message = normalizeOptionalString(candidate.message);
	const referrer = normalizeOptionalString(candidate.referrer);
	const source = normalizeOptionalString(candidate.source);
	const utmSource = normalizeOptionalString(candidate.utmSource);
	const utmMedium = normalizeOptionalString(candidate.utmMedium);
	const utmCampaign = normalizeOptionalString(candidate.utmCampaign);
	const honey = normalizeOptionalString(candidate.honey);

	if (!name || name.length > 120) return null;
	if (!email || email.length > MAX_EMAIL_LENGTH || !EMAIL_REGEX.test(email)) return null;
	if (!company || company.length > 120) return null;
	if (role && role.length > 120) return null;
	if (teamSize && !TEAM_SIZES.has(teamSize)) return null;
	if (deploymentScope && deploymentScope.length > 200) return null;
	if (timeline && !TIMELINES.has(timeline)) return null;
	if (interestArea && !INTEREST_AREAS.has(interestArea)) return null;
	if (message && message.length > 2000) return null;
	if (referrer && referrer.length > 200) return null;
	if (source && source.length > 120) return null;
	if (utmSource && utmSource.length > 120) return null;
	if (utmMedium && utmMedium.length > 120) return null;
	if (utmCampaign && utmCampaign.length > 120) return null;
	if (honey && honey.length > 120) return null;

	return {
		name,
		email,
		company,
		role,
		teamSize,
		deploymentScope,
		timeline,
		interestArea,
		message,
		referrer,
		source,
		utmSource,
		utmMedium,
		utmCampaign,
		honey
	};
}

export const POST: RequestHandler = async ({ request, fetch }) => {
	let payload: unknown;
	try {
		payload = await request.json();
	} catch {
		return json({ ok: false, error: 'invalid_json' }, { status: 400 });
	}

	const body = normalizeBody(payload);
	if (!body) {
		return json({ ok: false, error: 'invalid_payload' }, { status: 400 });
	}

	if (body.honey) {
		return json({ ok: true, accepted: true }, { status: 202 });
	}

	const turnstileToken = String(request.headers.get('x-turnstile-token') || '').trim();

	try {
		const response = await fetch(
			`${resolveBackendOrigin()}/api/v1/public/marketing/talk-to-sales`,
			{
				method: 'POST',
				headers: {
					'content-type': 'application/json',
					...(turnstileToken ? { 'x-turnstile-token': turnstileToken } : {})
				},
				body: JSON.stringify(body)
			}
		);
		const responsePayload = await response
			.json()
			.catch(() => ({ ok: false, error: 'delivery_failed' }));
		if (!response.ok) {
			if (response.status === 422) {
				return json({ ok: false, error: 'invalid_payload' }, { status: 400 });
			}
			return json(responsePayload, { status: response.status });
		}
		return json(responsePayload, { status: response.status });
	} catch (error) {
		serverLogger.error('marketing_talk_to_sales_proxy_failed', {
			emailHash: hashEmail(body.email),
			error: error instanceof Error ? error.message : 'unknown'
		});
		return json({ ok: false, error: 'delivery_failed' }, { status: 503 });
	}
};
