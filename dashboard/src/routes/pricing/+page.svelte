<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { trackProductFunnelStage } from '$lib/funnel/productFunnelTelemetry';
	import {
		FREE_TIER_HIGHLIGHTS,
		FREE_TIER_LIMIT_NOTE,
		PLANS_PRICING_EXPLANATION
	} from '$lib/landing/heroContent.extended';
	import { normalizeCheckoutUrl } from '$lib/utils';
	import type { PageData } from './$types';
	import type { PricingPlan, PricingPlanStory } from './plans';
	import { DEFAULT_PRICING_PLANS, mergePricingPlans } from './plans';
	import { PRICING_BUYING_NOTES, PRICING_HERO_META } from './pricingPageContent';
	import './pricing-page.css';

	type BillingCycle = 'monthly' | 'annual';

	let { data }: { data: PageData } = $props();

	let billingCycle = $state<BillingCycle>('monthly');
	let upgrading = $state('');
	let error = $state('');
	let pricingViewTracked = $state(false);

	let plans = $derived<PricingPlan[]>(
		mergePricingPlans(
			Array.isArray(data.plans) && data.plans.length > 0 ? data.plans : DEFAULT_PRICING_PLANS
		)
	);
	let freePlan = $derived(plans.find((plan) => plan.id === 'free') ?? null);
	let paidPlans = $derived(plans.filter((plan) => plan.id !== 'free'));
	let currentTier = $derived(String(data.subscription?.tier ?? 'free').trim().toLowerCase());

	$effect(() => {
		if (pricingViewTracked || !data.user || !data.session?.access_token) {
			return;
		}
		pricingViewTracked = true;
		void trackProductFunnelStage({
			accessToken: data.session.access_token,
			stage: 'pricing_viewed',
			tenantId: data.user?.tenant_id,
			url: $page.url,
			currentTier,
			persona: String(data.profile?.persona ?? ''),
			source: 'pricing_page'
		});
	});

	function getPlanStory(plan: PricingPlan): PricingPlanStory {
		return (
			plan.story ?? {
				badge: plan.popular ? 'Recommended paid plan' : 'Plan',
				headline: plan.name,
				summary: plan.description,
				note: plan.description,
				bestFor: plan.description,
				whyUpgrade: plan.description
			}
		);
	}

	function formatUsd(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			maximumFractionDigits: 0
		}).format(value);
	}

	function getDisplayedMonthlyPrice(plan: PricingPlan): number {
		return billingCycle === 'monthly' ? plan.price_monthly : Math.round(plan.price_annual / 12);
	}

	function getAnnualSavings(plan: PricingPlan): number {
		return Math.max(plan.price_monthly * 12 - plan.price_annual, 0);
	}

	function getSignupHref(planId: string): string {
		return `${base}/auth/login?mode=signup&plan=${planId}&cycle=${billingCycle}`;
	}

	function getFreeTierHref(): string {
		return data.user ? `${base}/onboarding?intent=pricing_free` : getSignupHref('free');
	}

	function isCurrentPlan(planId: string): boolean {
		return Boolean(data.user && currentTier === planId);
	}

	async function selectPlan(planId: string) {
		if (upgrading || isCurrentPlan(planId)) return;
		if (planId === 'free') {
			await goto(getFreeTierHref());
			return;
		}

		if (!data.user) {
			await goto(getSignupHref(planId));
			return;
		}

		upgrading = planId;

		try {
			const session = data.session;
			if (!session) throw new Error('Not authenticated');

			const res = await api.post(
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

			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || 'Checkout failed');
			}

			const { checkout_url } = await res.json();
			await trackProductFunnelStage({
				accessToken: session.access_token,
				stage: 'checkout_started',
				tenantId: data.user?.tenant_id,
				url: $page.url,
				currentTier,
				persona: String(data.profile?.persona ?? ''),
				source: `pricing_${billingCycle}`
			}).catch(() => false);
			window.location.assign(normalizeCheckoutUrl(checkout_url, window.location.origin));
		} catch (e) {
			const err = e as Error;
			error = err.message;
			upgrading = '';
		}
	}
</script>

<PublicPageMeta
	title="Pricing"
	description="Simple, transparent Valdrics pricing. Start on the permanent free tier, prove one governed workflow, and upgrade only when you need broader provider coverage, stronger owner routing, or finance-grade governance."
	pageType="WebPage"
	pageSection="Pricing"
	keywords={['pricing', 'free tier', 'starter', 'growth', 'pro', 'enterprise']}
/>

<PublicMarketingPage
	kicker="Pricing"
	title="Simple, transparent pricing"
	subtitle="Start on the permanent free tier, prove one governed workflow, and upgrade only when you need broader provider coverage, stronger owner routing, or finance-grade governance."
>
	{#snippet heroActions()}
		<a href={getFreeTierHref()} class="btn btn-primary">Start Free</a>
		<a href={`${base}/talk-to-sales`} class="btn btn-secondary">Talk to Sales</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each PRICING_HERO_META as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		{#if error}
			<div class="pricing-alert" role="alert">
				<p>{error}</p>
				<button type="button" onclick={() => (error = '')}>Dismiss</button>
			</div>
		{/if}

		<section class="public-page__section" aria-labelledby="pricing-self-serve-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Self-serve plans</p>
				<h2 id="pricing-self-serve-title" class="public-page__section-title">
					Choose the plan that matches your control depth
				</h2>
				<p class="public-page__section-subtitle">
					{PLANS_PRICING_EXPLANATION} Switch to annual billing to compare the lower effective monthly
					rate.
				</p>
			</div>

			<div class="pricing-cycle">
				<div class="pricing-cycle__copy">
					<p class="pricing-cycle__kicker">Billing cycle</p>
					<p class="pricing-cycle__note">Annual billing lowers the effective monthly price on paid plans.</p>
				</div>
				<div class="pricing-cycle__toggle" role="group" aria-label="Billing cycle">
					<span class:active={billingCycle === 'monthly'}>Monthly</span>
					<button
						type="button"
						class={`pricing-cycle__switch ${billingCycle === 'annual' ? 'annual' : ''}`}
						onclick={() => (billingCycle = billingCycle === 'monthly' ? 'annual' : 'monthly')}
						aria-label="Toggle billing cycle"
						role="switch"
						aria-checked={billingCycle === 'annual'}
					>
						<span class="pricing-cycle__knob"></span>
					</button>
					<span class:active={billingCycle === 'annual'}>
						Annual
						<span class="pricing-cycle__badge">Save 17%</span>
					</span>
				</div>
			</div>

			{#if freePlan}
				{@const freeStory = getPlanStory(freePlan)}
				<article class="public-page__card public-page__card--accent pricing-entry-card">
					<div class="pricing-entry-card__head">
						<div class="pricing-entry-card__copy">
							<p class="public-page__card-kicker">{freeStory.badge}</p>
							<h3 class="public-page__card-title">{freeStory.headline}</h3>
							<p class="public-page__card-copy">{freeStory.summary}</p>
						</div>
						<div class="pricing-entry-card__price">
							<p class="pricing-entry-card__price-label">Entry price</p>
							<p class="pricing-entry-card__price-value">$0</p>
						</div>
					</div>

					<ul class="public-page__list">
						{#each FREE_TIER_HIGHLIGHTS as feature (feature)}
							<li>{feature}</li>
						{/each}
					</ul>

					<dl class="pricing-plan-context" aria-label="Free plan fit and upgrade path">
						<div class="pricing-plan-context__row">
							<dt class="pricing-plan-context__label">Best for</dt>
							<dd class="pricing-plan-context__value">{freeStory.bestFor}</dd>
						</div>
						<div class="pricing-plan-context__row">
							<dt class="pricing-plan-context__label">Why teams upgrade</dt>
							<dd class="pricing-plan-context__value">{freeStory.whyUpgrade}</dd>
						</div>
					</dl>

					<div class="pricing-entry-card__footer">
						<p class="public-page__inline-note">{FREE_TIER_LIMIT_NOTE}</p>
						<div class="public-page__actions-row">
							<a href={getFreeTierHref()} class="btn btn-primary">Start on Free Tier</a>
							{#if isCurrentPlan('free')}
								<span class="pricing-current-plan">Current plan active</span>
							{:else}
								<span class="pricing-support-note">Upgrade later if you need more automation.</span>
							{/if}
						</div>
					</div>
				</article>
			{/if}

			<div class="pricing-plan-grid">
				{#each paidPlans as plan (plan.id)}
					{@const story = getPlanStory(plan)}
					<article
						class={`public-page__card pricing-plan-card ${plan.popular ? 'public-page__card--featured pricing-plan-card--popular' : ''}`}
					>
						<div class="pricing-plan-card__head">
							<div>
								<p class="public-page__card-kicker">{story.badge}</p>
								<h3 class="public-page__card-title">{plan.name}</h3>
							</div>
							{#if isCurrentPlan(plan.id)}
								<span class="pricing-current-plan">Current plan</span>
							{/if}
						</div>

						<p class="public-page__card-copy">{story.summary}</p>

						<div class="pricing-plan-price">
							<span class="pricing-plan-price__currency">$</span>
							<span class="pricing-plan-price__amount">{getDisplayedMonthlyPrice(plan)}</span>
							<span class="pricing-plan-price__period">
								{billingCycle === 'monthly' ? '/mo' : '/mo billed annually'}
							</span>
						</div>

						<p class="pricing-plan-price__note">
							{billingCycle === 'annual'
								? `${formatUsd(plan.price_annual)} billed yearly. Effective ${formatUsd(getDisplayedMonthlyPrice(plan))}/mo. ${story.note}`
								: `${formatUsd(plan.price_monthly)}/mo starting price. ${story.note}`}
						</p>

						<ul class="public-page__list">
							{#each plan.features as feature (feature)}
								<li>{feature}</li>
							{/each}
						</ul>

						<dl class="pricing-plan-context" aria-label={`${plan.name} plan fit and upgrade path`}>
							<div class="pricing-plan-context__row">
								<dt class="pricing-plan-context__label">Best for</dt>
								<dd class="pricing-plan-context__value">{story.bestFor}</dd>
							</div>
							<div class="pricing-plan-context__row">
								<dt class="pricing-plan-context__label">Why teams upgrade</dt>
								<dd class="pricing-plan-context__value">{story.whyUpgrade}</dd>
							</div>
						</dl>

						<div class="pricing-plan-card__footer">
							{#if isCurrentPlan(plan.id)}
								<button type="button" class="btn btn-secondary pricing-plan-button" disabled>
									Current Plan
								</button>
							{:else if data.user}
								<button
									type="button"
									class={`btn ${plan.popular ? 'btn-primary' : 'btn-secondary'} pricing-plan-button`}
									onclick={() => void selectPlan(plan.id)}
									disabled={!!upgrading}
									aria-label={`${plan.cta} for ${plan.name} plan`}
								>
									{#if upgrading === plan.id}
										<span class="pricing-spinner" aria-hidden="true"></span>
										Processing...
									{:else}
										{plan.cta}
									{/if}
								</button>
							{:else}
								<a
									href={getSignupHref(plan.id)}
									class={`btn ${plan.popular ? 'btn-primary' : 'btn-secondary'} pricing-plan-button`}
								>
									{plan.cta}
								</a>
							{/if}

							<p class="pricing-support-note">
								{billingCycle === 'annual' && getAnnualSavings(plan) > 0
									? `Save ${formatUsd(getAnnualSavings(plan))} per year versus monthly billing.`
									: story.note}
							</p>
						</div>
					</article>
				{/each}
			</div>
		</section>

		<section class="public-page__section" aria-labelledby="pricing-enterprise-title">
			<div class="public-page__band public-page__band--dark">
				<div class="public-page__band-copy">
					<p class="public-page__eyebrow">Need enterprise review?</p>
					<h2 id="pricing-enterprise-title" class="public-page__section-title">
						Use the enterprise lane only when security or procurement needs a separate track
					</h2>
					<p class="public-page__section-subtitle">
						Otherwise, start on Free, Starter, Growth, or Pro. Bring in sales when SCIM,
						private deployment, procurement, or custom control requirements need their own buying path.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={`${base}/talk-to-sales`} class="btn btn-primary">Talk to Sales</a>
					<a href={`${base}/enterprise`} class="btn btn-secondary">View Enterprise Overview</a>
				</div>
				<div class="public-page__badge-cloud pricing-buying-notes">
					{#each PRICING_BUYING_NOTES as item (item)}
						<span class="public-page__badge">{item}</span>
					{/each}
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
