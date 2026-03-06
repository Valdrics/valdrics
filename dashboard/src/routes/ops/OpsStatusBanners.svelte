<script lang="ts">
	let {
		error = '',
		success = ''
	}: {
		error?: string;
		success?: string;
	} = $props();
</script>

{#if error}
	<div class="card border-danger-500/50 bg-danger-500/10">
		<p class="text-danger-400">{error}</p>
	</div>
{/if}
{#if success}
	<div class="card border-success-500/50 bg-success-500/10">
		<p class="text-success-400">{success}</p>
	</div>
{/if}
