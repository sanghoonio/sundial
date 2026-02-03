<script lang="ts">
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type {
		EventResponse,
		EventList,
		TaskResponse,
		TaskList,
		CalendarItem,
		CalendarSettingsResponse
	} from '$lib/types';
	import { getItemDate } from '$lib/utils/calendar';
	import CalendarToolbar from '$lib/components/calendar/CalendarToolbar.svelte';
	import CalendarGrid from '$lib/components/calendar/CalendarGrid.svelte';
	import WeekView from '$lib/components/calendar/WeekView.svelte';
	import DayView from '$lib/components/calendar/DayView.svelte';
	import AgendaView from '$lib/components/calendar/AgendaView.svelte';
	import MiniCalendar from '$lib/components/calendar/MiniCalendar.svelte';
	import EventPanel from '$lib/components/calendar/EventPanel.svelte';

	type CalendarView = 'month' | 'week' | 'day' | 'agenda';

	let events = $state<EventResponse[]>([]);
	let tasks = $state<TaskResponse[]>([]);
	let currentDate = $state(new Date());
	let view = $state<CalendarView>('month');
	let loading = $state(true);

	let panelOpen = $state(false);
	let selectedEvent = $state<EventResponse | null>(null);
	let selectedDate = $state('');
	let selectedTime = $state('');
	let syncing = $state(false);
	let calSyncEnabled = $state(false);

	function getDateRange(date: Date, v: CalendarView): { start: string; end: string } {
		const fmt = (d: Date) =>
			`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

		if (v === 'month') {
			const year = date.getFullYear();
			const month = date.getMonth();
			const start = new Date(year, month, 1);
			const end = new Date(year, month + 1, 0);
			start.setDate(start.getDate() - start.getDay());
			end.setDate(end.getDate() + (6 - end.getDay()));
			return { start: fmt(start), end: fmt(end) };
		}
		if (v === 'week') {
			const start = new Date(date);
			start.setDate(start.getDate() - start.getDay());
			const end = new Date(start);
			end.setDate(end.getDate() + 6);
			return { start: fmt(start), end: fmt(end) };
		}
		if (v === 'day') {
			return { start: fmt(date), end: fmt(date) };
		}
		// agenda: 30 days forward
		const end = new Date(date);
		end.setDate(end.getDate() + 30);
		return { start: fmt(date), end: fmt(end) };
	}

	function formatDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	let calendarItems = $derived<CalendarItem[]>([
		...events.map((e) => ({ type: 'event' as const, data: e })),
		...tasks
			.filter((t) => t.due_date)
			.map((t) => ({ type: 'task' as const, data: t }))
	]);

	let itemDates = $derived(new Set(calendarItems.map((item) => getItemDate(item)).filter(Boolean)));

	async function loadData() {
		loading = true;
		try {
			const { start, end } = getDateRange(currentDate, view);
			const [eventRes, taskRes] = await Promise.all([
				api.get<EventList>(`/api/calendar/events?start=${start}&end=${end}`),
				api.get<TaskList>(`/api/tasks?due_after=${start}&due_before=${end}&limit=200`)
			]);
			events = eventRes.events;
			tasks = taskRes.tasks;
		} catch (e) {
			console.error('Failed to load calendar data', e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		currentDate;
		view;
		loadData();
	});

	function navigate(direction: -1 | 1) {
		const d = new Date(currentDate);
		if (view === 'month') {
			d.setMonth(d.getMonth() + direction);
		} else if (view === 'week') {
			d.setDate(d.getDate() + 7 * direction);
		} else if (view === 'day') {
			d.setDate(d.getDate() + direction);
		} else {
			d.setDate(d.getDate() + 30 * direction);
		}
		currentDate = d;
	}

	function goToday() {
		currentDate = new Date();
	}

	function switchView(v: CalendarView) {
		view = v;
	}

	function goToDay(date: Date) {
		currentDate = date;
		view = 'day';
	}

	function handleMiniCalendarClick(date: Date) {
		currentDate = date;
	}

	function handleDayClick(date: Date) {
		selectedEvent = null;
		selectedDate = formatDate(date);
		selectedTime = '';
		panelOpen = true;
	}

	function handleItemClick(item: CalendarItem) {
		if (item.type === 'event') {
			selectedEvent = item.data;
			selectedDate = '';
			selectedTime = '';
			panelOpen = true;
		} else {
			goto(`/tasks/${item.data.project_id}`);
		}
	}

	function handleNewEvent() {
		selectedEvent = null;
		selectedDate = formatDate(currentDate);
		selectedTime = '';
		panelOpen = true;
	}

	function handleNewEventAtTime(date: Date, hour: number) {
		selectedEvent = null;
		selectedDate = formatDate(date);
		selectedTime = `${String(hour).padStart(2, '0')}:00`;
		panelOpen = true;
	}

	function handleEventSaved(evt: EventResponse, isNew: boolean) {
		if (isNew) {
			events = [...events, evt];
		} else {
			events = events.map((e) => (e.id === evt.id ? evt : e));
		}
	}

	async function handleEventDeleted(eventId: string) {
		try {
			await api.delete(`/api/calendar/events/${eventId}`);
			events = events.filter((e) => e.id !== eventId);
			panelOpen = false;
		} catch (e) {
			console.error('Failed to delete event', e);
			toast.error('Failed to delete event');
		}
	}

	async function handleSeriesDeleted(masterId: string) {
		try {
			await api.delete(`/api/calendar/events/${masterId}/series`);
			// Remove all events belonging to this series (master, exceptions, and virtual instances)
			events = events.filter(
				(e) => e.id !== masterId && e.recurring_event_id !== masterId && !e.id.startsWith(`${masterId}__rec__`)
			);
			panelOpen = false;
		} catch (e) {
			console.error('Failed to delete series', e);
			toast.error('Failed to delete event series');
		}
	}

	// Periodic sync timer
	$effect(() => {
		let aborted = false;
		let interval: ReturnType<typeof setInterval> | null = null;

		api.get<CalendarSettingsResponse>('/api/calendar/settings').then((calSettings) => {
			if (aborted) return;
			calSyncEnabled = calSettings.sync_enabled;
			if (calSettings.sync_enabled && calSettings.sync_interval_minutes > 0) {
				const ms = calSettings.sync_interval_minutes * 60 * 1000;
				interval = setInterval(async () => {
					try {
						await api.post('/api/calendar/sync');
						loadData();
					} catch (e) {
						console.error('Periodic sync failed', e);
					}
				}, ms);
			}
		}).catch(() => {});

		return () => {
			aborted = true;
			if (interval) clearInterval(interval);
		};
	});

	async function handleSync() {
		syncing = true;
		try {
			await api.post('/api/calendar/sync');
			await loadData();
		} catch (e) {
			console.error('Calendar sync failed', e);
			toast.error('Calendar sync failed');
		} finally {
			syncing = false;
		}
	}

	function handlePanelClose() {
		panelOpen = false;
		selectedEvent = null;
	}
</script>

<div class="absolute inset-0 flex flex-col overflow-hidden">
	<CalendarToolbar
		{currentDate}
		{view}
		{syncing}
		onprev={() => navigate(-1)}
		onnext={() => navigate(1)}
		ontoday={goToday}
		onviewchange={switchView}
		onnewevent={handleNewEvent}
		onsync={calSyncEnabled ? handleSync : undefined}
	/>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else}
		<div class="flex flex-1 overflow-hidden">
			<!-- Main view -->
			<div class="flex-1 min-w-0 overflow-hidden">
				{#if view === 'month'}
					<CalendarGrid
						items={calendarItems}
						{currentDate}
						ondayclick={handleDayClick}
						onitemclick={handleItemClick}
						ondaynumberclick={goToDay}
					/>
				{:else if view === 'week'}
					<WeekView
						items={calendarItems}
						{currentDate}
						onitemclick={handleItemClick}
						onslotclick={handleNewEventAtTime}
						ondaynumberclick={goToDay}
					/>
				{:else if view === 'day'}
					<DayView
						items={calendarItems}
						{currentDate}
						onitemclick={handleItemClick}
						onslotclick={handleNewEventAtTime}
					/>
				{:else if view === 'agenda'}
					<AgendaView
						items={calendarItems}
						onitemclick={handleItemClick}
					/>
				{/if}
			</div>

			<!-- Right sidebar (desktop only) -->
			<div class="hidden lg:flex lg:flex-col w-64 shrink-0 border-l border-base-300 overflow-y-auto">
				<MiniCalendar
					{currentDate}
					{itemDates}
					ondateclick={handleMiniCalendarClick}
				/>

				{#if panelOpen}
					<EventPanel
						event={selectedEvent}
						defaultDate={selectedDate}
						defaultTime={selectedTime}
						onsaved={handleEventSaved}
						ondeleted={handleEventDeleted}
						onseriesdeleted={handleSeriesDeleted}
						onclose={handlePanelClose}
					/>
				{/if}
			</div>
		</div>
	{/if}
</div>
