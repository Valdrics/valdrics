<script lang="ts">
	let { loading = false }: { loading?: boolean } = $props();
</script>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold mb-1">Ops Center</h1>
		<p class="text-ink-400 text-sm">
			Operate remediation approvals, background jobs, and strategy recommendations.
		</p>
	</div>
</div>

{#if loading}
	<div class="card">
		<div class="skeleton h-6 w-64 mb-4"></div>
		<div class="skeleton h-4 w-full mb-2"></div>
		<div class="skeleton h-4 w-4/5"></div>
	</div>
{/if}
