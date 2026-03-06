<script lang="ts">
	import type { BudgetData, CarbonData, GravitonData } from './greenopsTypes';

	interface Props {
		carbonData: CarbonData | null;
		gravitonData: GravitonData | null;
		budgetData: BudgetData | null;
		formatCO2: (kg: number) => string;
	}

	let { carbonData, gravitonData, budgetData, formatCO2 }: Props = $props();
</script>

<div class="bento-grid">
	<div class="glass-panel col-span-2 relative overflow-hidden group">
		<div
			class="absolute top-0 right-0 p-4 opacity-10 text-9xl leading-none select-none pointer-events-none"
		>
			🌍
		</div>
		<div class="relative z-10 flex flex-col justify-between h-full">
			<div>
				<h2 class="text-ink-400 text-sm font-medium uppercase tracking-wider mb-1">
					Total Carbon Footprint
				</h2>
				<div class="flex items-baseline gap-2">
					<span class="text-5xl font-bold text-white tracking-tight">
						{carbonData ? formatCO2(carbonData.total_co2_kg) : '—'}
					</span>
					{#if carbonData?.forecast_30d}
						<span
							class="text-xs text-ink-400 bg-ink-800/50 px-2 py-1 rounded-full border border-ink-700"
						>
							Forecast: {formatCO2(carbonData.forecast_30d.projected_co2_kg)} / 30d
						</span>
					{/if}
				</div>
				<p class="text-ink-400 text-sm mt-2">
					Combined Scope 2 (Operational) & Scope 3 (Embodied)
				</p>
			</div>

			{#if carbonData}
				<div class="grid grid-cols-2 gap-4 mt-6">
					<div>
						<div class="text-xs text-ink-400 mb-1">Scope 2</div>
						<div class="h-1.5 w-full bg-ink-800 rounded-full overflow-hidden">
							<div
								class="h-full bg-accent-500"
								style="width: {carbonData.total_co2_kg > 0
									? (carbonData.scope2_co2_kg / carbonData.total_co2_kg) * 100
									: 0}%"
							></div>
						</div>
						<div class="text-white text-sm mt-1">{formatCO2(carbonData.scope2_co2_kg)}</div>
					</div>
					<div>
						<div class="text-xs text-ink-400 mb-1">Scope 3</div>
						<div class="h-1.5 w-full bg-ink-800 rounded-full overflow-hidden">
							<div
								class="h-full bg-purple-500"
								style="width: {carbonData.total_co2_kg > 0
									? (carbonData.scope3_co2_kg / carbonData.total_co2_kg) * 100
									: 0}%"
							></div>
						</div>
						<div class="text-white text-sm mt-1">{formatCO2(carbonData.scope3_co2_kg)}</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="glass-panel text-center flex flex-col items-center justify-center">
		<div class="text-4xl mb-2">📈</div>
		<h3 class="text-ink-400 text-xs uppercase font-medium">Efficiency Score</h3>
		<p class="text-3xl font-bold text-white mt-1">
			{carbonData ? carbonData.carbon_efficiency_score : '—'}
		</p>
		<p class="text-ink-500 text-xs">gCO₂e per $1 spent</p>
	</div>

	<div class="glass-panel text-center flex flex-col items-center justify-center">
		<div class="text-4xl mb-2">⚡</div>
		<h3 class="text-ink-400 text-xs uppercase font-medium">Est. Energy</h3>
		<p class="text-3xl font-bold text-white mt-1">
			{carbonData ? Math.round(carbonData.estimated_energy_kwh) : '—'}
		</p>
		<p class="text-ink-500 text-xs">kWh (incl. PUE)</p>
	</div>

	<div class="glass-panel col-span-2">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold text-white flex items-center gap-2">📊 Monthly Carbon Budget</h3>
			{#if budgetData}
				<span
					class="badge"
					class:badge-success={budgetData.alert_status === 'ok'}
					class:badge-warning={budgetData.alert_status === 'warning'}
					class:badge-error={budgetData.alert_status === 'exceeded'}
				>
					{budgetData.alert_status === 'ok'
						? 'ON TRACK'
						: budgetData.alert_status === 'warning'
							? 'WARNING'
							: 'EXCEEDED'}
				</span>
			{/if}
		</div>

		{#if budgetData}
			<div class="relative pt-4">
				<div class="flex justify-between text-xs text-ink-400 mb-1">
					<span>{formatCO2(budgetData.current_usage_kg)} used</span>
					<span>Limit: {formatCO2(budgetData.budget_kg)}</span>
				</div>
				<div class="w-full bg-ink-950 rounded-full h-3 border border-ink-800 overflow-hidden">
					<div
						class="h-full rounded-full transition-all duration-1000 ease-out relative"
						class:bg-green-500={budgetData.alert_status === 'ok'}
						class:bg-yellow-500={budgetData.alert_status === 'warning'}
						class:bg-red-500={budgetData.alert_status === 'exceeded'}
						style="width: {Math.min(budgetData.usage_percent, 100)}%"
					>
						<div class="absolute inset-0 bg-white/20 animate-pulse"></div>
					</div>
				</div>
				<p class="text-right text-xs text-ink-500 mt-1">{budgetData.usage_percent}% consumed</p>
			</div>
		{:else}
			<div class="animate-pulse h-12 bg-ink-800/50 rounded"></div>
		{/if}
	</div>

	<div class="glass-panel row-span-2 col-span-2">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold text-white flex items-center gap-2">
				🚀 Graviton Candidates
				{#if gravitonData && gravitonData.candidates?.length}
					<span class="bg-accent-500/20 text-accent-400 text-xs px-2 py-0.5 rounded-full"
						>{gravitonData.candidates.length}</span
					>
				{/if}
			</h3>
		</div>

		<div class="space-y-3 overflow-y-auto max-h-[300px] pr-2 custom-scrollbar">
			{#if gravitonData && (gravitonData.candidates?.length ?? 0) > 0}
				{#each (gravitonData.candidates ?? []).slice(0, 5) as candidate (candidate.instance_id)}
					<div
						class="bg-ink-900/40 border border-ink-800 rounded-lg p-3 hover:border-accent-500/30 transition-colors"
					>
						<div class="flex justify-between items-start mb-1">
							<span class="font-mono text-sm text-white">{candidate.instance_id}</span>
							<span class="text-green-400 text-xs font-bold"
								>-{candidate.energy_savings_percent}% CO₂</span
							>
						</div>
						<div class="flex items-center gap-2 text-xs text-ink-400">
							<span>{candidate.current_type}</span>
							<span>→</span>
							<span class="text-accent-400">{candidate.recommended_type}</span>
						</div>
					</div>
				{/each}
			{:else if gravitonData}
				<div class="text-center py-8 text-ink-500">
					<p>All workloads optimized! 🎉</p>
				</div>
			{:else}
				<div class="space-y-3">
					<!-- eslint-disable-next-line @typescript-eslint/no-unused-vars -->
					{#each Array(3) as _, i (i)}
						<div class="h-16 bg-ink-800/30 rounded-lg animate-pulse"></div>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<div class="glass-panel col-span-2">
		<h3 class="text-sm font-semibold text-ink-300 mb-3 uppercase tracking-wider">
			Environmental Equivalencies
		</h3>

		{#if carbonData?.equivalencies}
			<div class="grid grid-cols-4 gap-2">
				<div class="text-center p-2 bg-ink-900/30 rounded border border-ink-800/50">
					<div class="text-xl mb-1">🚗</div>
					<div class="text-sm font-bold text-white">
						{carbonData.equivalencies.miles_driven}
					</div>
					<div class="text-xs text-ink-500">miles</div>
				</div>
				<div class="text-center p-2 bg-ink-900/30 rounded border border-ink-800/50">
					<div class="text-xl mb-1">🌳</div>
					<div class="text-sm font-bold text-white">
						{carbonData.equivalencies.trees_needed_for_year}
					</div>
					<div class="text-xs text-ink-500">trees</div>
				</div>
				<div class="text-center p-2 bg-ink-900/30 rounded border border-ink-800/50">
					<div class="text-xl mb-1">📱</div>
					<div class="text-sm font-bold text-white">
						{carbonData.equivalencies.smartphone_charges}
					</div>
					<div class="text-xs text-ink-500">charges</div>
				</div>
				<div class="text-center p-2 bg-ink-900/30 rounded border border-ink-800/50">
					<div class="text-xl mb-1">🏠</div>
					<div class="text-sm font-bold text-white">
						{carbonData.equivalencies.percent_of_home_month}%
					</div>
					<div class="text-xs text-ink-500">home/mo</div>
				</div>
			</div>
		{/if}
	</div>
</div>
