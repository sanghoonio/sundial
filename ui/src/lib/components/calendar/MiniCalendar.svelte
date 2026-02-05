<script lang="ts">
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { isToday, isSameDay, formatDateKey } from '$lib/utils/calendar';

	interface Props {
		currentDate: Date;
		itemDates?: Set<string>;
		ondateclick: (date: Date) => void;
	}

	let { currentDate, itemDates = new Set(), ondateclick }: Props = $props();

	// svelte-ignore state_referenced_locally
	let displayMonth = $state(new Date(currentDate.getFullYear(), currentDate.getMonth(), 1));

	// Sync display month when currentDate changes
	$effect(() => {
		displayMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
	});

	const weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

	let calendarDays = $derived.by(() => {
		const year = displayMonth.getFullYear();
		const month = displayMonth.getMonth();
		const firstDay = new Date(year, month, 1);
		const lastDay = new Date(year, month + 1, 0);
		const startPad = firstDay.getDay();
		const totalDays = lastDay.getDate();

		const days: { date: Date; inMonth: boolean }[] = [];

		for (let i = startPad - 1; i >= 0; i--) {
			days.push({ date: new Date(year, month, -i), inMonth: false });
		}
		for (let i = 1; i <= totalDays; i++) {
			days.push({ date: new Date(year, month, i), inMonth: true });
		}
		const remaining = 7 - (days.length % 7);
		if (remaining < 7) {
			for (let i = 1; i <= remaining; i++) {
				days.push({ date: new Date(year, month + 1, i), inMonth: false });
			}
		}

		return days;
	});

	let monthLabel = $derived(
		displayMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
	);

	function prevMonth() {
		displayMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() - 1, 1);
	}

	function nextMonth() {
		displayMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 1);
	}

	function hasItems(date: Date): boolean {
		return itemDates.has(formatDateKey(date));
	}
</script>

<div class="p-3">
	<!-- Header -->
	<div class="flex items-center justify-between mb-2">
		<button class="btn btn-ghost btn-xs btn-square" onclick={prevMonth}>
			<ChevronLeft size={14} />
		</button>
		<span class="text-sm font-medium">{monthLabel}</span>
		<button class="btn btn-ghost btn-xs btn-square" onclick={nextMonth}>
			<ChevronRight size={14} />
		</button>
	</div>

	<!-- Weekday headers -->
	<div class="grid grid-cols-7 mb-1">
		{#each weekdays as day}
			<div class="text-center text-xs text-base-content/40 py-0.5">{day}</div>
		{/each}
	</div>

	<!-- Day grid -->
	<div class="grid grid-cols-7">
		{#each calendarDays as { date, inMonth }}
			<button
				class="relative flex items-center justify-center text-xs w-7 h-7 rounded-full transition-colors
					{!inMonth ? 'text-base-content/20' : ''}
					{isToday(date) ? 'bg-primary text-primary-content font-bold' : ''}
					{isSameDay(date, currentDate) && !isToday(date) ? 'ring-1 ring-primary' : ''}
					{inMonth && !isToday(date) ? 'hover:bg-base-200' : ''}"
				onclick={() => ondateclick(date)}
			>
				{date.getDate()}
				{#if hasItems(date) && !isToday(date)}
					<span class="absolute bottom-0.5 w-1 h-1 rounded-full bg-primary"></span>
				{/if}
			</button>
		{/each}
	</div>
</div>
