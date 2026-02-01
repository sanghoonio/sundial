<script lang="ts">
	import { api } from '$lib/services/api';
	import type { DashboardResponse } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import EventCard from '$lib/components/calendar/EventCard.svelte';
	import NoteCard from '$lib/components/notes/NoteCard.svelte';
	import TaskCard from '$lib/components/tasks/TaskCard.svelte';
	import { Plus, Calendar, StickyNote, CheckSquare } from 'lucide-svelte';

	let dashboard = $state<DashboardResponse | null>(null);
	let loading = $state(true);

	async function load() {
		try {
			dashboard = await api.get<DashboardResponse>('/api/dashboard/today');
		} catch (e) {
			console.error('Failed to load dashboard', e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		load();
	});

	function formatDate(dateStr: string): string {
		return new Date(dateStr + 'T00:00:00').toLocaleDateString([], {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric'
		});
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if dashboard}
	<div class="mb-6">
		<p class="text-base-content/60">{formatDate(dashboard.date)}</p>
	</div>

	<div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
		<!-- Calendar Events -->
		<Card>
			<div class="flex items-center justify-between mb-3">
				<h2 class="font-semibold flex items-center gap-2">
					<Calendar size={18} />
					Today's Events
				</h2>
			</div>
			{#if dashboard.calendar_events.length === 0}
				<p class="text-base-content/40 text-sm py-4 text-center">No events today</p>
			{:else}
				<div class="divide-y divide-base-200">
					{#each dashboard.calendar_events as event}
						<EventCard {event} />
					{/each}
				</div>
			{/if}
		</Card>

		<!-- Tasks Due -->
		<Card>
			<div class="flex items-center justify-between mb-3">
				<h2 class="font-semibold flex items-center gap-2">
					<CheckSquare size={18} />
					Tasks Due
				</h2>
				<a href="/tasks" class="btn btn-ghost btn-xs">
					<Plus size={14} />
					New
				</a>
			</div>
			{#if dashboard.tasks_due.length === 0}
				<p class="text-base-content/40 text-sm py-4 text-center">No tasks due</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each dashboard.tasks_due as task}
						<TaskCard {task} compact />
					{/each}
				</div>
			{/if}
		</Card>

		<!-- Recent Notes -->
		<Card class="md:col-span-2 xl:col-span-1">
			<div class="flex items-center justify-between mb-3">
				<h2 class="font-semibold flex items-center gap-2">
					<StickyNote size={18} />
					Recent Notes
				</h2>
				<a href="/notes/new" class="btn btn-ghost btn-xs">
					<Plus size={14} />
					New
				</a>
			</div>
			{#if dashboard.recent_notes.length === 0}
				<p class="text-base-content/40 text-sm py-4 text-center">No recent notes</p>
			{:else}
				<div class="flex flex-col gap-2">
					{#each dashboard.recent_notes as note}
						<NoteCard {note} compact />
					{/each}
				</div>
			{/if}
		</Card>
	</div>
{/if}
