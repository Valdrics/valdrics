<!--
  Pricing Page - Public Landing Page for Plans
  
  Features:
  - USD pricing with NGN payment note
  - BYOK available in current plans with no additional platform surcharge
  - Highlight Growth as "Most Popular"
  - Permanent free tier CTA
  - Feature comparison table
-->

<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { assets, base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { edgeApiPath } from '$lib/edgeProxy';
	import { normalizeCheckoutUrl } from '$lib/utils';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import type { PricingPlan } from './plans';
	import { DEFAULT_PRICING_PLANS } from './plans';
	import './pricing-page.css';

	let { data }: { data: PageData } = $props();

	let billingCycle = $state('monthly'); // 'monthly' or 'annual'
	let upgrading = $state(''); // plan ID being upgraded to
	let error = $state(''); // error message for display
	let plans = $derived<PricingPlan[]>(
		Array.isArray(data.plans) && data.plans.length > 0 ? data.plans : DEFAULT_PRICING_PLANS
	);

	async function selectPlan(planId: string) {
		if (upgrading) return;

		// If not logged in, redirect to signup
		if (!data.user) {
			goto(`${base}/auth/login?mode=signup&plan=${planId}&cycle=${billingCycle}`);
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
			window.location.assign(normalizeCheckoutUrl(checkout_url, window.location.origin));
		} catch (e) {
			const err = e as Error;
			error = err.message;
			upgrading = '';
		}
	}
</script>

<svelte:head>
	<title>Pricing | Valdrics</title>
	<meta
		name="description"
		content="Simple, transparent pricing for cloud cost optimization. Start on a permanent free tier, with BYOK available in current plans."
	/>
	<meta property="og:title" content="Pricing | Valdrics" />
	<meta
		property="og:description"
		content="Simple, transparent pricing for cloud cost optimization. Start on a permanent free tier, with BYOK available in current plans."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:url" content={new URL($page.url.pathname, $page.url.origin).toString()} />
	<meta
		property="og:image"
		content={new URL(`${assets}/og-image.png`, $page.url.origin).toString()}
	/>
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Pricing | Valdrics" />
	<meta
		name="twitter:description"
		content="Simple, transparent pricing for cloud cost optimization. Start on a permanent free tier, with BYOK available in current plans."
	/>
	<meta
		name="twitter:image"
		content={new URL(`${assets}/og-image.png`, $page.url.origin).toString()}
	/>
</svelte:head>

<div class="pricing-page">
	<!-- Hero Section -->
	<div class="hero-section">
		<h1 class="hero-title">Simple, Transparent Pricing</h1>
		<p class="hero-subtitle">
			Start with a <strong>permanent free tier</strong>. BYOK is available across current plans with
			no additional platform surcharge.
		</p>

		<!-- Cycle Toggle -->
		<div class="cycle-toggle-container">
			<span class={billingCycle === 'monthly' ? 'active' : ''}>Monthly</span>
			<button
				type="button"
				class="cycle-toggle-switch {billingCycle === 'annual' ? 'annual' : ''}"
				onclick={() => (billingCycle = billingCycle === 'monthly' ? 'annual' : 'monthly')}
				aria-label="Toggle billing cycle"
				role="switch"
				aria-checked={billingCycle === 'annual'}
			>
				<span class="toggle-knob"></span>
			</button>
			<span class={billingCycle === 'annual' ? 'active' : ''}>
				Yearly
				<span class="savings-badge">Save 17%</span>
			</span>
		</div>
	</div>

	{#if error}
		<div class="error-banner">
			<p>{error}</p>
			<button type="button" onclick={() => (error = '')}>Dismiss</button>
		</div>
	{/if}

	<!-- Pricing Grid -->
	<div class="pricing-grid">
		{#each plans as plan, i (plan.id)}
			<div
				class="pricing-card {plan.popular ? 'popular' : ''}"
				style="animation-delay: {i * 100}ms;"
			>
				{#if plan.popular}
					<div class="popular-badge">Most Popular</div>
				{/if}

				<div class="card-header">
					<h2 class="plan-name">{plan.name}</h2>
					<p class="plan-description">{plan.description}</p>
				</div>

				<div class="plan-price">
					<span class="currency">$</span>
					<span class="amount">
						{billingCycle === 'monthly' ? plan.price_monthly : Math.round(plan.price_annual / 12)}
					</span>
					<span class="period">
						{billingCycle === 'monthly' ? '/mo' : '/mo, billed yearly'}
					</span>
				</div>

				<ul class="feature-list">
					{#each plan.features as feature (feature)}
						<li>
							<span class="check-icon">✓</span>
							{feature}
						</li>
					{/each}
				</ul>

				<button
					type="button"
					class="cta-button {plan.popular ? 'primary' : 'secondary'}"
					onclick={() => selectPlan(plan.id)}
					disabled={!!upgrading}
					aria-label="{plan.cta} for {plan.name} plan"
				>
					{#if upgrading === plan.id}
						<span class="spinner" aria-hidden="true"></span>
						Processing...
					{:else}
						{plan.cta}
					{/if}
				</button>
			</div>
		{/each}
	</div>

	<!-- Enterprise Section -->
	<div class="enterprise-section">
		<div class="enterprise-content">
			<h2>Enterprise Governance</h2>
			<p>
				Optional advanced path for organizations that require formal controls, procurement workflows,
				and expanded governance support.
			</p>
			<ul>
				<li>Advanced security and identity controls (SSO/SCIM)</li>
				<li>Procurement and due-diligence support lane</li>
				<li>Priority support and commercial governance alignment</li>
				<li>Custom integrations for complex operating environments</li>
			</ul>
		</div>
		<div class="enterprise-cta-group">
			<a href="mailto:enterprise@valdrics.com?cc=sales@valdrics.com" class="enterprise-cta"
				>Contact Sales</a
			>
			<a href={`${base}/enterprise`} class="enterprise-cta enterprise-cta-secondary">
				View Enterprise Overview
			</a>
		</div>
	</div>

	<!-- Payment Note -->
	<div class="payment-note">
		<p>
			<strong>Secure payments via Paystack.</strong>
			Prices are listed in USD. Checkout is currently processed in NGN at the live exchange rate. BYOK
			does not add a separate platform surcharge.
		</p>
	</div>

	<!-- FAQ Section -->
	<div class="faq-section">
		<h2>Frequently Asked Questions</h2>

		<div class="faq-grid">
			<div class="faq-item">
				<h3>How does the free tier work?</h3>
				<p>
					The free tier is permanent with usage limits. Upgrade anytime when you need more scale.
				</p>
			</div>

			<div class="faq-item">
				<h3>Is BYOK available on every tier?</h3>
				<p>
					In the current lineup, Free, Starter, Growth, and Pro can use BYOK. Daily AI usage limits
					still apply by tier.
				</p>
			</div>

			<div class="faq-item">
				<h3>Can I upgrade or downgrade anytime?</h3>
				<p>
					You can request plan changes at any time. Most changes take effect on your next billing
					cycle.
				</p>
			</div>

			<div class="faq-item">
				<h3>What cloud providers do you support?</h3>
				<p>Starter supports AWS. Growth and Pro support AWS, Azure, and GCP.</p>
			</div>

			<div class="faq-item">
				<h3>Is my data secure?</h3>
				<p>
					We use read-only cloud roles where supported, and connector secrets are stored encrypted
					at rest.
				</p>
			</div>
		</div>
	</div>
</div>
