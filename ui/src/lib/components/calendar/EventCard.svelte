<script lang="ts">
	import type { DashboardEvent } from '$lib/types';
	import { Clock, Calendar } from 'lucide-svelte';

	interface Props {
		event: DashboardEvent;
	}

	let { event }: Props = $props();

	function formatTime(iso: string): string {
		return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
	}
</script>

<div class="flex items-center gap-3 py-2">
	<div class="text-primary">
		{#if event.all_day}
			<Calendar size={18} />
		{:else}
			<Clock size={18} />
		{/if}
	</div>
	<div class="flex-1 min-w-0">
		<p class="font-medium truncate">{event.title}</p>
		<p class="text-sm text-base-content/60">
			{#if event.all_day}
				All day
			{:else}
				{formatTime(event.start_time)}
				{#if event.end_time}
					&ndash; {formatTime(event.end_time)}
				{/if}
			{/if}
		</p>
	</div>
</div>
