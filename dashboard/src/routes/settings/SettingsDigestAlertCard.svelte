<script lang="ts">
	import { INITIAL_NOTIFICATION_SETTINGS } from './settingsPageInitialState';
	type AsyncAction = () => void | Promise<void>;
	type NotificationSettingsState = typeof INITIAL_NOTIFICATION_SETTINGS;

	interface Props {
		settings: NotificationSettingsState;
		saveSettings: AsyncAction;
		saving: boolean;
	}

	let { settings = $bindable(), saveSettings, saving }: Props = $props();
</script>

			<!-- Digest Schedule -->
			<div class="card stagger-enter" style="animation-delay: 50ms;">
				<h2 class="text-lg font-semibold mb-5 flex items-center gap-2">
					<span>📅</span> Daily Digest
				</h2>

				<div class="space-y-4">
					<div class="form-group">
						<label for="schedule">Frequency</label>
						<select
							id="schedule"
							bind:value={settings.digest_schedule}
							class="select"
							aria-label="Daily digest frequency"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly (Mondays)</option>
							<option value="disabled">Disabled</option>
						</select>
					</div>

					{#if settings.digest_schedule !== 'disabled'}
						<div class="grid grid-cols-2 gap-4">
							<div class="form-group">
								<label for="hour">Hour (UTC)</label>
								<select
									id="hour"
									bind:value={settings.digest_hour}
									class="select"
									aria-label="Digest delivery hour (UTC)"
								>
									{#each Array(24)
										.fill(0)
										.map((_, i) => i) as h (h)}
										<option value={h}>{h.toString().padStart(2, '0')}:00</option>
									{/each}
								</select>
							</div>
							<div class="form-group">
								<label for="minute">Minute</label>
								<select
									id="minute"
									bind:value={settings.digest_minute}
									class="select"
									aria-label="Digest delivery minute"
								>
									{#each [0, 15, 30, 45] as m (m)}
										<option value={m}>:{m.toString().padStart(2, '0')}</option>
									{/each}
								</select>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Alert Preferences -->
			<div class="card stagger-enter" style="animation-delay: 100ms;">
				<h2 class="text-lg font-semibold mb-5 flex items-center gap-2">
					<span>🚨</span> Alert Preferences
				</h2>

				<div class="space-y-3">
					<label class="flex items-center gap-3 cursor-pointer">
						<input type="checkbox" bind:checked={settings.alert_on_budget_warning} class="toggle" />
						<span>Alert when approaching budget limit</span>
					</label>

					<label class="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={settings.alert_on_budget_exceeded}
							class="toggle"
						/>
						<span>Alert when budget is exceeded</span>
					</label>

					<label class="flex items-center gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={settings.alert_on_zombie_detected}
							class="toggle"
						/>
						<span>Alert when zombie resources detected</span>
					</label>
				</div>
			</div>

			<!-- Save Button -->
				<div class="flex justify-end">
					<button type="button" class="btn btn-primary" onclick={saveSettings} disabled={saving}>
						{saving ? '⏳ Saving...' : '💾 Save Settings'}
					</button>
				</div>
