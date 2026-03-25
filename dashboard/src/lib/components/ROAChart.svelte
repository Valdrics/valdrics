<script lang="ts">
	import { Activity, TrendingUp } from '@lucide/svelte';

	const labels = [
		'Jan',
		'Feb',
		'Mar',
		'Apr',
		'May',
		'Jun',
		'Jul',
		'Aug',
		'Sep',
		'Oct',
		'Nov',
		'Dec'
	];
	const savingsData = [
		1200, 2500, 3900, 5400, 7100, 9000, 11200, 13700, 16500, 19600, 23000, 26800
	];

	const chartWidth = 640;
	const chartHeight = 260;
	const padding = { top: 20, right: 20, bottom: 34, left: 44 };
	const plotWidth = chartWidth - padding.left - padding.right;
	const plotHeight = chartHeight - padding.top - padding.bottom;

	let activePointIndex = $state(savingsData.length - 1);

	function formatCurrency(amount: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			maximumFractionDigits: 0
		}).format(amount);
	}

	function formatAxisTick(amount: number): string {
		return amount >= 1000 ? `$${Math.round(amount / 1000)}k` : `$${amount}`;
	}

	let maxValue = Math.ceil(Math.max(...savingsData) / 2000) * 2000;
	let minValue = 0;
	let tickValues = Array.from(
		{ length: 5 },
		(_, index) => minValue + ((maxValue - minValue) / 4) * index
	);

	type ChartPoint = {
		label: string;
		value: number;
		x: number;
		y: number;
	};

	let points = $derived(() =>
		savingsData.map((value, index) => {
			const x = padding.left + (index / (savingsData.length - 1)) * plotWidth;
			const normalized = (value - minValue) / (maxValue - minValue || 1);
			const y = padding.top + plotHeight - normalized * plotHeight;
			return { label: labels[index], value, x, y };
		})
	);

	let linePath = $derived(() =>
		points()
			.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
			.join(' ')
	);
	let areaPath = $derived(
		() =>
			`${linePath()} L ${points()[points().length - 1]?.x ?? padding.left} ${padding.top + plotHeight} L ${points()[0]?.x ?? padding.left} ${padding.top + plotHeight} Z`
	);
	let activePoint = $derived(
		() => points()[activePointIndex] ?? points()[points().length - 1] ?? null
	);

	function activatePoint(index: number): void {
		activePointIndex = index;
	}

	function handlePointKeydown(event: KeyboardEvent, index: number): void {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		activatePoint(index);
	}
</script>

<div class="roa-chart glass-panel stagger-enter" style="animation-delay: 300ms;">
	<div class="header">
		<div class="title-area">
			<div class="icon-wrap">
				<Activity size={18} color="#a78bfa" />
			</div>
			<div>
				<h3>12-Month ROA</h3>
				<p class="subtitle">Return on Automation Projection</p>
			</div>
		</div>
		<div class="growth-stats">
			<TrendingUp size={14} class="text-green-400" />
			<span class="growth-value">+22% MoM</span>
		</div>
	</div>

	<div class="chart-summary" aria-live="polite">
		<div>
			<span class="summary-label">Highlighted month</span>
			<strong>{activePoint()?.label ?? 'Dec'}</strong>
		</div>
		<div>
			<span class="summary-label">Projected savings</span>
			<strong>{formatCurrency(activePoint()?.value ?? savingsData[savingsData.length - 1])}</strong>
		</div>
	</div>

	<div class="chart-wrapper">
		<ul class="sr-only" aria-label="Monthly savings projection values">
			{#each points() as point (point.label)}
				<li>{point.label}: {formatCurrency(point.value)}</li>
			{/each}
		</ul>
		<svg
			viewBox={`0 0 ${chartWidth} ${chartHeight}`}
			class="chart-svg"
			role="img"
			aria-label="12-month return on automation projection"
		>
			<title>12-month return on automation projection</title>
			<defs>
				<linearGradient id="roaAreaFill" x1="0%" y1="0%" x2="0%" y2="100%">
					<stop offset="0%" stop-color="#3b82f6" stop-opacity="0.42" />
					<stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
				</linearGradient>
			</defs>

			{#each tickValues as tick}
				{@const y =
					padding.top + plotHeight - ((tick - minValue) / (maxValue - minValue || 1)) * plotHeight}
				<line class="grid-line" x1={padding.left} y1={y} x2={chartWidth - padding.right} y2={y}
				></line>
				<text class="axis-label axis-label--y" x={padding.left - 10} y={y + 4}>
					{formatAxisTick(tick)}
				</text>
			{/each}

			{#each points() as point}
				<text class="axis-label axis-label--x" x={point.x} y={chartHeight - 8}>{point.label}</text>
			{/each}

			<path class="area-path" d={areaPath()}></path>
			<path class="line-path" d={linePath()}></path>

			{#each points() as point, index (point.label)}
				<g class:point-active={index === activePointIndex}>
					<circle class="point-halo" cx={point.x} cy={point.y} r="11"></circle>
					<circle
						class="point-core"
						cx={point.x}
						cy={point.y}
						r="4.5"
						role="button"
						tabindex="0"
						aria-label={`${point.label}: ${formatCurrency(point.value)}`}
						onclick={() => {
							activatePoint(index);
						}}
						onkeydown={(event) => {
							handlePointKeydown(event, index);
						}}
						onfocus={() => {
							activatePoint(index);
						}}
						onpointerenter={() => {
							activatePoint(index);
						}}
					>
						<title>{point.label}: {formatCurrency(point.value)}</title>
					</circle>
				</g>
			{/each}
		</svg>
	</div>

	<div class="footer">
		<div class="footer-item">
			<span class="label">Projected EOY Savings</span>
			<span class="value text-accent-400">$26,800</span>
		</div>
		<div class="footer-item">
			<span class="label">Automation Score</span>
			<span class="value text-green-400">94/100</span>
		</div>
	</div>
</div>

<style>
	.roa-chart {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		min-height: 380px;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
	}

	.title-area {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}

	.icon-wrap {
		width: 36px;
		height: 36px;
		background: rgba(139, 92, 246, 0.1);
		border: 1px solid rgba(139, 92, 246, 0.2);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	h3 {
		font-size: 0.9375rem;
		font-weight: 600;
		color: #f8fafc;
		margin: 0;
	}

	.subtitle {
		font-size: var(--text-xs);
		color: #94a3b8;
		margin: 0;
	}

	.growth-stats {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: rgba(34, 197, 94, 0.1);
		padding: 0.25rem 0.5rem;
		border-radius: 6px;
	}

	.growth-value {
		font-size: var(--text-xs);
		font-weight: 700;
		color: #4ade80;
	}

	.chart-summary {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}

	.chart-summary div {
		display: grid;
		gap: 0.18rem;
		padding: 0.75rem 0.85rem;
		border-radius: 0.85rem;
		border: 1px solid rgba(148, 163, 184, 0.12);
		background: rgba(15, 23, 42, 0.42);
	}

	.summary-label,
	.label,
	.axis-label {
		font-size: var(--text-xs);
		text-transform: uppercase;
		color: #64748b;
		letter-spacing: 0.05em;
	}

	.chart-summary strong {
		font-size: 1rem;
		font-weight: 700;
		color: #f8fafc;
	}

	.chart-wrapper {
		position: relative;
		flex: 1;
		min-height: 220px;
	}

	.chart-svg {
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	.grid-line {
		stroke: rgba(51, 65, 85, 0.28);
		stroke-width: 1;
	}

	.axis-label {
		fill: #64748b;
	}

	.axis-label--y {
		text-anchor: end;
	}

	.axis-label--x {
		text-anchor: middle;
	}

	.area-path {
		fill: url(#roaAreaFill);
	}

	.line-path {
		fill: none;
		stroke: #3b82f6;
		stroke-width: 3;
		stroke-linecap: round;
		stroke-linejoin: round;
		filter: drop-shadow(0 10px 18px rgb(59 130 246 / 0.12));
	}

	.point-halo {
		fill: transparent;
		transition: fill 180ms ease;
	}

	.point-core {
		fill: #3b82f6;
		stroke: #0f172a;
		stroke-width: 2;
		cursor: pointer;
		transition:
			r 180ms ease,
			filter 180ms ease;
	}

	.point-core:is(:focus-visible, :hover),
	.point-active .point-core {
		r: 6;
		filter: drop-shadow(0 0 10px rgb(59 130 246 / 0.25));
		outline: none;
	}

	.point-active .point-halo {
		fill: rgba(59, 130, 246, 0.08);
	}

	.footer {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(51, 65, 85, 0.4);
	}

	.footer-item {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.value {
		font-size: 1.125rem;
		font-weight: 700;
	}

	@media (max-width: 640px) {
		.chart-summary,
		.footer {
			grid-template-columns: 1fr;
		}
	}
</style>
