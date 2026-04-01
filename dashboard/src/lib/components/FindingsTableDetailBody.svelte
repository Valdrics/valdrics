<script lang="ts">
	let {
		explanation,
		confidenceReason
	}: {
		explanation: string;
		confidenceReason?: string;
	} = $props();

	const sanitizeOptions = {
		ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'br', 'p', 'ul', 'li', 'code'],
		ALLOWED_ATTR: []
	};

	let domPurifyPromise: Promise<typeof import('dompurify')> | null = null;

	function loadDomPurify(): Promise<typeof import('dompurify')> {
		if (!domPurifyPromise) {
			domPurifyPromise = import('dompurify').catch((error) => {
				domPurifyPromise = null;
				throw error;
			});
		}

		return domPurifyPromise;
	}

	function stripHtml(value: string): string {
		return value
			.replace(/<[^>]+>/g, ' ')
			.replace(/\s+/g, ' ')
			.trim();
	}

	let sanitizedExplanation = $state('');

	$effect(() => {
		const currentExplanation = explanation;
		let cancelled = false;

		sanitizedExplanation = stripHtml(currentExplanation);

		void loadDomPurify()
			.then(({ default: DOMPurify }) => {
				if (cancelled || currentExplanation !== explanation) return;
				sanitizedExplanation = DOMPurify.sanitize(currentExplanation, sanitizeOptions);
			})
			.catch(() => {
				if (!cancelled && currentExplanation === explanation) {
					sanitizedExplanation = stripHtml(currentExplanation);
				}
			});

		return () => {
			cancelled = true;
		};
	});
</script>

<p class="findings-table__explanation">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html sanitizedExplanation}
</p>
{#if confidenceReason}
	<p class="findings-table__confidence-reason">{confidenceReason}</p>
{/if}
