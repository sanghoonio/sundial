<script lang="ts">
	import { base } from '$app/paths';
	import { api } from '$lib/services/api';
	import type { DashboardResponse, DailySuggestionsResponse, SettingsResponse, DashboardEvent, DashboardTask } from '$lib/types';
	import NoteCard from '$lib/components/notes/NoteCard.svelte';
	import FlipClock from '$lib/components/dashboard/FlipClock.svelte';
	import { TypeWriter } from 'svelte-typewrite';
	import { Plus, Calendar, StickyNote, CheckSquare } from 'lucide-svelte';
	import { ws } from '$lib/stores/websocket.svelte';

	function formatEventTime(event: DashboardEvent): string {
		if (event.all_day) return 'All day';
		const start = new Date(event.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
		if (!event.end_time) return start;
		const end = new Date(event.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
		return `${start} – ${end}`;
	}

	function formatTaskPriority(task: DashboardTask): string {
		const priority = task.priority.charAt(0).toUpperCase() + task.priority.slice(1);
		return priority === 'Medium' ? '' : priority;
	}

	function isTaskOverdue(task: DashboardTask): boolean {
		if (!task.due_date) return false;
		const due = new Date(task.due_date);
		const today = new Date();
		due.setHours(0, 0, 0, 0);
		today.setHours(0, 0, 0, 0);
		return due < today;
	}

	let dashboard = $state<DashboardResponse | null>(null);
	let suggestions = $state<DailySuggestionsResponse | null | 'disabled'>(null);
	let loading = $state(true);
	let visiblePriorities = $state(0);
	let showPriorities = $state(false);

	async function load() {
		try {
			const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
			const tzParam = `?tz=${encodeURIComponent(tz)}`;
			dashboard = await api.get<DashboardResponse>(`/api/dashboard/today${tzParam}`);
			// Check settings then load AI suggestions
			api.get<SettingsResponse>('/api/settings')
				.then(async (settings) => {
					const aiEnabled = settings.ai_enabled && settings.openrouter_api_key?.length > 4;
					if (aiEnabled && settings.ai_daily_suggestions) {
						suggestions = await api.get<DailySuggestionsResponse>(`/api/ai/suggestions/daily${tzParam}`);
					} else {
						suggestions = 'disabled';
					}
				})
				.catch(() => suggestions = 'disabled');
		} catch (e) {
			console.error('Failed to load dashboard', e);
		} finally {
			loading = false;
		}
	}

	function onSummaryEnd() {
		showPriorities = true;
		visiblePriorities = 1;
	}

	function onPriorityEnd() {
		if (suggestions && suggestions !== 'disabled' && visiblePriorities < (suggestions.priorities?.length ?? 0)) {
			visiblePriorities++;
		}
	}

	$effect(() => {
		load();
	});

	// WebSocket: silently refresh dashboard data (no loading spinner, no AI re-fetch)
	$effect(() => {
		return ws.on(
			[
				'note_created', 'note_updated', 'note_deleted',
				'task_created', 'task_updated', 'task_deleted',
				'event_created', 'event_updated', 'event_deleted',
				'project_updated'
			],
			async () => {
				try {
					const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
					const tzParam = `?tz=${encodeURIComponent(tz)}`;
					dashboard = await api.get<DashboardResponse>(`/api/dashboard/today${tzParam}`);
				} catch { /* ignore */ }
			},
			2000
		);
	});
</script>

<div class="min-h-0 md:h-[calc(100vh-4rem)] flex flex-col px-3 overflow-y-auto">
	{#if loading}
		<div class="flex items-center justify-center flex-1">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else if dashboard}
		<!-- Header -->
		<div class="flex flex-col md:flex-row items-center md:items-stretch gap-4 md:gap-6 mb-4 md:mb-6 pt-4 md:pt-0">
			<FlipClock />
			<div class="flex-1 relative w-full min-h-24">
				<div class="ai-terminal">
					{#if suggestions === null}
						<span class="loading-dots">...</span>
					{:else if suggestions === 'disabled'}
						<span class="text-[#e8e8e8]/40">AI features not enabled</span>
					{:else if suggestions?.summary || (suggestions?.priorities && suggestions.priorities.length > 0)}
						{#if suggestions?.summary}
							<p><TypeWriter texts={[suggestions.summary]} repeat={1} typeSpeed={33} endState={{ text: 'typed', caret: 'hidden' }} ontypeend={onSummaryEnd} /></p>
						{/if}
						{#if showPriorities && suggestions?.priorities && suggestions.priorities.length > 0}
							<ul class="mt-2">
								{#each suggestions.priorities.slice(0, visiblePriorities) as priority, i}
									<li>→ <TypeWriter texts={[priority]} repeat={1} typeSpeed={33} endState={{ text: 'typed', caret: 'hidden' }} ontypeend={onPriorityEnd} /></li>
								{/each}
							</ul>
						{/if}
					{:else}
						<span class="text-[#e8e8e8]/40">No suggestions yet</span>
					{/if}
				</div>
			</div>
		</div>

		<!-- Bottom row: 3 sections -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 flex-1 min-h-0 pb-4 md:pb-0">
			<!-- Today's Events -->
			<div class="flex flex-col min-h-0 bg-base-200 rounded-lg px-4 py-4">
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-primary/10 text-primary">
							<Calendar size={16} />
						</div>
						<h2 class="text-sm font-semibold">Today's Events</h2>
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
					<div class="flex-1 overflow-y-auto min-h-0">
						<div class="flex flex-col gap-2">
							{#each dashboard.calendar_events as event}
								<a href="{base}/calendar" class="block p-3 rounded-lg bg-base-100 hover:bg-base-100/80 transition-colors">
									<h3 class="text-sm font-medium truncate">{event.title}</h3>
									<span class="text-xs text-base-content/40">{formatEventTime(event)}</span>
								</a>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<!-- Tasks Due -->
			<div class="flex flex-col min-h-0 bg-base-200 rounded-lg px-4 py-4">
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-warning/10 text-warning">
							<CheckSquare size={16} />
						</div>
						<h2 class="text-sm font-semibold">Tasks Due</h2>
					</div>
					<a href="{base}/tasks" class="btn btn-ghost btn-xs btn-square">
						<Plus size={14} />
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
					<div class="flex-1 overflow-y-auto min-h-0">
						<div class="flex flex-col gap-2">
							{#each dashboard.tasks_due as task}
								<a href="{base}/tasks/{task.project_id}?task={task.id}" class="block p-3 rounded-lg bg-base-100 hover:bg-base-100/80 transition-colors">
									<h3 class="text-sm font-medium truncate">{task.title}</h3>
									<div class="flex items-center gap-2">
										{#if isTaskOverdue(task)}
											<span class="badge badge-xs badge-error">Overdue</span>
										{:else}
											<span class="text-xs text-base-content/40">Due today</span>
										{/if}
										{#if formatTaskPriority(task)}
											<span class="badge badge-xs badge-ghost">{formatTaskPriority(task)} priority</span>
										{/if}
									</div>
								</a>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<!-- Recent Notes -->
			<div class="flex flex-col min-h-0 bg-base-200 rounded-lg px-4 py-4">
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<div class="p-1.5 rounded-lg bg-success/10 text-success">
							<StickyNote size={16} />
						</div>
						<h2 class="text-sm font-semibold">Recent Notes</h2>
					</div>
					<a href="{base}/notes/new" class="btn btn-ghost btn-xs btn-square">
						<Plus size={14} />
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
					<div class="flex-1 overflow-y-auto min-h-0">
						<div class="flex flex-col gap-2">
							{#each dashboard.recent_notes as note}
								<NoteCard {note} compact />
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.ai-terminal {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		min-height: 100%;
		background: #1a1a1a;
		color: #e8e8e8;
		border-radius: 0.375rem;
		padding: 0.75rem 1rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.8rem;
		line-height: 1.5;
		overflow: hidden;
		max-height: 100%;
		transition: max-height 0.3s ease-in-out;
		z-index: 10;
	}

	.ai-terminal:hover {
		max-height: 20rem;
	}


	.loading-dots {
		display: inline-block;
		animation: blink 1.4s infinite;
	}

	@keyframes blink {
		0%, 20% { opacity: 0.2; }
		50% { opacity: 1; }
		80%, 100% { opacity: 0.2; }
	}
</style>
