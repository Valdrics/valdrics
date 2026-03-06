<script lang="ts">
	import type { JobStatus } from './opsTypes';

	let {
		pendingRequestsCount = 0,
		jobStatus = null,
		recommendationsCount = 0
	}: {
		pendingRequestsCount?: number;
		jobStatus?: JobStatus | null;
		recommendationsCount?: number;
	} = $props();
</script>

<div class="grid gap-5 md:grid-cols-5">
	<div class="card card-stat">
		<p class="text-xs text-ink-400 uppercase tracking-wide">Pending Remediation</p>
		<p class="text-3xl font-bold text-warning-400">{pendingRequestsCount}</p>
	</div>
	<div class="card card-stat">
		<p class="text-xs text-ink-400 uppercase tracking-wide">Jobs Pending</p>
		<p class="text-3xl font-bold text-accent-400">{jobStatus?.pending ?? 0}</p>
	</div>
	<div class="card card-stat">
		<p class="text-xs text-ink-400 uppercase tracking-wide">Jobs Running</p>
		<p class="text-3xl font-bold text-warning-400">{jobStatus?.running ?? 0}</p>
	</div>
	<div class="card card-stat">
		<p class="text-xs text-ink-400 uppercase tracking-wide">Jobs Failed</p>
		<p class="text-3xl font-bold text-danger-400">{jobStatus?.failed ?? 0}</p>
	</div>
	<div class="card card-stat">
		<p class="text-xs text-ink-400 uppercase tracking-wide">Open Strategies</p>
		<p class="text-3xl font-bold text-success-400">{recommendationsCount}</p>
	</div>
</div>
