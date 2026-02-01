<script lang="ts">
	import type { EventResponse, EventCreate, EventUpdate } from '$lib/types';
	import { api } from '$lib/services/api';
	import Input from '$lib/components/ui/Input.svelte';
	import { Trash2, X, Check, Save } from 'lucide-svelte';

	interface Props {
		event?: EventResponse | null;
		defaultDate?: string;
		defaultTime?: string;
		onsaved: (event: EventResponse, isNew: boolean) => void;
		ondeleted?: (id: string) => void;
		onclose: () => void;
	}

	let { event = null, defaultDate = '', defaultTime = '', onsaved, ondeleted, onclose }: Props =
		$props();

	let title = $state('');
	let description = $state('');
	let startDate = $state('');
	let startTime = $state('');
	let endDate = $state('');
	let endTime = $state('');
	let allDay = $state(false);
	let location = $state('');

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

	// Only re-initialize the form when the event identity actually changes
	// For new events, include defaultDate/defaultTime so clicking a different day re-inits
	$effect(() => {
		const key = event ? event.id : `new:${defaultDate}:${defaultTime}`;
		if (key === initEventKey) return;
		initEventKey = key;
		loaded = false;

		// Trigger flash animation
		clearTimeout(flashTimer);
		flash = true;
		flashTimer = setTimeout(() => (flash = false), 600);

		if (event) {
			title = event.title;
			description = event.description || '';
			location = event.location || '';
			allDay = event.all_day;
			const start = new Date(event.start_time);
			startDate = formatLocalDate(start);
			startTime = event.all_day ? '' : formatLocalTime(start);
			if (event.end_time) {
				const end = new Date(event.end_time);
				endDate = formatLocalDate(end);
				endTime = event.all_day ? '' : formatLocalTime(end);
			} else {
				endDate = '';
				endTime = '';
			}
			liveEventId = event.id;
		} else {
			title = '';
			description = '';
			location = '';
			allDay = false;
			startDate = defaultDate || formatLocalDate(new Date());
			startTime = defaultTime || '';
			endDate = '';
			endTime = '';
			liveEventId = null;
		}
		setTimeout(() => {
			lastSnapshot = currentSnapshot();
			loaded = true;
		}, 0);
	});

	function currentSnapshot(): string {
		return JSON.stringify({ title, description, startDate, startTime, endDate, endTime, allDay, location });
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

	function buildISOString(date: string, time: string): string {
		if (time) return `${date}T${time}:00`;
		return `${date}T00:00:00`;
	}

	async function handleSave() {
		if (!title.trim() || !startDate) return;
		saving = true;
		saveStatus = 'saving';

		const data: EventCreate | EventUpdate = {
			title: title.trim(),
			description: description.trim() || '',
			start_time: buildISOString(startDate, startTime),
			end_time: endDate ? buildISOString(endDate, endTime) : null,
			all_day: allDay,
			location: location.trim() || ''
		};

		try {
			let result: EventResponse;
			if (liveEventId) {
				result = await api.put<EventResponse>(`/api/calendar/events/${liveEventId}`, data);
				onsaved(result, false);
			} else {
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

	function handleDelete() {
		const id = liveEventId || event?.id;
		if (!id || !ondeleted) return;
		if (!confirm('Delete this event?')) return;
		ondeleted(id);
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
			<input type="date" class="input input-bordered input-xs w-full" bind:value={startDate} />
		</div>
		{#if !allDay}
			<div>
				<label class="label py-0"><span class="label-text text-xs">&nbsp;</span></label>
				<input
					type="time"
					class="input input-bordered input-xs w-full"
					bind:value={startTime}
				/>
			</div>
		{/if}
	</div>

	<!-- svelte-ignore a11y_label_has_associated_control -->
	<div class="grid gap-1.5" class:grid-cols-2={!allDay}>
		<div>
			<label class="label py-0"><span class="label-text text-xs">End</span></label>
			<input type="date" class="input input-bordered input-xs w-full" bind:value={endDate} />
		</div>
		{#if !allDay}
			<div>
				<label class="label py-0"><span class="label-text text-xs">&nbsp;</span></label>
				<input
					type="time"
					class="input input-bordered input-xs w-full"
					bind:value={endTime}
				/>
			</div>
		{/if}
	</div>

	<Input placeholder="Location" bind:value={location} />

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
</div>

