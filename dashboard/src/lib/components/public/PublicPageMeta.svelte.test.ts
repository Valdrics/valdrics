import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import { readable } from 'svelte/store';

import PublicPageMeta from './PublicPageMeta.svelte';

vi.mock('$app/paths', () => ({
	assets: ''
}));

vi.mock('$app/stores', () => ({
	page: readable({ url: new URL('https://example.com/talk-to-sales') })
}));

describe('PublicPageMeta', () => {
	afterEach(() => {
		cleanup();
		document.head.innerHTML = '';
	});

	it('renders JSON-LD in head without injecting extra markup', () => {
		render(PublicPageMeta, {
			title: 'Talk to Sales </script><meta name="oops" content="x">',
			description: 'Route the buying motion correctly from the start.',
			pageType: 'ContactPage',
			pageSection: 'Sales',
			keywords: ['talk to sales', 'sales']
		});

		const structuredDataScripts = document.head.querySelectorAll('script[type="application/ld+json"]');
		expect(structuredDataScripts).toHaveLength(1);
		expect(structuredDataScripts[0]?.textContent).toContain('"@type":"ContactPage"');
		expect(structuredDataScripts[0]?.textContent).toContain('\\u003c/script>');
		expect(document.head.querySelector('meta[name="oops"]')).toBeNull();
		expect(document.head.innerHTML).not.toContain('{@html');
	});
});
