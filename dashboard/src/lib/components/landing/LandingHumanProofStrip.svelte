<script lang="ts">
	import { getPublicCustomerCommentsFeed } from '$lib/landing/customerCommentsFeed';

	let {
		aboutHref,
		proofHref,
		docsHref
	}: {
		aboutHref: string;
		proofHref: string;
		docsHref: string;
	} = $props();

	const quotes = getPublicCustomerCommentsFeed().slice(0, 3);
</script>

<section
	id="human-proof"
	class="container mx-auto px-6 pb-16 landing-section-lazy"
	data-landing-section="human_proof"
>
	<div class="landing-section-head">
		<h2 class="landing-h2">Human proof before public logos exist</h2>
		<p class="landing-section-sub">
			The current public story uses labeled design-partner workshop feedback, product proof pages,
			and direct company review instead of fabricated launch-stage social proof.
		</p>
	</div>

	<div class="landing-human-proof-grid">
		{#each quotes as quote (quote.quote)}
			<article class="glass-panel landing-human-proof-card">
				<p class="landing-proof-k">
					{quote.stage === 'customer' ? 'Customer feedback' : 'Design-partner workshop'}
				</p>
				<blockquote>{quote.quote}</blockquote>
				<p class="landing-human-proof-attribution">{quote.attribution}</p>
			</article>
		{/each}
	</div>

	<div class="glass-panel landing-human-proof-actions">
		<div>
			<p class="landing-proof-k">Verify the people and proof directly</p>
			<h3 class="landing-h3">Review the company, the proof pack, and the operating materials</h3>
			<p class="landing-p">
				Background checks should not depend on a sales call alone. Use the company surface, proof
				pack, and technical materials before you connect a source or start procurement.
			</p>
		</div>
		<div class="landing-proof-state-links">
			<a href={aboutHref} class="landing-cta-link">About / Team</a>
			<a href={proofHref} class="landing-cta-link">Open Proof Pack</a>
			<a href={docsHref} class="landing-cta-link">Open Docs</a>
		</div>
	</div>
</section>
