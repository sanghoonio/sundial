<script lang="ts">
	import { base } from '$app/paths';
	import type { EventResponse, EventCreate, EventUpdate, ProjectList, TaskResponse, ProjectResponse } from '$lib/types';
	import { api } from '$lib/services/api';
	import { toLocalISOString } from '$lib/utils/calendar';
	import Input from '$lib/components/ui/Input.svelte';
	import RecurrenceInput from '$lib/components/calendar/RecurrenceInput.svelte';
	import TaskCreateModal from '$lib/components/tasks/TaskCreateModal.svelte';
	import { Trash2, X, Check, Save, StickyNote, ListTodo, Plus, Repeat } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	interface Props {
		event?: EventResponse | null;
		defaultDate?: string;
		defaultTime?: string;
		onsaved: (event: EventResponse, isNew: boolean) => void;
		ondeleted?: (id: string) => void;
		onseriesdeleted?: (masterId: string) => void;
		onclose: () => void;
	}

	let { event = null, defaultDate = '', defaultTime = '', onsaved, ondeleted, onseriesdeleted, onclose }: Props =
		$props();

	let title = $state('');
	let description = $state('');
	let startDate = $state('');
	let startTime = $state('');
	let endDate = $state('');
	let endTime = $state('');
	let allDay = $state(false);
	let location = $state('');
	let rrule = $state<string | null>(null);

	let endTouched = $state(false);
	let saving = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;

	// Track the live event ID so after create we autosave as updates
	let liveEventId = $state<string | null>(null);
	let loaded = $state(false);
	let lastSnapshot = $state('');
	let initEventKey = $state<string | undefined>(undefined);
	let flash = $state(false);
	let flashTimer: ReturnType<typeof setTimeout>;

	let createTaskOpen = $state(false);
	let createTaskProjectId = $state('');
	let createTaskProjects = $state<ProjectResponse[]>([]);
	let editingAsSeries = $state(false);

	// Recurring instance detection: synthetic IDs contain __rec__
	// When editingAsSeries, treat as non-instance so RecurrenceInput renders
	let isRecurringInstance = $derived(
		!editingAsSeries && (!!(event?.recurring_event_id) || !!(event?.id?.includes('__rec__')))
	);
	let masterEventId = $derived(
		editingAsSeries ? liveEventId : (event?.recurring_event_id ?? null)
	);

	// Track linked items from event (may update after task creation)
	let currentLinkedNotes = $derived(event?.linked_notes ?? []);
	let currentLinkedTasks = $state<EventResponse['linked_tasks']>([]);

	// Sync linked tasks from event prop
	$effect(() => {
		currentLinkedTasks = event?.linked_tasks ?? [];
	});

	// Fetch projects for task creation
	$effect(() => {
		if (liveEventId && !createTaskProjectId) {
			api.get<ProjectList>('/api/projects').then((pl) => {
				createTaskProjects = pl.projects;
				if (pl.projects.length > 0) {
					createTaskProjectId = pl.projects[0].id;
				}
			}).catch(() => {});
		}
	});

	function initFromEventData(evt: EventResponse) {
		title = evt.title;
		description = evt.description || '';
		location = evt.location || '';
		allDay = evt.all_day;
		rrule = evt.rrule ?? null;
		const start = new Date(evt.start_time);
		startDate = formatLocalDate(start);
		startTime = evt.all_day ? '' : formatLocalTime(start);
		if (evt.end_time) {
			const end = new Date(evt.end_time);
			endDate = formatLocalDate(end);
			endTime = evt.all_day ? '' : formatLocalTime(end);
		} else {
			endDate = '';
			endTime = '';
		}
		endTouched = true;
	}

	function finishInit() {
		setTimeout(() => {
			lastSnapshot = currentSnapshot();
			loaded = true;
		}, 0);
	}

	// Only re-initialize the form when the event identity actually changes
	// For new events, include defaultDate/defaultTime so clicking a different day re-inits
	$effect(() => {
		const key = event ? event.id : `new:${defaultDate}:${defaultTime}`;
		if (key === initEventKey) return;
		initEventKey = key;
		loaded = false;
		editingAsSeries = false;

		// Trigger flash animation
		clearTimeout(flashTimer);
		flash = true;
		flashTimer = setTimeout(() => (flash = false), 600);

		if (event) {
			// Virtual recurring instance → fetch master event
			if (event.id?.includes('__rec__')) {
				const masterId = event.recurring_event_id || event.id.split('__rec__')[0];
				api.get<EventResponse>(`/api/calendar/events/${masterId}`).then((master) => {
					initFromEventData(master);
					liveEventId = master.id;
					editingAsSeries = true;
					finishInit();
				}).catch(() => {
					initFromEventData(event);
					liveEventId = event!.id;
					finishInit();
				});
				return;
			}
			initFromEventData(event);
			liveEventId = event.id;
		} else {
			title = '';
			description = '';
			location = '';
			allDay = false;
			rrule = null;
			startDate = defaultDate || formatLocalDate(new Date());
			startTime = defaultTime || '12:00';
			endDate = startDate;
			const [h, m] = startTime.split(':').map(Number);
			endTime = h >= 23 ? '23:59' : `${String(h + 1).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
			endTouched = false;
			liveEventId = null;
		}
		finishInit();
	});

	function currentSnapshot(): string {
		return JSON.stringify({ title, description, startDate, startTime, endDate, endTime, allDay, location, rrule });
	}

	// Autosave: debounce 800ms after change
	let autoSaveTimer: ReturnType<typeof setTimeout>;

	$effect(() => {
		if (!loaded) return;
		const snap = currentSnapshot();
		if (snap === lastSnapshot) return;

		saveStatus = 'idle';
		showSavedText = false;
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => handleSave(), 800);
		return () => clearTimeout(autoSaveTimer);
	});

	function formatLocalDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function formatLocalTime(d: Date): string {
		return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
	}

	function plusOneHour(time: string): string {
		const [h, m] = time.split(':').map(Number);
		return h >= 23 ? '23:59' : `${String(h + 1).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
	}

	function handleStartChange() {
		if (!startDate || !startTime) return;
		const endStamp = `${endDate}T${endTime}`;
		const startStamp = `${startDate}T${startTime}`;
		if (!endTouched || endStamp <= startStamp) {
			endDate = startDate;
			endTime = plusOneHour(startTime);
		}
	}

	let endBeforeStart = $derived.by(() => {
		if (!endDate) return false;
		const s = `${startDate}T${startTime || '00:00'}`;
		const e = `${endDate}T${endTime || '00:00'}`;
		return e <= s;
	});

	function buildISOString(date: string, time: string): string {
		return toLocalISOString(date, time || undefined);
	}

	async function handleSave() {
		if (!title.trim() || !startDate || endBeforeStart) return;
		saving = true;
		saveStatus = 'saving';

		const data: EventCreate | EventUpdate = {
			title: title.trim(),
			description: description.trim() || '',
			start_time: buildISOString(startDate, startTime),
			end_time: endDate ? buildISOString(endDate, endTime) : null,
			all_day: allDay,
			location: location.trim() || '',
			rrule: rrule || null
		};

		try {
			let result: EventResponse;
			if (liveEventId) {
				result = await api.put<EventResponse>(`/api/calendar/events/${liveEventId}`, data);
				onsaved(result, false);
			} else {
				(data as EventCreate).original_timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
				result = await api.post<EventResponse>('/api/calendar/events', data);
				liveEventId = result.id;
				onsaved(result, true);
			}
			lastSnapshot = currentSnapshot();
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => {
				showSavedText = false;
				saveStatus = 'idle';
			}, 2000);
		} catch (e) {
			saveStatus = 'error';
			console.error('Failed to save event', e);
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		const id = liveEventId || event?.id;
		if (!id || !ondeleted) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Event',
			message: 'Are you sure you want to delete this event?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		ondeleted(id);
	}

	async function handleDeleteSeries() {
		const mid = masterEventId || liveEventId || event?.id;
		if (!mid || !onseriesdeleted) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Series',
			message: 'Are you sure you want to delete this entire recurring series?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		onseriesdeleted(mid);
	}
</script>

<div
	class="p-3 flex flex-col gap-2 border-t border-base-300 flex-1 transition-colors duration-500 {flash ? 'bg-primary/5' : ''}"
>
	<div class="flex items-center justify-between mb-1">
		<span class="text-sm font-semibold">{liveEventId ? 'Edit Event' : 'New Event'}</span>
		<div class="flex items-center gap-1">
			<button class="btn btn-ghost btn-xs btn-square" title="Save" onclick={handleSave} disabled={saving}>
				{#if saveStatus === 'saving'}
					<span class="loading loading-spinner loading-xs"></span>
				{:else if saveStatus === 'saved'}
					<Check size={14} class="text-success" />
				{:else if saveStatus === 'error'}
					<Save size={14} class="text-error" />
				{:else}
					<Save size={14} />
				{/if}
			</button>
			{#if liveEventId && ondeleted}
				<button class="btn btn-ghost btn-xs btn-square text-error" onclick={handleDelete} title="Delete">
					<Trash2 size={14} />
				</button>
			{/if}
			<button class="btn btn-ghost btn-xs btn-square" onclick={onclose}>
				<X size={14} />
			</button>
		</div>
	</div>

	<Input placeholder="Event title" bind:value={title} />

	<label class="flex items-center gap-2 cursor-pointer">
		<input type="checkbox" class="checkbox checkbox-xs" bind:checked={allDay} />
		<span class="text-xs">All day</span>
	</label>

	<!-- svelte-ignore a11y_label_has_associated_control -->
	<div class="grid gap-1.5" class:grid-cols-2={!allDay}>
		<div>
			<label class="label py-0"><span class="label-text text-xs">Start</span></label>
			<input type="date" class="input input-bordered input-xs w-full" bind:value={startDate} oninput={handleStartChange} />
		</div>
		{#if !allDay}
			<div>
				<label class="label py-0"><span class="label-text text-xs">&nbsp;</span></label>
				<input
					type="time"
					class="input input-bordered input-xs w-full"
					bind:value={startTime}
					oninput={handleStartChange}
				/>
			</div>
		{/if}
	</div>

	<!-- svelte-ignore a11y_label_has_associated_control -->
	<div class="grid gap-1.5" class:grid-cols-2={!allDay}>
		<div>
			<label class="label py-0"><span class="label-text text-xs">End</span></label>
			<input type="date" class="input input-bordered input-xs w-full" class:input-error={endBeforeStart} bind:value={endDate} onchange={() => endTouched = true} />
		</div>
		{#if !allDay}
			<div>
				<label class="label py-0"><span class="label-text text-xs">&nbsp;</span></label>
				<input
					type="time"
					class="input input-bordered input-xs w-full"
					class:input-error={endBeforeStart}
					bind:value={endTime}
					onchange={() => endTouched = true}
				/>
			</div>
		{/if}
	</div>
	{#if endBeforeStart}
		<p class="text-error text-xs -mt-1">End must be after start</p>
	{/if}

	<Input placeholder="Location" bind:value={location} />

	<!-- Recurrence -->
	{#if !isRecurringInstance}
		<RecurrenceInput bind:value={rrule} onchange={() => {
			if (loaded) {
				saveStatus = 'idle';
				showSavedText = false;
				clearTimeout(autoSaveTimer);
				autoSaveTimer = setTimeout(() => handleSave(), 800);
			}
		}} />
	{/if}

	<!-- Recurring series badge + controls -->
	{#if editingAsSeries}
		<div class="flex items-center gap-1.5 text-xs text-info py-1">
			<Repeat size={12} />
			<span>Editing recurring series</span>
		</div>
		{#if onseriesdeleted}
			<button class="btn btn-ghost btn-xs text-error gap-1 self-start" onclick={handleDeleteSeries}>
				<Trash2 size={12} />
				<span>Delete series</span>
			</button>
		{/if}
	{:else if isRecurringInstance}
		<div class="flex items-center gap-1.5 text-xs text-base-content/60 py-1">
			<Repeat size={12} />
			<span>Part of a recurring series</span>
		</div>
		{#if onseriesdeleted}
			<button class="btn btn-ghost btn-xs text-error gap-1 self-start" onclick={handleDeleteSeries}>
				<Trash2 size={12} />
				<span>Delete series</span>
			</button>
		{/if}
	{/if}

	<!-- svelte-ignore a11y_label_has_associated_control -->
	<div>
		<label class="label py-0"><span class="label-text text-xs">Description</span></label>
		<textarea
			class="textarea textarea-bordered w-full text-xs leading-snug"
			rows="2"
			placeholder="Description..."
			bind:value={description}
		></textarea>
	</div>

	<!-- Linked items (existing events only) -->
	{#if liveEventId && (currentLinkedNotes.length > 0 || currentLinkedTasks.length > 0)}
		<div class="border-t border-base-300 pt-2">
			<p class="text-xs text-base-content/50 mb-1">Linked Items</p>
			{#each currentLinkedNotes as ln}
				<a href="{base}/notes/{ln.id}" class="flex items-center gap-1.5 text-xs py-0.5 hover:text-primary transition-colors">
					<StickyNote size={12} class="shrink-0" />
					<span class="truncate">{ln.title}</span>
				</a>
			{/each}
			{#each currentLinkedTasks as lt}
				<a href="{base}/tasks?task={lt.id}" class="flex items-center gap-1.5 text-xs py-0.5 hover:text-primary transition-colors">
					<ListTodo size={12} class="shrink-0" />
					<span class="truncate">{lt.title}</span>
					<span class="badge badge-xs {lt.status === 'done' ? 'badge-success' : 'badge-ghost'}">{lt.status === 'done' ? 'done' : 'in progress'}</span>
				</a>
			{/each}
		</div>
	{/if}

	<!-- Create linked task -->
	{#if liveEventId && createTaskProjectId}
		<button class="btn btn-ghost btn-xs gap-1 self-start" onclick={() => (createTaskOpen = true)}>
			<Plus size={12} />
			<span class="text-xs">Create linked task</span>
		</button>
	{/if}
</div>

{#if liveEventId && createTaskProjectId}
	<TaskCreateModal
		bind:open={createTaskOpen}
		projectId={createTaskProjectId}
		projects={createTaskProjects}
		calendarEventId={liveEventId}
		oncreated={async () => {
			if (liveEventId) {
				const updated = await api.get<EventResponse>(`/api/calendar/events/${liveEventId}`);
				currentLinkedTasks = updated.linked_tasks;
				onsaved(updated, false);
			}
		}}
	/>
{/if}

