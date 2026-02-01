<script lang="ts">
	import type { EventResponse } from '$lib/types';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';

	interface Props {
		events: EventResponse[];
		currentDate: Date;
		onprevmonth: () => void;
		onnextmonth: () => void;
		ondayclick: (date: Date) => void;
		oneventclick: (event: EventResponse) => void;
	}

	let { events, currentDate, onprevmonth, onnextmonth, ondayclick, oneventclick }: Props = $props();

	const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	let calendarDays = $derived.by(() => {
		const year = currentDate.getFullYear();
		const month = currentDate.getMonth();
		const firstDay = new Date(year, month, 1);
		const lastDay = new Date(year, month + 1, 0);
		const startPad = firstDay.getDay();
		const totalDays = lastDay.getDate();

		const days: { date: Date; inMonth: boolean }[] = [];

		// Previous month padding
		for (let i = startPad - 1; i >= 0; i--) {
			const d = new Date(year, month, -i);
			days.push({ date: d, inMonth: false });
		}

		// Current month days
		for (let i = 1; i <= totalDays; i++) {
			days.push({ date: new Date(year, month, i), inMonth: true });
		}

		// Next month padding to fill grid
		const remaining = 7 - (days.length % 7);
		if (remaining < 7) {
			for (let i = 1; i <= remaining; i++) {
				days.push({ date: new Date(year, month + 1, i), inMonth: false });
			}
		}

		return days;
	});

	let monthLabel = $derived(
		currentDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
	);

	function eventsForDate(date: Date): EventResponse[] {
		const dateStr = formatDateKey(date);
		return events.filter((e) => {
			const eventDate = e.all_day
				? e.start_time.split('T')[0]
				: formatDateKey(new Date(e.start_time));
			return eventDate === dateStr;
		});
	}

	function formatDateKey(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function isToday(d: Date): boolean {
		const now = new Date();
		return d.getDate() === now.getDate() &&
			d.getMonth() === now.getMonth() &&
			d.getFullYear() === now.getFullYear();
	}
</script>

<div class="flex flex-col h-full">
	<!-- Month header -->
	<div class="flex items-center justify-between mb-4">
		<button class="btn btn-ghost btn-sm btn-square" onclick={onprevmonth}>
			<ChevronLeft size={18} />
		</button>
		<h2 class="text-lg font-semibold">{monthLabel}</h2>
		<button class="btn btn-ghost btn-sm btn-square" onclick={onnextmonth}>
			<ChevronRight size={18} />
		</button>
	</div>

	<!-- Weekday headers -->
	<div class="grid grid-cols-7 border-b border-base-300">
		{#each weekdays as day}
			<div class="text-center text-xs font-medium text-base-content/60 py-2">{day}</div>
		{/each}
	</div>

	<!-- Day grid -->
	<div class="grid grid-cols-7 flex-1 auto-rows-fr">
		{#each calendarDays as { date, inMonth }}
			{@const dayEvents = eventsForDate(date)}
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div
				class="border border-base-300/50 p-1 min-h-20 text-left flex flex-col
					{inMonth ? '' : 'bg-base-200/50 text-base-content/30'}
					hover:bg-base-200 transition-colors cursor-pointer"
				onclick={() => ondayclick(date)}
			>
				<span
					class="text-xs font-medium inline-flex items-center justify-center w-6 h-6 rounded-full
						{isToday(date) ? 'bg-primary text-primary-content' : ''}"
				>
					{date.getDate()}
				</span>
				<div class="flex flex-col gap-0.5 mt-0.5 overflow-hidden flex-1">
					{#each dayEvents.slice(0, 3) as event}
						<button
							class="text-xs truncate rounded px-1 py-0.5 text-left
								{event.all_day ? 'bg-primary/20 text-primary' : 'bg-info/20 text-info'}"
							onclick={(e) => { e.stopPropagation(); oneventclick(event); }}
						>
							{event.title}
						</button>
					{/each}
					{#if dayEvents.length > 3}
						<span class="text-xs text-base-content/40">+{dayEvents.length - 3} more</span>
					{/if}
				</div>
			</div>
		{/each}
	</div>
</div>
