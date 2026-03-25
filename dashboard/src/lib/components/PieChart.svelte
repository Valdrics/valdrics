<script lang="ts">
	interface ChartDataItem {
		label: string;
		value: number;
		color?: string;
	}

	let {
		data = [],
		title = 'Breakdown',
		height = 300,
		showLegend = true,
		showPercentage = true
	}: {
		data: ChartDataItem[];
		title?: string;
		height?: number;
		showLegend?: boolean;
		showPercentage?: boolean;
	} = $props();

	const chartSize = 180;
	const chartCenter = chartSize / 2;
	const chartRadius = 58;
	const strokeWidth = 24;
	const circumference = 2 * Math.PI * chartRadius;
	const defaultColors = [
		'#3b82f6',
		'#10b981',
		'#f59e0b',
		'#ef4444',
		'#8b5cf6',
		'#ec4899',
		'#06b6d4',
		'#84cc16',
		'#f97316',
		'#6366f1'
	];

	let activeSegmentIndex = $state(0);

	function getColor(index: number, itemColor?: string): string {
		return itemColor || defaultColors[index % defaultColors.length];
	}

	function formatValue(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		}).format(value);
	}

	type DonutSegment = ChartDataItem & {
		color: string;
		percentage: number;
		dasharray: string;
		dashoffset: number;
	};

	let chartSegments = $derived(() => {
		const total = data.reduce((sum, item) => sum + item.value, 0);
		if (total <= 0) return [];

		let offset = 0;
		return data.map((item, index) => {
			const percentage = item.value / total;
			const arcLength = percentage * circumference;
			const segment: DonutSegment = {
				...item,
				color: getColor(index, item.color),
				percentage,
				dasharray: `${arcLength} ${circumference - arcLength}`,
				dashoffset: -offset
			};
			offset += arcLength;
			return segment;
		});
	});

	let total = $derived(() => chartSegments().reduce((sum, item) => sum + item.value, 0));
	let activeSegment = $derived(
		() => chartSegments()[activeSegmentIndex] ?? chartSegments()[0] ?? null
	);

	$effect(() => {
		const segments = chartSegments();
		if (segments.length === 0) {
			activeSegmentIndex = 0;
			return;
		}
		if (activeSegmentIndex >= segments.length) {
			activeSegmentIndex = 0;
		}
	});

	function activateSegment(index: number): void {
		activeSegmentIndex = index;
	}

	function handleSegmentKeydown(event: KeyboardEvent, index: number): void {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		activateSegment(index);
	}
</script>

<div class="pie-chart-container">
	{#if title}
		<h3 class="chart-title">{title}</h3>
	{/if}

	<div class="chart-shell" class:chart-shell--legend={showLegend}>
		<div class="chart-wrapper" style={`height: ${height}px;`}>
			{#if chartSegments().length === 0}
				<div class="no-data">No data available</div>
			{:else}
				<div class="chart-stage">
					<svg
						viewBox={`0 0 ${chartSize} ${chartSize}`}
						class="chart-graphic"
						role="img"
						aria-label={title ? `${title} chart` : 'Breakdown chart'}
					>
						<title>{title ? `${title} chart` : 'Breakdown chart'}</title>
						<circle
							class="chart-track"
							cx={chartCenter}
							cy={chartCenter}
							r={chartRadius}
							fill="none"
							stroke="rgba(148, 163, 184, 0.18)"
							stroke-width={strokeWidth}
						/>
						<g transform={`rotate(-90 ${chartCenter} ${chartCenter})`}>
							{#each chartSegments() as segment, index (segment.label)}
								<circle
									class="chart-segment"
									class:is-active={index === activeSegmentIndex}
									cx={chartCenter}
									cy={chartCenter}
									r={chartRadius}
									fill="none"
									stroke={segment.color}
									stroke-width={strokeWidth}
									stroke-dasharray={segment.dasharray}
									stroke-dashoffset={segment.dashoffset}
									role="button"
									tabindex="0"
									aria-label={`${segment.label}: ${formatValue(segment.value)}`}
									onclick={() => {
										activateSegment(index);
									}}
									onkeydown={(event) => {
										handleSegmentKeydown(event, index);
									}}
									onfocus={() => {
										activateSegment(index);
									}}
									onpointerenter={() => {
										activateSegment(index);
									}}
								>
									<title>
										{segment.label}: {formatValue(segment.value)} ({(
											segment.percentage * 100
										).toFixed(1)}%)
									</title>
								</circle>
							{/each}
						</g>
					</svg>

					{#if activeSegment()}
						<div class="chart-center-copy" aria-live="polite">
							<span>{activeSegment()?.label}</span>
							<strong>{formatValue(activeSegment()?.value ?? 0)}</strong>
							<small>{((activeSegment()?.percentage ?? 0) * 100).toFixed(1)}% of total</small>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		{#if showLegend && chartSegments().length > 0}
			<ul class="chart-legend" role="list">
				{#each chartSegments() as segment, index (segment.label)}
					<li>
						<button
							type="button"
							class:active={index === activeSegmentIndex}
							onclick={() => {
								activateSegment(index);
							}}
							onfocus={() => {
								activateSegment(index);
							}}
						>
							<span class="legend-swatch" style={`background: ${segment.color};`}></span>
							<span class="legend-copy">
								<strong>
									{showPercentage
										? `${segment.label} (${(segment.percentage * 100).toFixed(1)}%)`
										: segment.label}
								</strong>
								<small>{formatValue(segment.value)}</small>
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	{#if total() > 0}
		<p class="chart-total">Total: {formatValue(total())}</p>
	{/if}
</div>

<style>
	.pie-chart-container {
		background: var(--card-bg, #0f172a);
		border-radius: 12px;
		padding: 1.5rem;
		border: 1px solid var(--border-color, #1e293b);
	}

	.chart-title {
		font-size: 1rem;
		font-weight: 600;
		color: var(--text-primary, #f8fafc);
		margin: 0 0 1rem;
	}

	.chart-shell {
		display: grid;
		align-items: center;
	}

	.chart-shell--legend {
		grid-template-columns: minmax(0, 1fr) minmax(15rem, 18rem);
		gap: 1rem;
	}

	.chart-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.chart-stage {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: min(100%, 16rem);
		aspect-ratio: 1;
	}

	.chart-graphic {
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	.chart-segment {
		cursor: pointer;
		transition:
			transform 180ms ease,
			filter 180ms ease,
			stroke-width 180ms ease;
		transform-origin: center;
	}

	.chart-segment:is(:hover, :focus-visible),
	.chart-segment.is-active {
		stroke-width: calc(24px + 2px);
		filter: drop-shadow(0 0 10px rgb(14 165 233 / 0.18));
		outline: none;
	}

	.chart-center-copy {
		position: absolute;
		inset: 0;
		display: grid;
		place-content: center;
		gap: 0.18rem;
		padding: 0 2rem;
		text-align: center;
		pointer-events: none;
	}

	.chart-center-copy span,
	.chart-total {
		font-size: 0.72rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-muted, #94a3b8);
	}

	.chart-center-copy strong {
		font-size: 1.2rem;
		font-weight: 700;
		color: var(--text-primary, #f8fafc);
		line-height: 1.15;
	}

	.chart-center-copy small {
		font-size: 0.78rem;
		color: var(--text-muted, #94a3b8);
	}

	.chart-legend {
		display: grid;
		gap: 0.65rem;
		padding: 0;
		margin: 0;
		list-style: none;
	}

	.chart-legend button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.7rem 0.85rem;
		border: 1px solid rgba(148, 163, 184, 0.12);
		border-radius: 0.9rem;
		background: rgba(15, 23, 42, 0.42);
		text-align: left;
		transition:
			border-color 180ms ease,
			background 180ms ease,
			transform 180ms ease;
	}

	.chart-legend button:is(:hover, :focus-visible),
	.chart-legend button.active {
		border-color: rgba(14, 165, 233, 0.32);
		background: rgba(15, 23, 42, 0.62);
		transform: translateY(-1px);
		outline: none;
	}

	.legend-swatch {
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 999px;
		flex: 0 0 auto;
	}

	.legend-copy {
		display: grid;
		gap: 0.1rem;
	}

	.legend-copy strong {
		font-size: 0.86rem;
		font-weight: 600;
		color: var(--text-primary, #f8fafc);
	}

	.legend-copy small {
		font-size: 0.8rem;
		color: var(--text-muted, #94a3b8);
	}

	.no-data {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--text-muted, #64748b);
		font-size: 0.875rem;
	}

	.chart-total {
		margin: 1rem 0 0;
	}

	@media (max-width: 720px) {
		.chart-shell--legend {
			grid-template-columns: 1fr;
		}

		.chart-stage {
			width: min(100%, 14rem);
		}
	}
</style>
