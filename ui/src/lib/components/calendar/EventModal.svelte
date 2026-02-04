<script lang="ts">
	import type { EventResponse, EventCreate, EventUpdate } from '$lib/types';
	import { api } from '$lib/services/api';
	import { toLocalISOString } from '$lib/utils/calendar';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import RecurrenceInput from '$lib/components/calendar/RecurrenceInput.svelte';
	import { Trash2, Repeat } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	interface Props {
		open: boolean;
		event?: EventResponse | null;
		defaultDate?: string;
		defaultTime?: string;
		onsaved: (event: EventResponse, isNew: boolean) => void;
		ondeleted?: (id: string) => void;
		onseriesdeleted?: (masterId: string) => void;
		onclose: () => void;
	}

	let { open = $bindable(false), event = null, defaultDate = '', defaultTime = '', onsaved, ondeleted, onseriesdeleted, onclose }: Props = $props();

	let title = $state('');
	let description = $state('');
	let startDate = $state('');
	let startTime = $state('');
	let endDate = $state('');
	let endTime = $state('');
	let allDay = $state(false);
	let location = $state('');
	let rrule = $state<string | null>(null);
	let saving = $state(false);

	let isEditing = $derived(!!event);

	// Recurring instance detection
	let isRecurringInstance = $derived(
		!!(event?.recurring_event_id) || !!(event?.id?.includes('__rec__'))
	);
	let masterEventId = $derived(event?.recurring_event_id ?? null);

	// Reset form when event changes or modal opens
	$effect(() => {
		if (open) {
			if (event) {
				title = event.title;
				description = event.description || '';
				location = event.location || '';
				allDay = event.all_day;
				rrule = event.rrule ?? null;
				const start = new Date(event.start_time);
				startDate = formatLocalDate(start);
				startTime = allDay ? '' : formatLocalTime(start);
				if (event.end_time) {
					const end = new Date(event.end_time);
					endDate = formatLocalDate(end);
					endTime = allDay ? '' : formatLocalTime(end);
				} else {
					endDate = '';
					endTime = '';
				}
			} else {
				title = '';
				description = '';
				location = '';
				allDay = false;
				rrule = null;
				startDate = defaultDate || formatLocalDate(new Date());
				startTime = defaultTime || '';
				endDate = '';
				endTime = '';
			}
		}
	});

	function formatLocalDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function formatLocalTime(d: Date): string {
		return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
	}

	function buildISOString(date: string, time: string): string {
		return toLocalISOString(date, time || undefined);
	}

	async function handleSave() {
		if (!title.trim() || !startDate) return;
		saving = true;

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
			if (event) {
				result = await api.put<EventResponse>(`/api/calendar/events/${event.id}`, data);
				onsaved(result, false);
			} else {
				result = await api.post<EventResponse>('/api/calendar/events', data);
				onsaved(result, true);
			}
			open = false;
		} catch (e) {
			console.error('Failed to save event', e);
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!event || !ondeleted) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Event',
			message: 'Are you sure you want to delete this event?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		ondeleted(event.id);
		open = false;
	}

	async function handleDeleteSeries() {
		const mid = masterEventId || event?.id;
		if (!mid || !onseriesdeleted) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Series',
			message: 'Are you sure you want to delete this entire recurring series?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		onseriesdeleted(mid);
		open = false;
	}
</script>

<Modal bind:open title={isEditing ? 'Edit Event' : 'New Event'} onclose={onclose}>
	<div class="flex flex-col gap-3">
		<Input placeholder="Event title" bind:value={title} />

		<label class="flex items-center gap-2 cursor-pointer">
			<input type="checkbox" class="checkbox checkbox-sm" bind:checked={allDay} />
			<span class="text-sm">All day</span>
		</label>

		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="grid grid-cols-2 gap-2">
			<div>
				<label class="label"><span class="label-text text-xs">Start date</span></label>
				<input type="date" class="input input-bordered input-sm w-full" bind:value={startDate} />
			</div>
			{#if !allDay}
				<div>
					<label class="label"><span class="label-text text-xs">Start time</span></label>
					<input type="time" class="input input-bordered input-sm w-full" bind:value={startTime} />
				</div>
			{/if}
		</div>

		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="grid grid-cols-2 gap-2">
			<div>
				<label class="label"><span class="label-text text-xs">End date</span></label>
				<input type="date" class="input input-bordered input-sm w-full" bind:value={endDate} />
			</div>
			{#if !allDay}
				<div>
					<label class="label"><span class="label-text text-xs">End time</span></label>
					<input type="time" class="input input-bordered input-sm w-full" bind:value={endTime} />
				</div>
			{/if}
		</div>

		<Input placeholder="Location" bind:value={location} />

		<!-- Recurrence -->
		{#if !isRecurringInstance}
			<RecurrenceInput bind:value={rrule} />
		{/if}

		<!-- Recurring instance badge + series controls -->
		{#if isRecurringInstance}
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
			<label class="label"><span class="label-text text-xs">Description</span></label>
			<textarea
				class="textarea textarea-bordered w-full text-sm"
				rows="3"
				placeholder="Event description..."
				bind:value={description}
			></textarea>
		</div>

		<div class="flex items-center gap-2 mt-2">
			<Button variant="primary" loading={saving} onclick={handleSave}>
				{isEditing ? 'Save' : 'Create'}
			</Button>
			{#if isEditing && ondeleted}
				<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
					<Trash2 size={16} />
				</button>
			{/if}
		</div>
	</div>
</Modal>
