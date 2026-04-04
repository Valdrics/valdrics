import { api } from '$lib/api';
import { edgeApiPath } from '$lib/edgeProxy';
import { TimeoutError } from '$lib/fetchWithTimeout';
import { clientLogger } from '$lib/logging/client';
import { formatValidationIssues } from '$lib/validation/formatValidationIssues';
import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';
import type { PolicyDiagnostics } from './settingsPageModels';
import {
	applyPostSaveNotificationSettings,
	buildNotificationSavePayload,
	mergeLoadedNotificationSettings
} from './settingsNotificationState';

type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;

const SETTINGS_REQUEST_TIMEOUT_MS = 8000;

function getHeaders(accessToken?: string) {
	return { Authorization: `Bearer ${accessToken}` };
}

async function getWithTimeout(url: string, headers?: Record<string, string>) {
	return api.get(url, {
		...(headers ? { headers } : {}),
		timeoutMs: SETTINGS_REQUEST_TIMEOUT_MS
	});
}

async function getApiErrorMessage(res: Response, fallback: string): Promise<string> {
	const payload = await res.json().catch(() => ({}));
	return payload.detail || payload.message || fallback;
}

export async function loadNotificationSettings(
	accessToken: string | undefined,
	current: NotificationSettingsState
): Promise<{ settings: NotificationSettingsState; error: string }> {
	try {
		const headers = getHeaders(accessToken);
		const res = await getWithTimeout(edgeApiPath('/settings/notifications'), headers);
		if (res.ok) {
			const loaded = (await res.json().catch(() => ({}))) as Record<string, unknown>;
			return {
				settings: mergeLoadedNotificationSettings(current, loaded),
				error: ''
			};
		}
	} catch (nextError) {
		clientLogger.error('Failed to load notification settings:', nextError);
		return {
			settings: current,
			error:
				nextError instanceof TimeoutError
					? 'Settings request timed out. Defaults are shown until data refresh succeeds.'
					: 'Failed to connect to backend service.'
		};
	}

	return { settings: current, error: '' };
}

export async function saveNotificationSettings(
	accessToken: string | undefined,
	settings: NotificationSettingsState
): Promise<NotificationSettingsState> {
	try {
		const { NotificationSettingsSchema } = await import('./settingsPageSchemas');
		const payload = buildNotificationSavePayload(settings);
		const validated = NotificationSettingsSchema.parse(payload);
		const headers = getHeaders(accessToken);
		const res = await api.put(edgeApiPath('/settings/notifications'), validated, { headers });
		if (!res.ok) {
			throw new Error(await getApiErrorMessage(res, 'Failed to save settings'));
		}
		return applyPostSaveNotificationSettings(settings, validated);
	} catch (nextError) {
		throw new Error(formatValidationIssues(nextError, false));
	}
}

export async function runNotificationTest(
	accessToken: string | undefined,
	path: string,
	fallbackMessage: string
): Promise<void> {
	const headers = getHeaders(accessToken);
	const res = await api.post(edgeApiPath(path), {}, { headers });
	if (!res.ok) {
		throw new Error(await getApiErrorMessage(res, fallbackMessage));
	}
}

export async function runNotificationPolicyDiagnostics(
	accessToken: string | undefined
): Promise<PolicyDiagnostics> {
	const headers = getHeaders(accessToken);
	const res = await api.get(edgeApiPath('/settings/notifications/policy-diagnostics'), {
		headers
	});
	if (!res.ok) {
		throw new Error(await getApiErrorMessage(res, 'Failed to run policy diagnostics'));
	}
	return (await res.json()) as PolicyDiagnostics;
}
