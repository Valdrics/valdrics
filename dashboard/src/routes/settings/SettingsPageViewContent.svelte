<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { clientLogger } from '$lib/logging/client';
	import type { SafetyStatus } from './settingsPageModels';
	import {
		INITIAL_ACTIVEOPS_SETTINGS,
		INITIAL_CARBON_SETTINGS,
		INITIAL_LLM_SETTINGS,
		INITIAL_PROVIDER_MODELS
	} from './settingsPageInitialState';
	import { formatValidationIssues } from '$lib/validation/formatValidationIssues';
	import './SettingsPageViewContent.css';

	function createModuleLoader<T>(loader: () => Promise<T>): () => Promise<T> {
		let promise: Promise<T> | null = null;

		return () => {
			if (!promise) {
				promise = loader().catch((error) => {
					promise = null;
					throw error;
				});
			}
			return promise;
		};
	}

	const loadSettingsPageViewBody = createModuleLoader(
		() => import('./SettingsPageViewBody.svelte')
	);

	let { data } = $props();
	const SETTINGS_REQUEST_TIMEOUT_MS = 8000;

	let loading = $state(false);
	let error = $state('');
	let success = $state('');

	let safetyStatus = $state<SafetyStatus | null>(null),
		loadingSafety = $state(true),
		resettingSafety = $state(false);
	let safetyError = $state('');
	let safetySuccess = $state('');

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
	let settingsSchemasPromise: Promise<typeof import('./settingsPageSchemas')> | null = null;
	let deferredSettingsDataPromise: Promise<void> | null = null;
	let deferredSettingsDataLoaded = $state(false);

	const getHeaders = () => ({ Authorization: `Bearer ${data.session?.access_token}` });

	function loadSettingsSchemas() {
		if (!settingsSchemasPromise) {
			settingsSchemasPromise = import('./settingsPageSchemas');
		}
		return settingsSchemasPromise;
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
			const { CarbonSettingsSchema } = await loadSettingsSchemas();
			CarbonSettingsSchema.parse(carbonSettings);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/carbon'), carbonSettings, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save carbon settings'));
			}
			success = 'Carbon settings saved successfully!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = formatValidationIssues(e, true);
		} finally {
			savingCarbon = false;
		}
	}

	async function loadModels() {
		try {
			const headers = await getHeaders();
			const res = await getWithTimeout(edgeApiPath('/settings/llm/models'), headers);
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
			const { LLMSettingsSchema } = await loadSettingsSchemas();
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
			error = formatValidationIssues(e, true);
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
			const { ActiveOpsSettingsSchema } = await loadSettingsSchemas();
			ActiveOpsSettingsSchema.parse(activeOpsSettings);
			const headers = await getHeaders();
			const res = await api.put(edgeApiPath('/settings/activeops'), activeOpsSettings, { headers });
			if (!res.ok) {
				throw new Error(await getApiErrorMessage(res, 'Failed to save ActiveOps settings'));
			}
			success = 'ActiveOps / Auto-Pilot settings saved!';
			setTimeout(() => (success = ''), 3000);
		} catch (e) {
			error = formatValidationIssues(e, true);
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

	async function ensureDeferredSettingsData(): Promise<void> {
		if (deferredSettingsDataLoaded) {
			return;
		}

		if (!data.user) {
			loadingLLM = false;
			loadingActiveOps = false;
			loadingSafety = false;
			deferredSettingsDataLoaded = true;
			return;
		}

		if (!deferredSettingsDataPromise) {
			deferredSettingsDataPromise = Promise.all([
				loadModels(),
				loadLLMSettings(),
				loadSafetyStatus(),
				['growth', 'pro', 'enterprise'].includes(data.subscription?.tier)
					? loadActiveOpsSettings()
					: Promise.resolve().then(() => {
							loadingActiveOps = false;
						})
			])
				.then(() => {
					deferredSettingsDataLoaded = true;
				})
				.catch((error) => {
					deferredSettingsDataPromise = null;
					throw error;
				});
		}

		return deferredSettingsDataPromise;
	}

	onMount(() => {
		if (data.user) {
			void loadCarbonSettings();
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
		onRevealDeferredSections: ensureDeferredSettingsData
	});
</script>

<svelte:head>
	<title>Settings | Valdrics</title>
</svelte:head>

{#await loadSettingsPageViewBody()}
	<div class="card">
		<div class="skeleton h-8 w-48 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-3/4 mb-6"></div>
		<div class="skeleton h-64 rounded-2xl"></div>
	</div>
{:then module}
	{@const SettingsPageViewBody = module.default}
	<SettingsPageViewBody
		{...viewProps}
		bind:persona
		bind:carbonSettings
		bind:llmSettings
		bind:activeOpsSettings
	/>
{/await}
