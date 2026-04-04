<script lang="ts">
	import {
		PUBLIC_CONTACT_CHANNELS,
		PUBLIC_FOOTER_BADGES,
		PUBLIC_FOOTER_CAPTION,
		PUBLIC_FOOTER_LINK_GROUPS,
		PUBLIC_FOOTER_SUBTITLE
	} from '$lib/landing/publicNav';

	interface Props {
		currentYear: number;
		toAppPath: (path: string) => string;
	}

	let { currentYear, toAppPath }: Props = $props();
</script>

<footer class="public-site-footer">
	<div class="public-site-footer__inner container mx-auto px-6 py-12">
		<div class="public-site-footer__top">
			<div class="public-site-footer__brand-block">
				<p class="public-footer-brand">Valdrics</p>
				<p class="public-footer-subtitle">{PUBLIC_FOOTER_SUBTITLE}</p>
				<p class="public-footer-caption">{PUBLIC_FOOTER_CAPTION}</p>
			</div>

			<nav class="public-site-footer__links" aria-label="Footer">
				{#each PUBLIC_FOOTER_LINK_GROUPS as group (group.heading)}
					<div class="public-footer-group">
						<p class="public-footer-group-label">{group.heading}</p>
						<div class="public-footer-group-links">
							{#each group.links as link (link.href)}
								{#if link.external}
									<a
										href={link.href}
										target="_blank"
										rel="noopener noreferrer"
										class="public-footer-link"
									>
										{link.label}
									</a>
								{:else}
									<a
										href={toAppPath(link.href)}
										class="public-footer-link"
										data-sveltekit-preload-data="hover"
										data-sveltekit-preload-code="hover"
									>
										{link.label}
									</a>
								{/if}
							{/each}
						</div>
					</div>
				{/each}
			</nav>

			<div class="public-site-footer__contact-block" aria-label="Public contact channels">
				<p class="public-footer-group-label">Contact</p>
				<div class="public-site-footer__contact-list">
					{#each PUBLIC_CONTACT_CHANNELS as channel (channel.email)}
						<a
							href={channel.href}
							class="badge badge-default public-footer-contact"
							aria-label={`${channel.label} contact ${channel.email}`}
						>
							{channel.label}: {channel.email}
						</a>
					{/each}
				</div>
			</div>
		</div>

		<div class="public-site-footer__bottom">
			<div class="public-site-footer__badges" aria-label="Technology badges">
				{#each PUBLIC_FOOTER_BADGES as badge (badge)}
					<span
						class={`badge ${badge === 'Owner-routed actions' ? 'badge-success' : 'badge-default'}`}
					>
						{badge}
					</span>
				{/each}
			</div>
			<p class="public-footer-copyright">© {currentYear} Valdrics. All rights reserved.</p>
		</div>
	</div>
</footer>
