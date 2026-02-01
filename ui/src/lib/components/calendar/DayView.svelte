<script lang="ts">
	import type { CalendarItem } from '$lib/types';
	import TimeGrid from './TimeGrid.svelte';
	import {
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
	}

	let { items, currentDate, onitemclick, onslotclick }: Props = $props();

	let columns = $derived([currentDate]);

	let dayItems = $derived(itemsForDate(items, currentDate));
	let allDayItems = $derived(dayItems.filter(isAllDay));
	let timedItems = $derived(dayItems.filter((i) => !isAllDay(i)));

	function itemLabel(item: CalendarItem): string {
		if (item.type === 'event') {
			if (item.data.all_day) return item.data.title;
			return item.data.title;
		}
		return item.data.title;
	}

	function itemTimeLabel(item: CalendarItem): string {
		if (item.type === 'event' && !item.data.all_day) {
			let label = formatCompactTime(item.data.start_time);
			if (item.data.end_time) {
				label += ` – ${formatCompactTime(item.data.end_time)}`;
			}
			return label;
		}
		return '';
	}
</script>

<div class="flex flex-col h-full">
	<TimeGrid
		{columns}
		{onslotclick}
	>
		{#snippet allDayContent({ date })}
			{#each allDayItems as item}
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
		{/snippet}

		{#snippet children({ date })}
			{@const layout = layoutTimedItems(timedItems)}
			{#each layout as { item, col, totalCols }}
				{@const top = (getStartHour(item) + getStartMinute(item) / 60) * 48}
				{@const height = Math.max(getDurationHours(item) * 48, 24)}
				<button
					class="absolute rounded px-2 py-1 text-left overflow-hidden pointer-events-auto border-l-2 {chipClasses(item)}"
					style="top: {top}px; height: {height}px; left: calc({(col / totalCols) * 100}% + 2px); width: calc({(1 / totalCols) * 100}% - 4px);"
					onclick={() => onitemclick(item)}
				>
					<span class="font-medium text-sm truncate block">{itemLabel(item)}</span>
					{#if height >= 40}
						<span class="text-xs opacity-70">{itemTimeLabel(item)}</span>
					{/if}
				</button>
			{/each}
		{/snippet}
	</TimeGrid>
</div>
