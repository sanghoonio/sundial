<script lang="ts">
	import type { CalendarItem } from '$lib/types';
	import TimeGrid from './TimeGrid.svelte';
	import {
		getWeekDays,
		isToday,
		itemsForDate,
		isAllDay,
		getStartHour,
		getStartMinute,
		getDurationHours,
		chipClasses,
		formatCompactTime,
		layoutTimedItems
	} from '$lib/utils/calendar';

	interface Props {
		items: CalendarItem[];
		currentDate: Date;
		onitemclick: (item: CalendarItem) => void;
		onslotclick?: (date: Date, hour: number) => void;
		ondaynumberclick?: (date: Date) => void;
	}

	let { items, currentDate, onitemclick, onslotclick, ondaynumberclick }: Props = $props();

	let weekDays = $derived(getWeekDays(currentDate));

	function allDayItemsFor(date: Date): CalendarItem[] {
		return itemsForDate(items, date).filter(isAllDay);
	}

	function timedItemsFor(date: Date): CalendarItem[] {
		return itemsForDate(items, date).filter((i) => !isAllDay(i));
	}

	function itemLabel(item: CalendarItem): string {
		if (item.type === 'event') {
			if (item.data.all_day) return item.data.title;
			return `${formatCompactTime(item.data.start_time)} ${item.data.title}`;
		}
		return item.data.title;
	}
</script>

<div class="flex flex-col h-full">
	<!-- Day headers -->
	<div class="flex border-b border-base-300">
		<div class="w-16 shrink-0"></div>
		<div class="grid flex-1" style="grid-template-columns: repeat(7, 1fr)">
			{#each weekDays as day}
				<div class="text-center py-2 border-l border-base-300/50">
					<div class="text-xs text-base-content/50">
						{day.toLocaleDateString(undefined, { weekday: 'short' })}
					</div>
					<button
						class="text-lg font-semibold leading-tight inline-flex items-center justify-center w-8 h-8 rounded-full
							{isToday(day) ? 'bg-primary text-primary-content' : 'hover:bg-base-300'}"
						onclick={() => ondaynumberclick?.(day)}
					>
						{day.getDate()}
					</button>
				</div>
			{/each}
		</div>
	</div>

	<!-- Time grid -->
	<TimeGrid
		columns={weekDays}
		{onslotclick}
	>
		{#snippet allDayContent({ date })}
			{@const adItems = allDayItemsFor(date)}
			{#each adItems.slice(0, 2) as item}
				<button
					class="text-xs truncate rounded px-1 py-0.5 block w-full text-left mb-0.5 {chipClasses(item)}"
					onclick={() => onitemclick(item)}
				>
					{#if item.type === 'task'}
						<span class="inline-block w-2 h-2 rounded-sm border border-current mr-0.5 align-middle {item.data.status === 'done' ? 'bg-current' : ''}"></span>
					{/if}
					{item.data.title}
				</button>
			{/each}
			{#if adItems.length > 2}
				<span class="text-xs text-base-content/40">+{adItems.length - 2}</span>
			{/if}
		{/snippet}

		{#snippet children({ date })}
			{@const timed = timedItemsFor(date)}
			{@const layout = layoutTimedItems(timed)}
			{#each layout as { item, col, totalCols }}
				{@const top = (getStartHour(item) + getStartMinute(item) / 60) * 48}
				{@const height = Math.max(getDurationHours(item) * 48, 20)}
				<button
					class="absolute rounded px-1 py-0.5 text-xs text-left overflow-hidden pointer-events-auto border-l-2 {chipClasses(item)}"
					style="top: {top}px; height: {height}px; left: {(col / totalCols) * 100}%; width: {(1 / totalCols) * 100}%;"
					onclick={() => onitemclick(item)}
				>
					<span class="font-medium truncate block">{itemLabel(item)}</span>
				</button>
			{/each}
		{/snippet}
	</TimeGrid>
</div>
