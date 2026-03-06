<script lang="ts">
	interface Props {
		toAppPath: (path: string) => string;
	}

	let { toAppPath }: Props = $props();
</script>

<div class="relative">
	<div
		class="absolute inset-0 z-20 flex flex-col items-center justify-center text-center bg-ink-950/60 backdrop-blur-[1px] rounded-xl"
	>
		<div class="text-6xl mb-4">🌱</div>
		<h2 class="text-2xl font-bold text-white mb-2">Upgrade to Unlock GreenOps</h2>
		<p class="text-ink-300 max-w-md mb-6">
			Track your cloud carbon footprint, get green region recommendations, and monitor sustainability
			metrics.
		</p>
		<div class="flex items-center gap-2 mb-6">
			<span class="badge badge-warning">Growth Plan Required</span>
		</div>
		<a href={toAppPath('/billing')} class="btn btn-primary"> Upgrade to Growth </a>
	</div>

	<div class="opacity-50 pointer-events-none select-none">
		<div class="bento-grid">
			<div class="glass-panel col-span-2">
				<h2 class="text-ink-400 text-sm font-medium uppercase tracking-wider mb-1">
					Total Carbon Footprint
				</h2>
				<span class="text-5xl font-bold text-white">42.7 kg</span>
				<p class="text-ink-400 text-sm mt-2">Combined Scope 2 + Scope 3</p>
			</div>
			<div class="glass-panel text-center">
				<div class="text-4xl mb-2">📈</div>
				<h3 class="text-ink-400 text-xs uppercase">Efficiency Score</h3>
				<p class="text-3xl font-bold text-white mt-1">89</p>
			</div>
			<div class="glass-panel text-center">
				<div class="text-4xl mb-2">⚡</div>
				<h3 class="text-ink-400 text-xs uppercase">Est. Energy</h3>
				<p class="text-3xl font-bold text-white mt-1">156 kWh</p>
			</div>
			<div class="glass-panel col-span-2">
				<h3 class="text-lg font-semibold text-white mb-4">📊 Monthly Carbon Budget</h3>
				<div class="w-full bg-ink-800 rounded-full h-3">
					<div class="h-full bg-green-500 rounded-full" style="width: 65%"></div>
				</div>
				<p class="text-right text-xs text-ink-500 mt-1">65% consumed</p>
			</div>
		</div>
	</div>
</div>
