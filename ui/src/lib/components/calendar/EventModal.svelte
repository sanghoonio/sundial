<script lang="ts">
	import type { EventResponse, EventCreate, EventUpdate } from '$lib/types';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Trash2 } from 'lucide-svelte';

	interface Props {
		open: boolean;
		event?: EventResponse | null;
		defaultDate?: string;
		defaultTime?: string;
		onsave: (data: EventCreate | EventUpdate) => void;
		ondelete?: (id: string) => void;
		onclose: () => void;
	}

	let { open = $bindable(false), event = null, defaultDate = '', defaultTime = '', onsave, ondelete, onclose }: Props = $props();

	let title = $state('');
	let description = $state('');
	let startDate = $state('');
	let startTime = $state('');
	let endDate = $state('');
	let endTime = $state('');
	let allDay = $state(false);
	let location = $state('');
	let saving = $state(false);

	let isEditing = $derived(!!event);

	// Reset form when event changes or modal opens
	$effect(() => {
		if (open) {
			if (event) {
				title = event.title;
				description = event.description || '';
				location = event.location || '';
				allDay = event.all_day;
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
		if (time) {
			return `${date}T${time}:00`;
		}
		return `${date}T00:00:00`;
	}

	async function handleSave() {
		if (!title.trim() || !startDate) return;
		saving = true;
		const data: EventCreate | EventUpdate = {
			title: title.trim(),
			description: description.trim() || undefined,
			start_time: buildISOString(startDate, startTime),
			end_time: endDate ? buildISOString(endDate, endTime) : null,
			all_day: allDay,
			location: location.trim() || undefined
		};
		onsave(data);
		saving = false;
	}

	function handleDelete() {
		if (!event || !ondelete) return;
		if (!confirm('Delete this event?')) return;
		ondelete(event.id);
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
			{#if isEditing && ondelete}
				<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
					<Trash2 size={16} />
				</button>
			{/if}
		</div>
	</div>
</Modal>
