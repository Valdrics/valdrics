<script lang="ts">
	interface AIData {
		total_monthly_savings?: string;
		summary?: string;
	}
	export let aiData: AIData | null | undefined;
</script>

{#if aiData}
	<div class="glass-panel stagger-enter savings-hero">
		<div class="savings-hero__content">
			<div class="savings-hero__copy">
				<p class="savings-hero__eyebrow">Potential Monthly Savings</p>
				<p class="savings-hero__value">{aiData.total_monthly_savings || '$0.00'}</p>
				<p class="savings-hero__summary">
					{aiData.summary || 'Analysis complete.'}
					<span class="savings-hero__note">
						Value Optimizer: Continuously eliminating waste and technical debt.
					</span>
				</p>
			</div>
			<div class="savings-hero__icon" aria-hidden="true">💰</div>
		</div>
	</div>
{/if}

<style>
	.savings-hero {
		grid-column: 1 / -1;
		animation-delay: 200ms;
	}

	.savings-hero__content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-6);
	}

	.savings-hero__copy {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.savings-hero__eyebrow {
		margin: 0;
		font-size: var(--text-sm);
		color: var(--color-ink-400);
	}

	.savings-hero__value {
		margin: 0;
		font-size: clamp(2.5rem, 5vw, 3.5rem);
		font-weight: 700;
		line-height: 0.95;
		background: linear-gradient(
			135deg,
			var(--color-accent-300) 0%,
			var(--color-success-400) 50%,
			white 100%
		);
		background-clip: text;
		-webkit-text-fill-color: transparent;
	}

	.savings-hero__summary {
		max-width: 34rem;
		margin: 0;
		font-size: var(--text-sm);
		line-height: 1.6;
		color: var(--color-ink-400);
	}

	.savings-hero__note {
		display: block;
		margin-top: var(--space-1);
		font-weight: 600;
		color: var(--color-accent-400);
	}

	.savings-hero__icon {
		flex: none;
		font-size: clamp(3rem, 6vw, 3.75rem);
		animation: savingsHeroFloat 3s ease-in-out infinite;
	}

	@media (max-width: 720px) {
		.savings-hero__content {
			flex-direction: column;
			align-items: flex-start;
		}

		.savings-hero__icon {
			align-self: flex-end;
		}
	}

	@keyframes savingsHeroFloat {
		0%,
		100% {
			transform: translateY(0);
		}

		50% {
			transform: translateY(-8px);
		}
	}
</style>
