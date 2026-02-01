<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { EventResponse, EventList, EventCreate, EventUpdate } from '$lib/types';
	import CalendarGrid from '$lib/components/calendar/CalendarGrid.svelte';
	import EventModal from '$lib/components/calendar/EventModal.svelte';
	import { Plus } from 'lucide-svelte';

	let events = $state<EventResponse[]>([]);
	let currentDate = $state(new Date());
	let loading = $state(true);

	let modalOpen = $state(false);
	let selectedEvent = $state<EventResponse | null>(null);
	let selectedDate = $state('');

	function getMonthRange(date: Date): { start: string; end: string } {
		const year = date.getFullYear();
		const month = date.getMonth();
		const start = new Date(year, month, 1);
		const end = new Date(year, month + 1, 0);
		// Extend to show padding days
		start.setDate(start.getDate() - start.getDay());
		end.setDate(end.getDate() + (6 - end.getDay()));
		return {
			start: formatDate(start),
			end: formatDate(end)
		};
	}

	function formatDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	async function loadEvents() {
		loading = true;
		try {
			const { start, end } = getMonthRange(currentDate);
			const res = await api.get<EventList>(
				`/api/calendar/events?start_date=${start}&end_date=${end}`
			);
			events = res.events;
		} catch {
			toasts.error('Failed to load events');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		currentDate;
		loadEvents();
	});

	function prevMonth() {
		currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
	}

	function nextMonth() {
		currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
	}

	function handleDayClick(date: Date) {
		selectedEvent = null;
		selectedDate = formatDate(date);
		modalOpen = true;
	}

	function handleEventClick(event: EventResponse) {
		selectedEvent = event;
		selectedDate = '';
		modalOpen = true;
	}

	function handleNewEvent() {
		selectedEvent = null;
		selectedDate = formatDate(new Date());
		modalOpen = true;
	}

	async function handleSave(data: EventCreate | EventUpdate) {
		try {
			if (selectedEvent) {
				const updated = await api.put<EventResponse>(
					`/api/calendar/events/${selectedEvent.id}`,
					data
				);
				events = events.map((e) => (e.id === updated.id ? updated : e));
				toasts.success('Event updated');
			} else {
				const created = await api.post<EventResponse>('/api/calendar/events', data);
				events = [...events, created];
				toasts.success('Event created');
			}
			modalOpen = false;
		} catch {
			toasts.error('Failed to save event');
		}
	}

	async function handleDelete(eventId: string) {
		try {
			await api.delete(`/api/calendar/events/${eventId}`);
			events = events.filter((e) => e.id !== eventId);
			modalOpen = false;
			toasts.success('Event deleted');
		} catch {
			toasts.error('Failed to delete event');
		}
	}

	function handleModalClose() {
		modalOpen = false;
		selectedEvent = null;
	}
</script>

<div class="flex items-center justify-end mb-4">
	<button class="btn btn-primary btn-sm" onclick={handleNewEvent}>
		<Plus size={16} />
		New Event
	</button>
</div>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else}
	<div class="h-[calc(100vh-12rem)]">
		<CalendarGrid
			{events}
			{currentDate}
			onprevmonth={prevMonth}
			onnextmonth={nextMonth}
			ondayclick={handleDayClick}
			oneventclick={handleEventClick}
		/>
	</div>
{/if}

<EventModal
	bind:open={modalOpen}
	event={selectedEvent}
	defaultDate={selectedDate}
	onsave={handleSave}
	ondelete={handleDelete}
	onclose={handleModalClose}
/>
