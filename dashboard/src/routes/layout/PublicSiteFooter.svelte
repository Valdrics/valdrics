<script lang="ts">
	import {
		PUBLIC_CONTACT_CHANNELS,
		PUBLIC_FOOTER_BADGES,
		PUBLIC_FOOTER_CAPTION,
		PUBLIC_FOOTER_LINKS,
		PUBLIC_FOOTER_SUBTITLE
	} from '$lib/landing/publicNav';

	interface Props {
		currentYear: number;
		toAppPath: (path: string) => string;
	}

	let { currentYear, toAppPath }: Props = $props();
</script>

<footer class="public-site-footer">
	<div class="container mx-auto px-6 py-10">
		<div class="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
			<div class="space-y-2">
				<p class="public-footer-brand text-sm font-semibold">Valdrics</p>
				<p class="public-footer-subtitle max-w-xl">{PUBLIC_FOOTER_SUBTITLE}</p>
			</div>

			<nav
				class="public-footer-nav grid grid-cols-2 gap-x-6 gap-y-2 md:grid-cols-4"
				aria-label="Footer"
			>
				{#each PUBLIC_FOOTER_LINKS as link (link.href)}
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
			</nav>
		</div>

		<div class="mt-6 flex flex-wrap items-center gap-2" aria-label="Technology badges">
			{#each PUBLIC_FOOTER_BADGES as badge (badge)}
				<span
					class={`badge ${badge === 'Owner-routed actions' ? 'badge-success' : 'badge-default'}`}
				>
					{badge}
				</span>
			{/each}
		</div>

		<p class="public-footer-caption mt-4">{PUBLIC_FOOTER_CAPTION}</p>

		<div class="mt-5 space-y-2" aria-label="Public contact channels">
			<p class="public-footer-contact-label">Contact Channels</p>
			<div class="flex flex-wrap gap-2">
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
		<p class="public-footer-copyright mt-6">© {currentYear} Valdrics. All rights reserved.</p>
	</div>
</footer>
