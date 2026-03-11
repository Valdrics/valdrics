<script lang="ts">
	import { INITIAL_LLM_SETTINGS, INITIAL_PROVIDER_MODELS } from './settingsPageInitialState';

	type AsyncAction = () => void | Promise<void>;
	type LlmSettingsState = typeof INITIAL_LLM_SETTINGS;
	type ProviderModels = typeof INITIAL_PROVIDER_MODELS;

	interface Props {
		loadingLLM: boolean;
		llmSettings: LlmSettingsState;
		providerModels: ProviderModels;
		saveLLMSettings: AsyncAction;
		savingLLM: boolean;
	}

	let {
		loadingLLM,
		llmSettings = $bindable(),
		providerModels,
		saveLLMSettings,
		savingLLM
	}: Props = $props();
</script>

<!-- AI Strategy Settings -->
<div class="card stagger-enter">
	<h2 class="text-lg font-semibold mb-5 flex items-center gap-2">
		<span>🤖</span> AI Strategy
	</h2>

	{#if loadingLLM}
		<div class="skeleton h-4 w-48"></div>
	{:else}
		<div class="space-y-4">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="form-group">
					<label for="provider">Preferred Provider</label>
					<select
						id="provider"
						bind:value={llmSettings.preferred_provider}
						class="select"
						onchange={() =>
							(llmSettings.preferred_model =
								providerModels[llmSettings.preferred_provider as keyof typeof providerModels][0])}
						aria-label="Preferred AI provider"
					>
						<option value="groq">Groq (Ultra-Fast)</option>
						<option value="openai">OpenAI (Gold Standard)</option>
						<option value="anthropic">Anthropic (Claude)</option>
						<option value="google">Google (Gemini)</option>
					</select>
				</div>

				<div class="form-group">
					<label for="model">AI Model</label>
					<select
						id="model"
						bind:value={llmSettings.preferred_model}
						class="select"
						aria-label="Preferred AI model"
					>
						{#each providerModels[llmSettings.preferred_provider as keyof typeof providerModels] as model (model)}
							<option value={model}>{model}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="form-group">
					<label for="llm_budget">Monthly AI Budget (USD)</label>
					<input
						type="number"
						id="llm_budget"
						bind:value={llmSettings.monthly_limit_usd}
						min="0"
						step="1"
						aria-label="Monthly AI budget in USD"
					/>
				</div>

				<div class="form-group">
					<label for="llm_alert_threshold">Alert Threshold (%)</label>
					<input
						type="number"
						id="llm_alert_threshold"
						bind:value={llmSettings.alert_threshold_percent}
						min="0"
						max="100"
						aria-label="AI alert threshold percentage"
					/>
				</div>
			</div>

			<div class="space-y-4 pt-4 border-t border-ink-700">
				<h3 class="text-sm font-semibold text-accent-400 uppercase tracking-wider">
					Bring Your Own Key (Optional)
				</h3>
				<p class="text-xs text-ink-400">
					Provide your own API key to pay the provider directly. The platform will still track usage
					for your awareness.
				</p>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="form-group">
						<label for="openai_key" class="flex items-center justify-between">
							<span>OpenAI API Key</span>
							{#if llmSettings.has_openai_key}
								<span
									class="text-xs px-1.5 py-0.5 rounded bg-success-500/10 text-success-400 border border-success-500/50"
									>Configured</span
								>
							{/if}
						</label>
						<input
							type="password"
							id="openai_key"
							bind:value={llmSettings.openai_api_key}
							placeholder={llmSettings.has_openai_key ? '••••••••••••••••' : 'sk-...'}
							aria-label="OpenAI API Key"
						/>
					</div>
					<div class="form-group">
						<label for="claude_key" class="flex items-center justify-between">
							<span>Claude API Key</span>
							{#if llmSettings.has_claude_key}
								<span
									class="text-xs px-1.5 py-0.5 rounded bg-success-500/10 text-success-400 border border-success-500/50"
									>Configured</span
								>
							{/if}
						</label>
						<input
							type="password"
							id="claude_key"
							bind:value={llmSettings.claude_api_key}
							placeholder={llmSettings.has_claude_key ? '••••••••••••••••' : 'sk-ant-...'}
							aria-label="Claude API Key"
						/>
					</div>
					<div class="form-group">
						<label for="google_key" class="flex items-center justify-between">
							<span>Google AI (Gemini) Key</span>
							{#if llmSettings.has_google_key}
								<span
									class="text-xs px-1.5 py-0.5 rounded bg-success-500/10 text-success-400 border border-success-500/50"
									>Configured</span
								>
							{/if}
						</label>
						<input
							type="password"
							id="google_key"
							bind:value={llmSettings.google_api_key}
							placeholder={llmSettings.has_google_key ? '••••••••••••••••' : 'AIza...'}
							aria-label="Google AI (Gemini) API Key"
						/>
					</div>
					<div class="form-group">
						<label for="groq_key" class="flex items-center justify-between">
							<span>Groq API Key</span>
							{#if llmSettings.has_groq_key}
								<span
									class="text-xs px-1.5 py-0.5 rounded bg-success-500/10 text-success-400 border border-success-500/50"
									>Configured</span
								>
							{/if}
						</label>
						<input
							type="password"
							id="groq_key"
							bind:value={llmSettings.groq_api_key}
							placeholder={llmSettings.has_groq_key ? '••••••••••••••••' : 'gsk_...'}
							aria-label="Groq API Key"
						/>
					</div>
				</div>
			</div>

			<div class="form-group">
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={llmSettings.hard_limit}
						class="toggle"
						aria-label="Enable hard limit for AI budget"
					/>
					<span>Enable Hard Limit (Block AI analysis if budget exceeded)</span>
				</label>
			</div>

			<button
				type="button"
				class="btn btn-primary"
				onclick={saveLLMSettings}
				disabled={savingLLM}
				aria-label="Save AI strategy settings"
			>
				{savingLLM ? '⏳ Saving...' : '💾 Save AI Strategy'}
			</button>
		</div>
	{/if}
</div>
