<script lang="ts">
	import { base } from '$app/paths';
	import { api } from '$lib/services/api';
	import type { DashboardResponse } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import EventCard from '$lib/components/calendar/EventCard.svelte';
	import NoteCard from '$lib/components/notes/NoteCard.svelte';
	import TaskCard from '$lib/components/tasks/TaskCard.svelte';
	import DailySuggestions from '$lib/components/dashboard/DailySuggestions.svelte';
	import { Plus, Calendar, StickyNote, CheckSquare, Sun, Moon, Sunrise, Sunset } from 'lucide-svelte';

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

	function getGreeting(): { text: string; icon: typeof Sun } {
		const hour = new Date().getHours();
		if (hour < 6) return { text: 'Good night', icon: Moon };
		if (hour < 12) return { text: 'Good morning', icon: Sunrise };
		if (hour < 18) return { text: 'Good afternoon', icon: Sun };
		return { text: 'Good evening', icon: Sunset };
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr + 'T00:00:00').toLocaleDateString([], {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}

	let greeting = $derived(getGreeting());
</script>

<div class="max-w-6xl mx-auto px-4 py-6">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else if dashboard}
		<!-- Header -->
		<div class="mb-8">
			<div class="flex items-center gap-3 mb-1">
				<svelte:component this={greeting.icon} size={24} class="text-primary" />
				<h1 class="text-2xl font-semibold">{greeting.text}</h1>
			</div>
			<p class="text-base-content/50">{formatDate(dashboard.date)}</p>
		</div>

		<div class="grid gap-6 md:grid-cols-2">
			<!-- Calendar Events -->
			<Card>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-primary/10 text-primary">
							<Calendar size={16} />
						</div>
						<h2 class="font-semibold">Today's Events</h2>
					</div>
					<a href="{base}/calendar" class="text-xs text-base-content/50 hover:text-base-content transition-colors">
						View all
					</a>
				</div>
				{#if dashboard.calendar_events.length === 0}
					<div class="text-center py-6">
						<Calendar size={32} class="mx-auto text-base-content/20 mb-2" />
						<p class="text-base-content/40 text-sm">No events scheduled</p>
					</div>
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
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-warning/10 text-warning">
							<CheckSquare size={16} />
						</div>
						<h2 class="font-semibold">Tasks Due</h2>
					</div>
					<a href="{base}/tasks" class="btn btn-ghost btn-xs gap-1">
						<Plus size={14} />
						New
					</a>
				</div>
				{#if dashboard.tasks_due.length === 0}
					<div class="text-center py-6">
						<CheckSquare size={32} class="mx-auto text-base-content/20 mb-2" />
						<p class="text-base-content/40 text-sm">No tasks due today</p>
						<a href="{base}/tasks" class="btn btn-ghost btn-xs mt-2 text-primary">
							View all tasks
						</a>
					</div>
				{:else}
					<div class="flex flex-col gap-2">
						{#each dashboard.tasks_due as task}
							<TaskCard {task} compact />
						{/each}
					</div>
				{/if}
			</Card>

			<!-- Recent Notes -->
			<Card>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-success/10 text-success">
							<StickyNote size={16} />
						</div>
						<h2 class="font-semibold">Recent Notes</h2>
					</div>
					<a href="{base}/notes/new" class="btn btn-ghost btn-xs gap-1">
						<Plus size={14} />
						New
					</a>
				</div>
				{#if dashboard.recent_notes.length === 0}
					<div class="text-center py-6">
						<StickyNote size={32} class="mx-auto text-base-content/20 mb-2" />
						<p class="text-base-content/40 text-sm">No notes yet</p>
						<a href="{base}/notes/new" class="btn btn-ghost btn-xs mt-2 text-primary">
							Create your first note
						</a>
					</div>
				{:else}
					<div class="flex flex-col gap-2">
						{#each dashboard.recent_notes as note}
							<NoteCard {note} compact />
						{/each}
					</div>
				{/if}
			</Card>

			<!-- AI Daily Suggestions -->
			<DailySuggestions />
		</div>
	{/if}
</div>
