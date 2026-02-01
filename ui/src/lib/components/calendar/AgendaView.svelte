<script lang="ts">
	import type { CalendarItem } from '$lib/types';
	import { isToday, getItemDate, formatCompactTime, chipClasses } from '$lib/utils/calendar';

	interface Props {
		items: CalendarItem[];
		onitemclick: (item: CalendarItem) => void;
	}

	let { items, onitemclick }: Props = $props();

	interface GroupedDay {
		dateStr: string;
		date: Date;
		items: CalendarItem[];
	}

	let grouped = $derived.by(() => {
		const map = new Map<string, CalendarItem[]>();

		for (const item of items) {
			const dateStr = getItemDate(item);
			if (!dateStr) continue;
			if (!map.has(dateStr)) map.set(dateStr, []);
			map.get(dateStr)!.push(item);
		}

		const days: GroupedDay[] = [];
		for (const [dateStr, dayItems] of map) {
			// Sort: all-day first, then by time
			dayItems.sort((a, b) => {
				const aAllDay = a.type === 'event' ? a.data.all_day : true;
				const bAllDay = b.type === 'event' ? b.data.all_day : true;
				if (aAllDay && !bAllDay) return -1;
				if (!aAllDay && bAllDay) return 1;
				const aTime = a.type === 'event' ? a.data.start_time : a.data.due_date ?? '';
				const bTime = b.type === 'event' ? b.data.start_time : b.data.due_date ?? '';
				return aTime.localeCompare(bTime);
			});
			days.push({ dateStr, date: new Date(dateStr + 'T00:00:00'), items: dayItems });
		}

		days.sort((a, b) => a.dateStr.localeCompare(b.dateStr));
		return days;
	});

	function formatDateHeader(d: Date): string {
		if (isToday(d)) return 'Today';
		const tomorrow = new Date();
		tomorrow.setDate(tomorrow.getDate() + 1);
		if (
			d.getDate() === tomorrow.getDate() &&
			d.getMonth() === tomorrow.getMonth() &&
			d.getFullYear() === tomorrow.getFullYear()
		)
			return 'Tomorrow';
		return d.toLocaleDateString(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}

	function timeLabel(item: CalendarItem): string {
		if (item.type === 'event') {
			if (item.data.all_day) return 'All day';
			let label = formatCompactTime(item.data.start_time);
			if (item.data.end_time) label += ` – ${formatCompactTime(item.data.end_time)}`;
			return label;
		}
		return 'Due';
	}

	function typeBadge(item: CalendarItem): { label: string; classes: string } {
		if (item.type === 'task') {
			return { label: 'Task', classes: 'badge-warning' };
		}
		return { label: 'Event', classes: 'badge-info' };
	}
</script>

<div class="flex flex-col gap-6 overflow-y-auto h-full pt-4 pb-8">
	{#if grouped.length === 0}
		<div class="text-center text-base-content/50 py-12">
			No events or tasks in this period.
		</div>
	{/if}

	{#each grouped as { date, items: dayItems }}
		<div>
			<h3 class="text-sm font-semibold text-base-content/70 border-b border-base-300 pb-1 mb-2 px-4 sticky top-0 bg-base-100 z-10">
				{formatDateHeader(date)}
			</h3>
			<div class="flex flex-col gap-1 px-4">
				{#each dayItems as item}
					{@const badge = typeBadge(item)}
					<button
						class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-base-200 transition-colors text-left w-full"
						onclick={() => onitemclick(item)}
					>
						<div class="w-20 shrink-0 text-xs text-base-content/60">
							{timeLabel(item)}
						</div>
						<div class="flex-1 min-w-0">
							<span class="text-sm font-medium truncate block">
								{#if item.type === 'task'}
									<span class="inline-block w-2.5 h-2.5 rounded-sm border border-current mr-1 align-middle {item.data.status === 'done' ? 'bg-current' : ''} {chipClasses(item).includes('error') ? 'text-error' : 'text-warning'}"></span>
								{/if}
								{item.type === 'event' ? item.data.title : item.data.title}
							</span>
						</div>
						<span class="badge badge-sm {badge.classes}">{badge.label}</span>
					</button>
				{/each}
			</div>
		</div>
	{/each}
</div>
