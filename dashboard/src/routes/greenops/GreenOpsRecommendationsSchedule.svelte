<script lang="ts">
	import type { CarbonData, IntensityData, ScheduleResult } from './greenopsTypes';

	interface Props {
		carbonData: CarbonData | null;
		intensityData: IntensityData | null;
		workloadDuration: number;
		scheduleResult: ScheduleResult | null;
		onGetOptimalSchedule: () => void | Promise<void>;
	}

	let {
		carbonData,
		intensityData,
		workloadDuration = $bindable(),
		scheduleResult,
		onGetOptimalSchedule
	}: Props = $props();
</script>

{#if carbonData}
	<div class="glass-panel mt-6">
		<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
			🌿 Recommended Regions
			<span class="text-xs font-normal text-ink-400 bg-ink-800 px-2 py-0.5 rounded"
				>Lower Carbon Intensity</span
			>
		</h3>
		{#if (carbonData.green_region_recommendations?.length ?? 0) > 0}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				{#each (carbonData.green_region_recommendations ?? []).slice(0, 3) as rec (rec.region)}
					<div
						class="group p-4 rounded-lg bg-gradient-to-br from-green-900/10 to-green-900/5 border border-green-900/30 hover:border-green-500/50 transition-all"
					>
						<div class="flex justify-between items-start">
							<span class="font-bold text-white group-hover:text-green-400 transition-colors"
								>{rec.region}</span
							>
							<span class="text-xs bg-green-900/40 text-green-300 px-1.5 py-0.5 rounded"
								>{rec.carbon_intensity} g/kWh</span
							>
						</div>
						<div class="mt-2 text-sm text-ink-400">
							Save <span class="text-green-400 font-bold">{rec.savings_percent}%</span> emissions
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div
				class="p-4 rounded-lg bg-gradient-to-br from-green-900/10 to-green-900/5 border border-green-900/30 text-ink-400"
			>
				You’re already in one of the greenest regions 🌿
			</div>
		{/if}
	</div>
{/if}

<div class="glass-panel mt-6">
	<div class="flex items-center justify-between mb-6">
		<div>
			<h3 class="text-xl font-bold text-white flex items-center gap-2">🕒 Carbon-Aware Scheduling</h3>
			<p class="text-ink-400 text-sm">Optimize non-urgent workloads for low-carbon windows</p>
		</div>
		<div class="flex items-center gap-2 text-xs">
			{#if intensityData?.source === 'simulation'}
				<span
					class="px-2 py-0.5 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 rounded-full"
				>
					Simulated Curves (No API Key)
				</span>
			{:else}
				<span
					class="px-2 py-0.5 bg-green-500/10 text-green-500 border border-green-500/20 rounded-full"
				>
					Live Grid Data
				</span>
			{/if}
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
		<div class="lg:col-span-2">
			<h4 class="text-white text-sm font-semibold mb-4 uppercase tracking-wider">
				24h Intensity Forecast (gCO₂/kWh)
			</h4>
			<div class="flex items-end gap-1 h-32 w-full pt-4">
				{#if intensityData?.forecast}
					{#each intensityData.forecast as hour (hour.hour_utc)}
						<div class="group relative flex-1 flex flex-col items-center justify-end h-full">
							<div
								class="w-full rounded-t-sm transition-all hover:opacity-100 opacity-70"
								class:bg-green-500={hour.level === 'very_low' || hour.level === 'low'}
								class:bg-yellow-500={hour.level === 'medium'}
								class:bg-red-500={hour.level === 'high' || hour.level === 'very_high'}
								style="height: {(hour.intensity_gco2_kwh / 800) * 100}%"
							></div>
							<div
								class="absolute bottom-full mb-2 hidden group-hover:block bg-ink-900 border border-ink-700 p-2 rounded text-xs z-50 whitespace-nowrap"
							>
								{hour.hour_utc}:00 UTC <br />
								<span class="font-bold">{hour.intensity_gco2_kwh} g/kWh</span>
							</div>
						</div>
					{/each}
				{/if}
			</div>
			<div class="flex justify-between mt-2 text-xs text-ink-500 px-1">
				<span>NOW</span>
				<span>+12h</span>
				<span>+24h</span>
			</div>
		</div>

		<div class="bg-ink-900/50 p-6 rounded-xl border border-ink-800">
			<h4 class="text-white text-sm font-semibold mb-4 uppercase tracking-wider">Optimal Scheduler</h4>
			<div class="space-y-4">
				<div>
					<label for="duration" class="block text-xs text-ink-400 mb-2"
						>Workload Duration (Hours)</label
					>
					<input
						type="range"
						id="duration"
						min="1"
						max="24"
						bind:value={workloadDuration}
						class="w-full h-1.5 bg-ink-800 rounded-lg appearance-none cursor-pointer accent-accent-500"
					/>
					<div class="text-right text-xs font-mono text-ink-300 mt-1">{workloadDuration}h</div>
				</div>

				<button
					type="button"
					onclick={onGetOptimalSchedule}
					class="w-full py-2 bg-accent-600 hover:bg-accent-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-lg shadow-accent-600/20"
				>
					Find Optimal Window
				</button>

				{#if scheduleResult}
					<div
						class="mt-4 p-4 bg-accent-950/30 border border-accent-500/20 rounded-lg animate-in fade-in slide-in-from-bottom-2"
					>
						<div class="text-xs uppercase font-bold text-accent-400 mb-1">Recommendation</div>
						<div class="text-sm text-white font-medium">{scheduleResult.recommendation}</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
