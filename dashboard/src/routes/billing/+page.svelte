<script lang="ts">
	import { base } from '$app/paths';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { normalizeCheckoutUrl } from '$lib/utils';

	import type { PageData } from './$types';
	import {
		BILLING_USAGE_LABELS,
		BILLING_USAGE_ORDER,
		canSelfServeCheckout,
		getVisibleBillingPlans,
		mergeBillingPlans,
		type BillingCycle,
		type ConnectionUsageItem
	} from './billingPage';
	import { DEFAULT_PRICING_PLANS, type PricingPlan } from '../pricing/plans';

	type BillingSubscription = {
		tier?: string;
		status?: string;
		next_payment_date?: string | null;
	};

	let { data }: { data: PageData } = $props();

	let billingCycle = $state<BillingCycle>('monthly');
	let upgrading = $state('');
	let error = $state('');
	let subscription = $derived((data.subscription ?? { tier: 'free', status: 'active' }) as BillingSubscription);

	let plans = $derived(
		mergeBillingPlans(
			Array.isArray(data.plans) && data.plans.length > 0 ? data.plans : DEFAULT_PRICING_PLANS
		)
	);
	let currentTier = $derived(String(subscription?.tier ?? 'free').trim().toLowerCase());
	let visiblePlans = $derived(getVisibleBillingPlans(plans, currentTier));
	let hasSelfServeUpgrade = $derived(
		visiblePlans.some((plan) => canSelfServeCheckout(plan.id, currentTier))
	);

	function isCurrentPlan(planId: string): boolean {
		return currentTier === planId;
	}

	function formatUsd(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			maximumFractionDigits: 0
		}).format(value);
	}

	function formatDate(timestamp: string): string {
		return new Intl.DateTimeFormat('en-US', {
			dateStyle: 'medium',
			timeStyle: 'short'
		}).format(new Date(timestamp));
	}

	function getDisplayedMonthlyPrice(plan: PricingPlan): number {
		return billingCycle === 'monthly' ? plan.price_monthly : Math.round(plan.price_annual / 12);
	}

	function getAnnualSavings(plan: PricingPlan): number {
		return Math.max(plan.price_monthly * 12 - plan.price_annual, 0);
	}

	function getUsageItem(provider: (typeof BILLING_USAGE_ORDER)[number]): ConnectionUsageItem {
		return (
			data.usage?.connections?.[provider] ?? {
				connected: 0,
				limit: null,
				remaining: null,
				utilization_percent: null
			}
		);
	}

	function getUsageBarWidth(provider: (typeof BILLING_USAGE_ORDER)[number]): number {
		const utilization = getUsageItem(provider).utilization_percent;
		if (utilization === null) return 0;
		return Math.max(0, Math.min(100, utilization));
	}

	function getActionLabel(plan: PricingPlan): string {
		if (isCurrentPlan(plan.id)) return 'Current plan';
		if (currentTier === 'enterprise') return 'Managed via sales';
		if (!canSelfServeCheckout(plan.id, currentTier)) {
			return plan.id === 'free' ? 'Free tier is for new workspaces' : 'Not available in self-serve';
		}
		return billingCycle === 'annual' ? `${plan.cta} annually` : plan.cta;
	}

	async function upgrade(planId: string) {
		if (upgrading || !canSelfServeCheckout(planId, currentTier)) return;

		upgrading = planId;
		error = '';

		try {
			const session = data.session;
			if (!session?.access_token) {
				throw new Error('Not authenticated');
			}

			const response = await api.post(
				edgeApiPath('/billing/checkout'),
				{
					tier: planId,
					billing_cycle: billingCycle
				},
				{
					headers: {
						Authorization: `Bearer ${session.access_token}`
					}
				}
			);

			if (!response.ok) {
				const payload = await response.json().catch(() => ({}));
				throw new Error(payload?.detail || 'Checkout failed');
			}

			const { checkout_url } = await response.json();
			window.location.assign(normalizeCheckoutUrl(checkout_url, window.location.origin));
		} catch (err) {
			error = err instanceof Error ? err.message : 'Checkout failed';
			upgrading = '';
		}
	}
</script>

<svelte:head>
	<title>Billing | Valdrics</title>
</svelte:head>

<div class="billing-page space-y-8">
	<header class="billing-header">
		<div>
			<p class="billing-header__eyebrow">Billing</p>
			<h1 class="billing-header__title">Subscription and usage</h1>
			<p class="billing-header__copy">
				Manage your current plan, compare upgrade paths, and review connection utilization against
				plan limits.
			</p>
		</div>
			<div class="billing-header__meta">
				<span class="badge badge-success capitalize">{subscription?.status ?? 'active'}</span>
				<span class="billing-header__tier">Current tier: {subscription?.tier ?? 'free'}</span>
			</div>
	</header>

	{#if data.checkoutSuccess}
		<div class="billing-alert billing-alert--success" role="status">
			<p>Checkout started successfully. Finish the payment flow to activate your new plan.</p>
		</div>
	{/if}

	{#if error}
		<div class="billing-alert billing-alert--error" role="alert">
			<p>{error}</p>
			<button type="button" class="btn btn-secondary" onclick={() => (error = '')}>Dismiss</button>
		</div>
	{/if}

	<section class="billing-summary-grid">
			<article class="card billing-current-plan">
				<p class="billing-card__kicker">Current plan</p>
				<h2 class="billing-card__title capitalize">{subscription?.tier ?? 'free'}</h2>
			<p class="billing-card__copy">
				Self-serve checkout supports paid-plan upgrades. For downgrades or enterprise commercial changes,
				contact billing or sales.
			</p>
				<div class="billing-current-plan__meta">
					<span class="badge badge-success capitalize">{subscription?.status ?? 'active'}</span>
					{#if subscription?.next_payment_date}
						<span class="billing-current-plan__date">
							Next billing: {formatDate(subscription.next_payment_date)}
						</span>
					{/if}
				</div>
		</article>

		<article class="card billing-notes">
			<p class="billing-card__kicker">Commercial notes</p>
			<h2 class="billing-card__title">What self-serve covers</h2>
			<ul class="billing-bullets">
				<li>Prices are shown in USD for plan comparison.</li>
				<li>The free tier is permanent for one live workflow; it is not a time-limited trial.</li>
				<li>BYOK does not add a separate platform surcharge in the current lineup.</li>
				<li>Enterprise packaging, procurement, SCIM, and private deployment stay on the sales-assisted path.</li>
			</ul>
		</article>
	</section>

	<section class="space-y-4" aria-labelledby="billing-usage-title">
		<div class="billing-section-head">
			<div>
				<p class="billing-card__kicker">Plan utilization</p>
				<h2 id="billing-usage-title" class="billing-section-head__title">Connection usage by provider</h2>
			</div>
			{#if data.usage}
				<p class="billing-section-head__note">Snapshot generated {formatDate(data.usage.generated_at)}</p>
			{/if}
		</div>

		{#if data.usage}
			<div class="billing-usage-grid">
				{#each BILLING_USAGE_ORDER as provider (provider)}
					{@const usage = getUsageItem(provider)}
					<article class="card billing-usage-card">
						<p class="billing-card__kicker">{BILLING_USAGE_LABELS[provider]}</p>
						<p class="billing-usage-card__value">
							{usage.connected}
							{#if usage.limit !== null}
								<span>/ {usage.limit}</span>
							{/if}
						</p>
						<p class="billing-card__copy">
							{#if usage.limit === null}
								No enforced limit on this tier.
							{:else if usage.remaining === 0}
								At plan limit for this provider.
							{:else}
								{usage.remaining} remaining before the plan limit.
							{/if}
						</p>
						{#if usage.utilization_percent !== null}
							<div
								class="billing-usage-card__bar"
								role="progressbar"
								aria-label={`${BILLING_USAGE_LABELS[provider]} utilization`}
								aria-valuemin={0}
								aria-valuemax={100}
								aria-valuenow={Math.round(usage.utilization_percent)}
							>
								<span style={`width: ${getUsageBarWidth(provider)}%`}></span>
							</div>
							<p class="billing-usage-card__footnote">{usage.utilization_percent}% utilized</p>
						{/if}
					</article>
				{/each}
			</div>
		{:else}
			<article class="card billing-usage-empty">
				<p class="billing-card__copy">
					A live connection-usage snapshot was not available. Plan comparison and checkout remain available.
				</p>
			</article>
		{/if}
	</section>

	<section class="space-y-5" aria-labelledby="billing-plans-title">
		<div class="billing-section-head">
			<div>
				<p class="billing-card__kicker">Upgrade paths</p>
				<h2 id="billing-plans-title" class="billing-section-head__title">Available self-serve plans</h2>
			</div>
			<div class="billing-cycle-toggle" role="group" aria-label="Billing cycle">
				<button
					type="button"
					class:active={billingCycle === 'monthly'}
					onclick={() => (billingCycle = 'monthly')}
				>
					Monthly
				</button>
				<button
					type="button"
					class:active={billingCycle === 'annual'}
					onclick={() => (billingCycle = 'annual')}
				>
					Annual
				</button>
			</div>
		</div>

		{#if !hasSelfServeUpgrade}
			<article class="card billing-upgrade-note">
				<p class="billing-card__copy">
					You are already on the highest available self-serve tier. Use the enterprise lane for security,
					procurement, or custom commercial review.
				</p>
			</article>
		{/if}

		<div class="billing-plan-grid">
			{#each visiblePlans as plan (plan.id)}
				<article class={`card billing-plan-card ${plan.popular ? 'billing-plan-card--popular' : ''}`}>
					<div class="billing-plan-card__head">
						<div>
							<p class="billing-card__kicker">{plan.popular ? 'Most popular' : 'Plan'}</p>
							<h3 class="billing-card__title">{plan.name}</h3>
						</div>
						{#if isCurrentPlan(plan.id)}
							<span class="badge badge-success">Current</span>
						{/if}
					</div>
					<p class="billing-plan-card__price">
						{formatUsd(getDisplayedMonthlyPrice(plan))}
						<span>/mo</span>
					</p>
					<p class="billing-card__copy">{plan.description}</p>
					{#if billingCycle === 'annual' && plan.price_annual > 0}
						<p class="billing-plan-card__annual-note">
							Billed annually at {formatUsd(plan.price_annual)}. Save {formatUsd(getAnnualSavings(plan))}
							per year.
						</p>
					{/if}
					<ul class="billing-bullets">
						{#each plan.features as feature (feature)}
							<li>{feature}</li>
						{/each}
					</ul>
					<button
						type="button"
						class={`btn ${plan.popular ? 'btn-primary' : 'btn-secondary'} w-full`}
						disabled={!!upgrading || !canSelfServeCheckout(plan.id, currentTier)}
						onclick={() => upgrade(plan.id)}
					>
						{#if upgrading === plan.id}
							<span class="spinner"></span>
							Processing...
						{:else}
							{getActionLabel(plan)}
						{/if}
					</button>
				</article>
			{/each}

			<article class="card billing-enterprise-card">
				<p class="billing-card__kicker">Enterprise lane</p>
				<h3 class="billing-card__title">Security, procurement, and rollout review</h3>
				<p class="billing-card__copy">
					Use the sales-assisted lane when your workspace needs SCIM, procurement diligence,
					private deployment, or complex rollout governance.
				</p>
				<ul class="billing-bullets">
					<li>Security and identity review for SCIM and private deployment requirements</li>
					<li>Procurement-ready diligence artifacts and rollout planning</li>
					<li>Commercial alignment for large or complex operating environments</li>
				</ul>
				<div class="billing-enterprise-card__actions">
					<a href={`${base}/talk-to-sales?intent=billing_enterprise`} class="btn btn-primary"
						>Talk to Sales</a
					>
					<a href={`${base}/enterprise`} class="btn btn-secondary">View enterprise overview</a>
				</div>
			</article>
		</div>
	</section>
</div>

<style>
	.billing-page {
		padding-bottom: 1rem;
	}

	.billing-header,
	.billing-section-head,
	.billing-plan-card__head,
	.billing-current-plan__meta,
	.billing-enterprise-card__actions {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}

	.billing-header {
		padding-top: 0.25rem;
	}

	.billing-header__eyebrow,
	.billing-card__kicker {
		margin: 0;
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: var(--color-accent-400);
	}

	.billing-header__title,
	.billing-card__title,
	.billing-section-head__title {
		margin: 0.35rem 0 0;
		font-weight: 700;
	}

	.billing-header__title {
		font-size: clamp(2rem, 3vw, 2.6rem);
	}

	.billing-header__copy,
	.billing-card__copy,
	.billing-section-head__note {
		margin: 0.6rem 0 0;
		max-width: 44rem;
		line-height: 1.7;
		color: var(--color-ink-400);
	}

	.billing-header__meta {
		display: grid;
		justify-items: end;
		gap: 0.55rem;
	}

	.billing-header__tier,
	.billing-current-plan__date,
	.billing-usage-card__footnote,
	.billing-plan-card__annual-note {
		font-size: 0.82rem;
		color: var(--color-ink-500);
	}

	.billing-alert {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem 1.1rem;
		border-radius: 1rem;
		border: 1px solid transparent;
	}

	.billing-alert p {
		margin: 0;
	}

	.billing-alert--success {
		border-color: rgb(34 197 94 / 0.24);
		background: rgb(34 197 94 / 0.1);
		color: rgb(134 239 172);
	}

	.billing-alert--error {
		border-color: rgb(239 68 68 / 0.24);
		background: rgb(239 68 68 / 0.1);
		color: rgb(252 165 165);
	}

	.billing-summary-grid,
	.billing-plan-grid,
	.billing-usage-grid {
		display: grid;
		gap: 1rem;
	}

	.billing-summary-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.billing-usage-grid {
		grid-template-columns: repeat(5, minmax(0, 1fr));
	}

	.billing-plan-grid {
		grid-template-columns: repeat(4, minmax(0, 1fr));
	}

	.billing-current-plan,
	.billing-notes,
	.billing-plan-card,
	.billing-usage-card,
	.billing-enterprise-card {
		display: grid;
		gap: 1rem;
	}

	.billing-plan-card--popular {
		border-color: rgb(18 158 192 / 0.28);
		box-shadow:
			0 0 0 1px rgb(18 158 192 / 0.08),
			0 20px 42px rgb(18 158 192 / 0.12);
	}

	.billing-plan-card__price,
	.billing-usage-card__value {
		margin: 0;
		font-size: clamp(2rem, 3vw, 2.5rem);
		font-weight: 700;
		line-height: 1;
	}

	.billing-plan-card__price span,
	.billing-usage-card__value span {
		font-size: 0.95rem;
		font-weight: 500;
		color: var(--color-ink-500);
	}

	.billing-bullets {
		display: grid;
		gap: 0.7rem;
		padding: 0;
		margin: 0;
		list-style: none;
	}

	.billing-bullets li {
		position: relative;
		padding-left: 1rem;
		line-height: 1.55;
		color: var(--color-ink-300);
	}

	.billing-bullets li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0.56rem;
		width: 0.42rem;
		height: 0.42rem;
		border-radius: 999px;
		background: var(--color-brand-600);
		box-shadow: 0 0 0 4px rgb(18 158 192 / 0.12);
	}

	.billing-cycle-toggle {
		display: inline-flex;
		align-items: center;
		padding: 0.22rem;
		border: 1px solid rgb(255 255 255 / 0.08);
		border-radius: 999px;
		background: rgb(15 23 42 / 0.32);
	}

	.billing-cycle-toggle button {
		border: 0;
		background: transparent;
		color: var(--color-ink-400);
		padding: 0.55rem 0.9rem;
		border-radius: 999px;
		font-size: 0.9rem;
		font-weight: 600;
		cursor: pointer;
	}

	.billing-cycle-toggle button.active {
		background: var(--color-brand-600);
		color: white;
	}

	.billing-usage-card__bar {
		position: relative;
		height: 0.5rem;
		border-radius: 999px;
		background: rgb(148 163 184 / 0.18);
		overflow: hidden;
	}

	.billing-usage-card__bar span {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: linear-gradient(90deg, rgb(18 158 192), rgb(59 130 246));
	}

	.billing-enterprise-card {
		border-style: dashed;
	}

	@media (max-width: 1200px) {
		.billing-usage-grid,
		.billing-plan-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}

	@media (max-width: 900px) {
		.billing-header,
		.billing-section-head,
		.billing-plan-card__head,
		.billing-current-plan__meta,
		.billing-enterprise-card__actions {
			flex-direction: column;
			align-items: flex-start;
		}

		.billing-summary-grid,
		.billing-usage-grid,
		.billing-plan-grid {
			grid-template-columns: 1fr;
		}

		.billing-header__meta {
			justify-items: start;
		}
	}
</style>
