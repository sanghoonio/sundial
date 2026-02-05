<script lang="ts">
	import type { CalendarItem } from '$lib/types';

	interface Props {
		items: CalendarItem[];
		currentDate: Date;
		ondayclick: (date: Date) => void;
		onitemclick: (item: CalendarItem) => void;
		ondaynumberclick?: (date: Date) => void;
	}

	let { items, currentDate, ondayclick, onitemclick, ondaynumberclick }: Props = $props();

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

	function itemsForDate(date: Date): CalendarItem[] {
		const dateStr = formatDateKey(date);
		return items.filter((item) => {
			if (item.type === 'event') {
				// Always use Date parsing to correctly handle timezone conversion
				return formatDateKey(new Date(item.data.start_time)) === dateStr;
			} else {
				return item.data.due_date
					? formatDateKey(new Date(item.data.due_date)) === dateStr
					: false;
			}
		});
	}

	function formatDateKey(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function isToday(d: Date): boolean {
		const now = new Date();
		return (
			d.getDate() === now.getDate() &&
			d.getMonth() === now.getMonth() &&
			d.getFullYear() === now.getFullYear()
		);
	}

	function formatCompactTime(iso: string): string {
		const d = new Date(iso);
		let hours = d.getHours();
		const mins = d.getMinutes();
		const ampm = hours >= 12 ? 'p' : 'a';
		hours = hours % 12 || 12;
		return mins > 0 ? `${hours}:${String(mins).padStart(2, '0')}${ampm}` : `${hours}${ampm}`;
	}

	function chipLabel(item: CalendarItem): string {
		if (item.type === 'event') {
			if (item.data.all_day) return item.data.title;
			return `${formatCompactTime(item.data.start_time)} ${item.data.title}`;
		}
		return item.data.title;
	}

	function isOverdue(item: CalendarItem): boolean {
		if (item.type !== 'task') return false;
		if (item.data.status === 'done') return false;
		const due = item.data.due_date;
		if (!due) return false;
		return new Date(due) < new Date(new Date().toDateString());
	}

	function chipClasses(item: CalendarItem): string {
		if (item.type === 'task') {
			if (isOverdue(item)) return 'bg-error/20 text-error';
			return 'bg-warning/20 text-warning-content';
		}
		if (item.data.all_day) return 'bg-primary/20 text-primary';
		return 'bg-info/20 text-info';
	}
</script>

<div class="flex flex-col h-full">
	<!-- Weekday headers -->
	<div class="grid grid-cols-7 border-b border-base-300">
		{#each weekdays as day}
			<div class="text-center text-xs font-medium text-base-content/60 py-2">{day}</div>
		{/each}
	</div>

	<!-- Day grid -->
	<div class="grid grid-cols-7 flex-1 auto-rows-fr">
		{#each calendarDays as { date, inMonth }}
			{@const dayItems = itemsForDate(date)}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="border border-base-300/50 p-1 min-h-20 text-left flex flex-col
					{inMonth ? '' : 'bg-base-200/50 text-base-content/30'}
					hover:bg-base-200 transition-colors cursor-pointer"
				onclick={() => ondayclick(date)}
			>
				<button
					class="text-xs font-medium inline-flex items-center justify-center w-6 h-6 rounded-full self-start
						{isToday(date) ? 'bg-primary text-primary-content' : 'hover:bg-base-300'}"
					onclick={(e) => {
						e.stopPropagation();
						if (ondaynumberclick) ondaynumberclick(date);
						else ondayclick(date);
					}}
				>
					{date.getDate()}
				</button>
				<div class="flex flex-col gap-0.5 mt-0.5 overflow-hidden flex-1">
					{#each dayItems.slice(0, 3) as item}
						<button
							class="text-xs truncate rounded px-1 py-0.5 text-left {chipClasses(item)}"
							onclick={(e) => {
								e.stopPropagation();
								onitemclick(item);
							}}
						>
							{#if item.type === 'task'}
								<span class="inline-block w-2 h-2 rounded-sm border border-current mr-0.5 align-middle {item.data.status === 'done' ? 'bg-current' : ''}"></span>
							{/if}
							{chipLabel(item)}
						</button>
					{/each}
					{#if dayItems.length > 3}
						<span class="text-xs text-base-content/40">+{dayItems.length - 3} more</span>
					{/if}
				</div>
			</div>
		{/each}
	</div>
</div>
