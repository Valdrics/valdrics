<script lang="ts">
	import { browser } from '$app/environment';
	import { base } from '$app/paths';
	import PublicMarketingPage from '$lib/components/public/PublicMarketingPage.svelte';
	import PublicPageMeta from '$lib/components/public/PublicPageMeta.svelte';
	import { getTurnstileToken } from '$lib/security/turnstile';
	import {
		createInitialSalesInquiryForm,
		heroHighlights,
		interestAreaOptions,
		mapSalesInquiryError,
		normalizeOptionalField,
		resolveSalesInquirySource,
		responseChecklist,
		salesMailHref,
		sidebarCards,
		teamSizeOptions,
		timelineOptions,
		type SalesInquiryForm
	} from './talk-to-sales-page-content';
	import './talk-to-sales-page.css';

	type SubmitState = 'idle' | 'submitting' | 'success' | 'error';
	let form = $state<SalesInquiryForm>(createInitialSalesInquiryForm());
	let submitState = $state<SubmitState>('idle');
	let statusMessage = $state('');
	let inquiryId = $state('');

	async function submitInquiry(event: SubmitEvent) {
		event.preventDefault();
		if (submitState === 'submitting') return;

		submitState = 'submitting';
		statusMessage = '';
		inquiryId = '';

		try {
			const turnstileToken = await getTurnstileToken('public_sales_intake');
			const currentUrl = browser ? new URL(window.location.href) : null;
			const payload = {
				name: form.name.trim(),
				email: form.email.trim().toLowerCase(),
				company: form.company.trim(),
				role: normalizeOptionalField(form.role),
				teamSize: normalizeOptionalField(form.teamSize),
				deploymentScope: normalizeOptionalField(form.deploymentScope),
				timeline: normalizeOptionalField(form.timeline),
				interestArea: normalizeOptionalField(form.interestArea),
				message: normalizeOptionalField(form.message),
				referrer: browser ? normalizeOptionalField(document.referrer) : undefined,
				source: resolveSalesInquirySource(currentUrl),
				utmSource: currentUrl?.searchParams.get('utm_source') || undefined,
				utmMedium: currentUrl?.searchParams.get('utm_medium') || undefined,
				utmCampaign: currentUrl?.searchParams.get('utm_campaign') || undefined,
				honey: normalizeOptionalField(form.honey)
			};

			const response = await fetch(`${base}/api/marketing/talk-to-sales`, {
				method: 'POST',
				headers: {
					'content-type': 'application/json',
					...(turnstileToken ? { 'x-turnstile-token': turnstileToken } : {})
				},
				body: JSON.stringify(payload)
			});
			const body = (await response.json().catch(() => ({ ok: false, error: 'delivery_failed' }))) as {
				ok?: boolean;
				error?: string;
				inquiryId?: string;
			};

			if (!response.ok || !body.ok) {
				submitState = 'error';
				statusMessage = mapSalesInquiryError(body.error);
				return;
			}

			submitState = 'success';
			inquiryId = body.inquiryId || '';
			statusMessage =
				'Inquiry received. We will route it to the right sales path and follow up from a human inbox.';
			form = createInitialSalesInquiryForm();
		} catch (error) {
			submitState = 'error';
			statusMessage =
				error instanceof Error && error.message.includes('turnstile')
					? mapSalesInquiryError(error.message)
					: mapSalesInquiryError('delivery_failed');
		}
	}
</script>

<PublicPageMeta
	title="Talk to Sales"
	description="Start a real Valdrics sales inquiry for rollout planning, security review, pricing fit, and procurement-ready buyer support."
	pageType="ContactPage"
	pageSection="Sales"
	keywords={['talk to sales', 'enterprise', 'pricing fit', 'security review', 'procurement']}
/>

<PublicMarketingPage
	kicker="Sales Path"
	title="Talk to Sales"
	subtitle="Route the buying motion correctly from the start. Share your scope, timing, and review needs once, and we will steer you to the right Valdrics path without restarting the conversation."
	heroVariant="narrow"
>
	{#snippet heroActions()}
		<a href="#sales-inquiry-form" class="btn btn-primary">Start sales inquiry</a>
		<a href={`${base}/enterprise`} class="btn btn-secondary">Explore Enterprise Overview</a>
		<a href={`${base}/auth/login?intent=talk_to_sales&entry=talk_to_sales`} class="btn btn-secondary">
			Start Free Instead
		</a>
	{/snippet}

	{#snippet heroMeta()}
		{#each heroHighlights as item (item.label)}
			<article class="public-page__meta-item">
				<strong>{item.label}</strong>
				<span>{item.value}</span>
			</article>
		{/each}
	{/snippet}

	{#snippet children()}
		<section class="public-page__section sales-page__section" aria-labelledby="sales-inquiry-title">
			<div class="public-page__section-head">
				<p class="public-page__eyebrow">Primary path</p>
				<h2 id="sales-inquiry-title" class="public-page__section-title">Send one inquiry, get the right path</h2>
				<p class="public-page__section-subtitle">
					Use the form when you want plan-fit guidance, rollout clarity, security review support, or a
					procurement-ready conversation.
				</p>
			</div>

			<div class="sales-page__grid">
				<div class="sales-page__form-shell">
					<form
						id="sales-inquiry-form"
						class="sales-page__form-card"
						aria-describedby="sales-inquiry-support"
						aria-busy={submitState === 'submitting'}
						onsubmit={submitInquiry}
					>
						<div class="sales-page__form-head">
							<div>
								<p class="public-page__eyebrow">Inquiry form</p>
								<h3 class="sales-page__form-title">Talk to a human, not a dead-end inbox</h3>
							</div>
							<p id="sales-inquiry-support" class="sales-page__form-copy">
								Most qualified inquiries receive a human response within one business day.
							</p>
						</div>

						<div class="sales-page__field-grid sales-page__field-grid--2">
							<label class="sales-page__field">
								<span>Name</span>
								<input
									type="text"
									name="name"
									maxlength="120"
									autocomplete="name"
									required
									bind:value={form.name}
								/>
							</label>
							<label class="sales-page__field">
								<span>Work email</span>
								<input
									type="email"
									name="email"
									maxlength="254"
									autocomplete="email"
									required
									bind:value={form.email}
								/>
							</label>
							<label class="sales-page__field">
								<span>Company</span>
								<input
									type="text"
									name="company"
									maxlength="120"
									autocomplete="organization"
									required
									bind:value={form.company}
								/>
							</label>
							<label class="sales-page__field">
								<span>Role</span>
								<input
									type="text"
									name="role"
									maxlength="120"
									autocomplete="organization-title"
									placeholder="FinOps lead, platform engineering, procurement"
									bind:value={form.role}
								/>
							</label>
							<label class="sales-page__field">
								<span>Team size</span>
								<select name="teamSize" bind:value={form.teamSize}>
									{#each teamSizeOptions as option (option.value)}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>
							</label>
							<label class="sales-page__field">
								<span>Target timeline</span>
								<select name="timeline" bind:value={form.timeline}>
									{#each timelineOptions as option (option.value)}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>
							</label>
						</div>

						<div class="sales-page__field-grid">
							<label class="sales-page__field">
								<span>Primary interest area</span>
								<select name="interestArea" bind:value={form.interestArea}>
									{#each interestAreaOptions as option (option.value)}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>
							</label>
							<label class="sales-page__field">
								<span>Cloud and SaaS scope</span>
								<input
									type="text"
									name="deploymentScope"
									maxlength="200"
									placeholder="AWS + Azure, Microsoft 365, Salesforce, Datadog"
									bind:value={form.deploymentScope}
								/>
							</label>
							<label class="sales-page__field">
								<span>Message</span>
								<textarea
									name="message"
									rows="5"
									maxlength="2000"
									placeholder="Share the rollout context, security questions, or commercial review blockers."
									bind:value={form.message}
								></textarea>
							</label>
							<label class="sales-page__field sales-page__field--honeypot" aria-hidden="true">
								<span>Leave this field blank</span>
								<input type="text" name="companyWebsite" tabindex="-1" autocomplete="off" bind:value={form.honey} />
							</label>
						</div>

						<div class="sales-page__form-footer">
							<div class="sales-page__status-wrap">
								{#if submitState !== 'idle' && statusMessage}
									<p
										class={`sales-page__status sales-page__status--${submitState}`}
										role={submitState === 'error' ? 'alert' : 'status'}
									>
										{statusMessage}
										{#if inquiryId}
											<span class="sales-page__status-id">Reference: {inquiryId}</span>
										{/if}
									</p>
								{/if}
							</div>
							<div class="sales-page__actions">
								<button type="submit" class="btn btn-primary" disabled={submitState === 'submitting'}>
									{submitState === 'submitting' ? 'Sending inquiry…' : 'Send inquiry'}
								</button>
								<a href={salesMailHref} class="btn btn-secondary">Email instead</a>
							</div>
						</div>
					</form>
				</div>

				<aside class="sales-page__sidebar" aria-label="Sales page guidance">
					<div class="sales-page__rail-card sales-page__rail-card--dark">
						<p class="public-page__card-kicker">What happens next</p>
						<h3 class="public-page__card-title">We route the review correctly from the first reply</h3>
						<ul class="public-page__list">
							{#each responseChecklist as item (item)}
								<li>{item}</li>
							{/each}
						</ul>
					</div>

					{#each sidebarCards as card (card.title)}
						<article class="sales-page__rail-card">
							<p class="public-page__card-kicker">{card.kicker}</p>
							<h3 class="public-page__card-title">{card.title}</h3>
							<p class="public-page__card-copy">{card.copy}</p>
							{#if card.kicker === 'Fallback'}
								<a href={salesMailHref} class="sales-page__mail-link">enterprise@valdrics.com</a>
							{/if}
						</article>
					{/each}
				</aside>
			</div>
		</section>

		<section class="public-page__section">
			<div class="public-page__band public-page__band--dark sales-page__band">
				<div class="public-page__band-copy sales-page__band-copy">
					<p class="public-page__eyebrow">Review shortcuts</p>
					<h2 class="public-page__section-title">Need to verify before you book time?</h2>
					<p class="public-page__section-subtitle">
						Use the enterprise overview, proof pack, and resources library to answer the first round of
						questions before the live conversation.
					</p>
				</div>
				<div class="public-page__actions-row">
					<a href={`${base}/enterprise`} class="btn btn-primary">Enterprise Overview</a>
					<a href={`${base}/proof`} class="btn btn-secondary">Open Proof Pack</a>
					<a href={`${base}/resources`} class="btn btn-secondary">Browse Resources</a>
				</div>
			</div>
		</section>
	{/snippet}
</PublicMarketingPage>
