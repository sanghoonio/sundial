import type { CalendarItem } from '$lib/types';

export function toLocalISOString(date: string, time?: string): string {
	// Parse date and time components explicitly to avoid browser inconsistencies
	// with Date string parsing (some browsers parse "2025-02-03T00:00:00" as UTC)
	const [year, month, day] = date.split('-').map(Number);
	const [hours, minutes] = time ? time.split(':').map(Number) : [0, 0];
	const d = new Date(year, month - 1, day, hours, minutes, 0);
	const tzOffset = -d.getTimezoneOffset();
	const sign = tzOffset >= 0 ? '+' : '-';
	const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, '0');
	const tzMinutes = String(Math.abs(tzOffset) % 60).padStart(2, '0');
	const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:00`;
	return `${dateStr}T${timeStr}${sign}${tzHours}:${tzMinutes}`;
}

export function formatDateKey(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function isToday(d: Date): boolean {
	const now = new Date();
	return (
		d.getDate() === now.getDate() &&
		d.getMonth() === now.getMonth() &&
		d.getFullYear() === now.getFullYear()
	);
}

export function isSameDay(a: Date, b: Date): boolean {
	return (
		a.getDate() === b.getDate() &&
		a.getMonth() === b.getMonth() &&
		a.getFullYear() === b.getFullYear()
	);
}

export function getWeekDays(date: Date): Date[] {
	const start = new Date(date);
	start.setDate(start.getDate() - start.getDay());
	return Array.from({ length: 7 }, (_, i) => {
		const d = new Date(start);
		d.setDate(d.getDate() + i);
		return d;
	});
}

export function formatCompactTime(iso: string): string {
	const d = new Date(iso);
	let hours = d.getHours();
	const mins = d.getMinutes();
	const ampm = hours >= 12 ? 'p' : 'a';
	hours = hours % 12 || 12;
	return mins > 0 ? `${hours}:${String(mins).padStart(2, '0')}${ampm}` : `${hours}${ampm}`;
}

export function formatHourLabel(hour: number): string {
	if (hour === 0) return '12 AM';
	if (hour < 12) return `${hour} AM`;
	if (hour === 12) return '12 PM';
	return `${hour - 12} PM`;
}

export function getItemDate(item: CalendarItem): string {
	if (item.type === 'event') {
		// Always use Date parsing to correctly handle timezone conversion
		// (string splitting fails when backend returns UTC times)
		return formatDateKey(new Date(item.data.start_time));
	}
	// For tasks, also parse as Date to handle timezone correctly
	return item.data.due_date ? formatDateKey(new Date(item.data.due_date)) : '';
}

export function isAllDay(item: CalendarItem): boolean {
	if (item.type === 'event') return item.data.all_day;
	return true; // Tasks are treated as all-day items
}

export function getStartHour(item: CalendarItem): number {
	if (item.type === 'event' && !item.data.all_day) {
		return new Date(item.data.start_time).getHours();
	}
	return 0;
}

export function getStartMinute(item: CalendarItem): number {
	if (item.type === 'event' && !item.data.all_day) {
		return new Date(item.data.start_time).getMinutes();
	}
	return 0;
}

export function getDurationHours(item: CalendarItem): number {
	if (item.type === 'event' && !item.data.all_day && item.data.end_time) {
		const start = new Date(item.data.start_time).getTime();
		const end = new Date(item.data.end_time).getTime();
		return Math.max((end - start) / (1000 * 60 * 60), 0.5);
	}
	return 1; // Default 1 hour
}

export function itemsForDate(items: CalendarItem[], date: Date): CalendarItem[] {
	const dateStr = formatDateKey(date);
	return items.filter((item) => getItemDate(item) === dateStr);
}

export function chipClasses(item: CalendarItem): string {
	if (item.type === 'task') {
		const isOverdue =
			item.data.status !== 'done' &&
			item.data.due_date &&
			new Date(item.data.due_date) < new Date(new Date().toDateString());
		if (isOverdue) return 'bg-error/20 text-error border-error/30';
		return 'bg-warning/20 text-warning-content border-warning/30';
	}
	if (item.data.all_day) return 'bg-primary/20 text-primary border-primary/30';
	return 'bg-info/20 text-info border-info/30';
}

/** Compute column layout for overlapping timed events */
export function layoutTimedItems(
	items: CalendarItem[]
): { item: CalendarItem; col: number; totalCols: number }[] {
	if (items.length === 0) return [];

	const sorted = [...items].sort((a, b) => {
		const aStart = getStartHour(a) * 60 + getStartMinute(a);
		const bStart = getStartHour(b) * 60 + getStartMinute(b);
		return aStart - bStart;
	});

	const result: { item: CalendarItem; col: number; totalCols: number }[] = [];
	const columns: { end: number }[] = [];

	for (const item of sorted) {
		const startMin = getStartHour(item) * 60 + getStartMinute(item);
		const endMin = startMin + getDurationHours(item) * 60;

		let placed = false;
		for (let c = 0; c < columns.length; c++) {
			if (columns[c].end <= startMin) {
				columns[c].end = endMin;
				result.push({ item, col: c, totalCols: 0 });
				placed = true;
				break;
			}
		}
		if (!placed) {
			columns.push({ end: endMin });
			result.push({ item, col: columns.length - 1, totalCols: 0 });
		}
	}

	// Set totalCols for all items
	const totalCols = columns.length;
	for (const r of result) {
		r.totalCols = totalCols;
	}

	return result;
}
