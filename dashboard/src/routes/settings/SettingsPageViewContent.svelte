<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { TimeoutError } from '$lib/fetchWithTimeout';
	import { clientLogger } from '$lib/logging/client';
	import {
		ActiveOpsSettingsSchema,
		CarbonSettingsSchema,
		LLMSettingsSchema,
		NotificationSettingsSchema,
		type PolicyDiagnostics,
		type SafetyStatus
	} from './settingsPageSchemas';
	import {
		INITIAL_ACTIVEOPS_SETTINGS,
		INITIAL_CARBON_SETTINGS,
		INITIAL_LLM_SETTINGS,
		INITIAL_NOTIFICATION_SETTINGS,
		INITIAL_PROVIDER_MODELS
	} from './settingsPageInitialState';
	import {
		applyPostSaveNotificationSettings,
		buildNotificationSavePayload,
		mergeLoadedNotificationSettings
	} from './settingsNotificationState';
	import SettingsPageViewBody from './SettingsPageViewBody.svelte';
	import './SettingsPageViewContent.css';
	import { z } from 'zod';

	let { data } = $props();
	const SETTINGS_REQUEST_TIMEOUT_MS = 8000;

	let loading = $state(false),
		saving = $state(false);
	let testing = $state(false),
		testingJira = $state(false),
		testingTeams = $state(false),
		testingWorkflow = $state(false);
	let diagnosticsLoading = $state(false);
	let error = $state('');
	let success = $state('');

	let policyDiagnostics = $state<PolicyDiagnostics | null>(null);
	let safetyStatus = $state<SafetyStatus | null>(null),
		loadingSafety = $state(true),
		resettingSafety = $state(false);
	let safetyError = $state('');
	let safetySuccess = $state('');

	let settings = $state({ ...INITIAL_NOTIFICATION_SETTINGS });
	let llmSettings = $state({ ...INITIAL_LLM_SETTINGS });
	let loadingLLM = $state(true),
		savingLLM = $state(false);
	let activeOpsSettings = $state({ ...INITIAL_ACTIVEOPS_SETTINGS });
	let loadingActiveOps = $state(true),
		savingActiveOps = $state(false);
	let providerModels = $state({ ...INITIAL_PROVIDER_MODELS });
	let carbonSettings = $state({ ...INITIAL_CARBON_SETTINGS });
	let loadingCarbon = $state(true),
		savingCarbon = $state(false);

	let persona = $derived(String(data.profile?.persona ?? 'engineering'));
	let savingPersona = $state(false);

	const getHeaders = () => ({ Authorization: `Bearer ${data.session?.access_token}` });

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

	function formatZodIssues(error: z.ZodError, includePath: boolean): string {
		if (!includePath) {
			return error.issues.map((issue: z.ZodIssue) => issue.message).join(', ');
		}
		return error.issues
			.map((issue: z.ZodIssue) => `${issue.path.join('.')}: ${issue.message}`)
			.join(', ');
	}

	async function loadSettings() {
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/notifications'), headers);
			if (res.ok) {
				const loaded = (await res.json()) as Record<string, unknown>;
				settings = mergeLoadedNotificationSettings(settings, loaded);
			}
		} catch (e) {
			clientLogger.error('Failed to load settings:', e);
			error =
				e instanceof TimeoutError
					? 'Settings request timed out. Defaults are shown until data refresh succeeds.'
					: 'Failed to connect to backend service.';
		}
	}

	async function savePersona() {
		savingPersona = true;
		error = '';
		success = '';
		try {
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/profile'), { persona }, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save persona.'));
			}
			success = `Persona updated: ${persona}.`;
			setTimeout(() => (success = ''), 3000);
			await invalidateAll();
		} catch (e) {
			const err = e as Error;
			error = err.message || 'Failed to save persona.';
		} finally {
			savingPersona = false;
		}
	}

	async function saveSettings() {
		saving = true;
		error = '';
		success = '';
		try {
			const payload = buildNotificationSavePayload(settings);
			const validated = NotificationSettingsSchema.parse(payload);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/notifications'), validated, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save settings'));
			}
			settings = applyPostSaveNotificationSettings(settings, validated);
			success = 'General settings saved!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = e instanceof z.ZodError ? formatZodIssues(e, false) : (e as Error).message;
		} finally {
			saving = false;
		}
	}

	async function runNotificationTest(
		path: string,
		successMessage: string,
		setLoadingState: (value: boolean) => void,
		fallbackMessage: string
	) {
		setLoadingState(true);
		error = '';
		try {
			const headers = await getHeaders();
			const res = await api.post(edgeApiPath(path), {}, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, fallbackMessage));
			}
			success = successMessage;
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			setLoadingState(false);
		}
	}

	const testSlack = () =>
		runNotificationTest(
			'/settings/notifications/test-slack',
			'Test notification sent to Slack!',
			(value) => (testing = value),
			'Failed to send test notification'
		);
	const testJira = () =>
		runNotificationTest(
			'/settings/notifications/test-jira',
			'Test issue created in Jira!',
			(value) => (testingJira = value),
			'Failed to send Jira test issue'
		);
	const testTeams = () =>
		runNotificationTest(
			'/settings/notifications/test-teams',
			'Test notification sent to Teams!',
			(value) => (testingTeams = value),
			'Failed to send Teams test notification'
		);
	const testWorkflowDispatch = () =>
		runNotificationTest(
			'/settings/notifications/test-workflow',
			'Workflow test event dispatched!',
			(value) => (testingWorkflow = value),
			'Failed to dispatch workflow test event'
		);

	async function runPolicyDiagnostics() {
		diagnosticsLoading = true;
		error = '';
		try {
			const headers = await getHeaders();
			const res = await api.get(edgeApiPath('/settings/notifications/policy-diagnostics'), {
				headers
			});
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to run policy diagnostics'));
			}
			policyDiagnostics = await res.json();
			success = 'Policy diagnostics refreshed.';
			setTimeout(() => (success = ''), 2000);
		} catch (e) {
			const err = e as Error;
			error = err.message;
		} finally {
			diagnosticsLoading = false;
		}
	}

	async function loadCarbonSettings() {
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/carbon'), headers);
			if (res.ok) {
				carbonSettings = await res.json();
			}
		} catch (e) {
			clientLogger.error('Failed to load carbon settings:', e);
		} finally {
			loadingCarbon = false;
		}
	}

	async function saveCarbonSettings() {
		savingCarbon = true;
		error = '';
		success = '';
		try {
			CarbonSettingsSchema.parse(carbonSettings);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/carbon'), carbonSettings, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save carbon settings'));
			}
			success = 'Carbon settings saved successfully!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = e instanceof z.ZodError ? formatZodIssues(e, true) : (e as Error).message;
		} finally {
			savingCarbon = false;
		}
	}

	async function loadModels() {
		try {
			const res = await getWithTimeout(edgeApiPath('/settings/llm/models'));
			if (res.ok) {
				providerModels = await res.json();
			}
		} catch (e) {
			clientLogger.error('Failed to load LLM models:', e);
		}
	}

	async function loadLLMSettings() {
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/llm'), headers);
			if (res.ok) {
				llmSettings = await res.json();
			}
		} catch (e) {
			clientLogger.error('Failed to load LLM settings:', e);
		} finally {
			loadingLLM = false;
		}
	}

	async function saveLLMSettings() {
		savingLLM = true;
		error = '';
		success = '';
		try {
			LLMSettingsSchema.parse(llmSettings);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/llm'), llmSettings, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save LLM settings'));
			}
			const updated = await res.json();
			llmSettings.openai_api_key = '';
			llmSettings.claude_api_key = '';
			llmSettings.google_api_key = '';
			llmSettings.groq_api_key = '';
			llmSettings.has_openai_key = updated.has_openai_key;
			llmSettings.has_claude_key = updated.has_claude_key;
			llmSettings.has_google_key = updated.has_google_key;
			llmSettings.has_groq_key = updated.has_groq_key;
			success = 'AI strategy settings saved!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = e instanceof z.ZodError ? formatZodIssues(e, true) : (e as Error).message;
		} finally {
			savingLLM = false;
		}
	}

	async function loadActiveOpsSettings() {
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/activeops'), headers);
			if (res.ok) {
				activeOpsSettings = await res.json();
			}
		} catch (e) {
			clientLogger.error('Failed to load ActiveOps settings:', e);
		} finally {
			loadingActiveOps = false;
		}
	}

	async function saveActiveOpsSettings() {
		savingActiveOps = true;
		error = '';
		success = '';
		try {
			ActiveOpsSettingsSchema.parse(activeOpsSettings);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/activeops'), activeOpsSettings, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save ActiveOps settings'));
			}
			success = 'ActiveOps / Auto-Pilot settings saved!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = e instanceof z.ZodError ? formatZodIssues(e, true) : (e as Error).message;
		} finally {
			savingActiveOps = false;
		}
	}

	async function loadSafetyStatus() {
		loadingSafety = true;
		safetyError = '';
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/safety'), headers);
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to load safety status'));
			}
			safetyStatus = (await res.json()) as SafetyStatus;
		} catch (e) {
			const err = e as Error;
			safetyError = err.message;
		} finally {
			loadingSafety = false;
		}
	}

	async function resetSafetyCircuitBreaker() {
		resettingSafety = true;
		safetyError = '';
		safetySuccess = '';
		try {
			const headers = await getHeaders();
			const res = await api.post(edgeApiPath('/settings/safety/reset'), {}, { headers });
			if (!res.ok) {
				const payload = await res.json().catch(() => ({}));
				throw new Error(
					payload.detail ||
						payload.message ||
						(res.status === 403
							? 'Admin role required to reset the circuit breaker.'
							: 'Failed to reset circuit breaker.')
				);
			}
			safetySuccess = 'Circuit breaker reset to closed state.';
			await loadSafetyStatus();
		} catch (e) {
			const err = e as Error;
			safetyError = err.message;
		} finally {
			resettingSafety = false;
		}
	}

	onMount(() => {
		if (data.user) {
			void loadSettings();
			void loadCarbonSettings();
			void loadModels();
			void loadLLMSettings();
			void loadSafetyStatus();
			if (['growth', 'pro', 'enterprise'].includes(data.subscription?.tier)) {
				void loadActiveOpsSettings();
			} else {
				loadingActiveOps = false;
			}
		} else {
			loading = false;
			loadingCarbon = false;
			loadingLLM = false;
			loadingActiveOps = false;
			loadingSafety = false;
		}
	});

	const viewProps = $derived({
		data,
		loading,
		error,
		success,
		savingPersona,
		savePersona,
		loadingCarbon,
		savingCarbon,
		saveCarbonSettings,
		loadingLLM,
		savingLLM,
		providerModels,
		saveLLMSettings,
		loadingActiveOps,
		savingActiveOps,
		saveActiveOpsSettings,
		loadingSafety,
		resettingSafety,
		loadSafetyStatus,
		resetSafetyCircuitBreaker,
		safetyError,
		safetySuccess,
		safetyStatus,
		testing,
		testingJira,
		testingTeams,
		testingWorkflow,
		diagnosticsLoading,
		policyDiagnostics,
		testSlack,
		testJira,
		testTeams,
		testWorkflowDispatch,
		runPolicyDiagnostics,
		saveSettings,
		saving
	});
</script>

<svelte:head>
	<title>Settings | Valdrics</title>
</svelte:head>

<SettingsPageViewBody
	{...viewProps}
	bind:persona
	bind:carbonSettings
	bind:llmSettings
	bind:activeOpsSettings
	bind:settings
/>
