<script lang="ts">
	let {
		proofHref,
		onePagerHref,
		docsHref,
		aboutHref,
		statusHref,
		trustEnterpriseHref,
		requestValidationBriefingHref,
		onTrackCta
	}: {
		proofHref: string;
		onePagerHref: string;
		docsHref: string;
		aboutHref: string;
		statusHref: string;
		trustEnterpriseHref: string;
		requestValidationBriefingHref: string;
		onTrackCta: (action: string, section: string, value: string) => void;
	} = $props();
</script>

<section id="trust" class="landing-public-section" data-landing-section="trust">
	<div class="container mx-auto px-6 py-12">
		<div class="landing-public-section-head">
			<p class="landing-public-eyebrow">Trust</p>
			<h2>Review the company before you talk to us</h2>
			<p>Review the company, proof pack, and technical materials before you book a call.</p>
		</div>
		<div class="landing-public-trust-grid">
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Proof pack</p>
				<h3>Start with the materials, not the pitch</h3>
				<p>Open the proof pack, one-pager, and technical validation notes directly.</p>
				<div class="landing-public-link-list">
					<a href={proofHref} onclick={() => onTrackCta('cta_click', 'trust', 'proof_pack')}>
						Open Proof Pack
					</a>
					<a href={onePagerHref} onclick={() => onTrackCta('cta_click', 'trust', 'one_pager')}>
						Download One-Pager
					</a>
					<a href={docsHref} onclick={() => onTrackCta('cta_click', 'trust', 'docs')}>
						Technical Validation
					</a>
				</div>
			</article>
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Company</p>
				<h3>Know who is behind the product</h3>
				<p>
					Review the founder, company background, and public contact channels before procurement
					starts.
				</p>
				<div class="landing-public-link-list">
					<a href={aboutHref} onclick={() => onTrackCta('cta_click', 'trust', 'about')}>
						About / Team
					</a>
					<a href={statusHref} onclick={() => onTrackCta('cta_click', 'trust', 'status')}>
						Status Page
					</a>
				</div>
			</article>
			<article class="landing-public-surface landing-public-trust-card">
				<p class="landing-public-proof-label">Enterprise review</p>
				<h3>Use enterprise review when it is needed</h3>
				<p>
					Security, privacy, residency, and procurement questions can be handled separately without
					slowing down a basic evaluation.
				</p>
				<div class="landing-public-link-list">
					<a
						href={trustEnterpriseHref}
						onclick={() => onTrackCta('cta_click', 'trust', 'enterprise')}
					>
						Enterprise Review
					</a>
					<a
						href={requestValidationBriefingHref}
						onclick={() => onTrackCta('cta_click', 'trust', 'validation_briefing')}
					>
						Request Validation Briefing
					</a>
				</div>
			</article>
		</div>
	</div>
</section>
