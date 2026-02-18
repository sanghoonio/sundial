<script lang="ts">
	import { base } from '$app/paths';
	import { api, fetchAllTasks } from '$lib/services/api';
	import type {
		ProjectResponse,
		TaskResponse,
		NoteListItem,
		NoteList
	} from '$lib/types';
	import ProjectIcon from '$lib/components/ui/ProjectIcon.svelte';
	import { Circle, CircleCheckBig, FileText } from 'lucide-svelte';

	interface Props {
		projects: ProjectResponse[];
	}

	let { projects }: Props = $props();

	let allTasks = $state<TaskResponse[]>([]);
	let allNotes = $state<NoteListItem[]>([]);
	let loading = $state(true);
	let fetched = $state(false);

	// Popover state — single fixed popover
	let openPopoverKey = $state<string | null>(null);
	let popoverPos = $state({ x: 0, y: 0 });
	let popoverBucket = $state<DayBucket | null>(null);

	$effect(() => {
		if (fetched) return;
		fetched = true;
		loadData();
	});

	async function loadData() {
		loading = true;
		try {
			const [taskRes, noteRes] = await Promise.all([
				fetchAllTasks('', true),
				api.get<NoteList>('/api/notes?limit=200')
			]);
			allTasks = taskRes.tasks;
			allNotes = noteRes.notes;
		} catch (e) {
			console.error('Failed to load timeline data', e);
		} finally {
			loading = false;
		}
	}

	function dayKey(iso: string): string {
		return new Date(iso).toISOString().slice(0, 10);
	}

	interface DayBucket {
		dateKey: string;
		tasks: TaskResponse[];
		notes: NoteListItem[];
		count: number;
	}

	let bucketsByProject = $derived.by(() => {
		const map = new Map<string, Map<string, DayBucket>>();

		for (const task of allTasks) {
			const dk = dayKey(task.due_date ?? task.created_at);
			if (!map.has(task.project_id)) map.set(task.project_id, new Map());
			const proj = map.get(task.project_id)!;
			if (!proj.has(dk)) proj.set(dk, { dateKey: dk, tasks: [], notes: [], count: 0 });
			const bucket = proj.get(dk)!;
			bucket.tasks.push(task);
			bucket.count++;
		}

		for (const note of allNotes) {
			if (!note.project_id) continue;
			const dk = dayKey(note.updated_at);
			if (!map.has(note.project_id)) map.set(note.project_id, new Map());
			const proj = map.get(note.project_id)!;
			if (!proj.has(dk)) proj.set(dk, { dateKey: dk, tasks: [], notes: [], count: 0 });
			const bucket = proj.get(dk)!;
			bucket.notes.push(note);
			bucket.count++;
		}

		const result = new Map<string, DayBucket[]>();
		for (const [pid, dayMap] of map) {
			result.set(pid, Array.from(dayMap.values()).sort((a, b) => a.dateKey.localeCompare(b.dateKey)));
		}
		return result;
	});

	let timeRange = $derived.by(() => {
		const now = new Date();
		let min = now;
		let max = now;

		for (const task of allTasks) {
			const d = new Date(task.due_date ?? task.created_at);
			if (d < min) min = d;
			if (d > max) max = d;
		}
		for (const note of allNotes) {
			const d = new Date(note.updated_at);
			if (d < min) min = d;
			if (d > max) max = d;
		}

		if (max < now) max = now;

		const padMin = new Date(min.getTime() - 7 * 86400000);
		const padMax = new Date(max.getTime() + 7 * 86400000);

		const range = padMax.getTime() - padMin.getTime();
		if (range < 30 * 86400000) {
			const center = padMin.getTime() + range / 2;
			return { min: new Date(center - 15 * 86400000), max: new Date(center + 15 * 86400000) };
		}

		return { min: padMin, max: padMax };
	});

	let monthTicks = $derived.by(() => {
		const ticks: { label: string; pct: number }[] = [];
		const { min, max } = timeRange;
		const totalMs = max.getTime() - min.getTime();
		if (totalMs <= 0) return ticks;

		const spansYears = min.getFullYear() !== max.getFullYear();
		const current = new Date(min.getFullYear(), min.getMonth(), 1);
		let isFirst = true;
		while (current <= max) {
			let pct = ((current.getTime() - min.getTime()) / totalMs) * 100;
			// Clamp first tick to left edge so there's always a starting label
			if (isFirst && pct < 0) pct = 0;
			isFirst = false;
			if (pct >= 0 && pct <= 100) {
				const isJan = current.getMonth() === 0;
				const label = spansYears && isJan
					? current.toLocaleDateString([], { month: 'short', year: 'numeric' })
					: current.toLocaleDateString([], { month: 'short' });
				ticks.push({ label, pct });
			}
			current.setMonth(current.getMonth() + 1);
		}
		return ticks;
	});

	let todayPct = $derived.by(() => {
		const now = new Date();
		const { min, max } = timeRange;
		const totalMs = max.getTime() - min.getTime();
		if (totalMs <= 0) return 50;
		return ((now.getTime() - min.getTime()) / totalMs) * 100;
	});

	function dateKeyToPct(dk: string): number {
		const d = new Date(dk + 'T12:00:00');
		const { min, max } = timeRange;
		const totalMs = max.getTime() - min.getTime();
		if (totalMs <= 0) return 50;
		return ((d.getTime() - min.getTime()) / totalMs) * 100;
	}

	function dotSize(count: number): number {
		if (count <= 1) return 8;
		if (count <= 3) return 11;
		if (count <= 6) return 14;
		return 17;
	}

	function formatDateLabel(dk: string): string {
		return new Date(dk + 'T12:00:00').toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	function togglePopover(key: string, bucket: DayBucket, e: MouseEvent) {
		e.stopPropagation();
		if (openPopoverKey === key) {
			openPopoverKey = null;
			return;
		}
		const el = e.currentTarget as HTMLElement;
		const rect = el.getBoundingClientRect();
		popoverPos = { x: rect.left + rect.width / 2, y: rect.bottom + 8 };
		popoverBucket = bucket;
		openPopoverKey = key;
	}

	function closePopover() {
		openPopoverKey = null;
	}

	let hasAnyItems = $derived(allTasks.length > 0 || allNotes.length > 0);
</script>

<svelte:window onclick={closePopover} />
<svelte:document onscrollcapture={closePopover} />

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if !hasAnyItems}
	<div class="text-center py-20">
		<p class="text-base-content/40">No tasks or notes to display</p>
	</div>
{:else}
	<div class="flex flex-col gap-0 pt-1">
		<!-- Month axis (top) -->
		<div class="flex border-b border-base-300">
			<div class="w-40 md:w-56 shrink-0 pl-4"></div>
			<div class="flex-1 relative h-6">
				{#each monthTicks as tick}
					<span
						class="absolute text-[10px] text-base-content/40 bottom-1 -translate-x-1/2"
						style:left="{tick.pct}%"
					>
						{tick.label}
					</span>
				{/each}
				<!-- Today pill -->
				<span
					class="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-40 text-[9px] font-medium text-white bg-error rounded-full px-1.5 py-px leading-tight"
					style:left="{todayPct}%"
				>Today</span>
			</div>
		</div>

		<!-- Project rows wrapper — relative so today overlay is scoped here -->
		<div class="relative">
			<!-- Today line overlay -->
			<div class="absolute inset-0 pointer-events-none flex z-30">
				<div class="w-40 md:w-56 shrink-0"></div>
				<div class="flex-1 relative">
					<div class="absolute -top-3 bottom-0 w-[1.25px] bg-error" style:left="{todayPct}%"></div>
				</div>
			</div>

		{#each projects as project (project.id)}
			{@const buckets = bucketsByProject.get(project.id) ?? []}
			<div class="flex items-center group hover:bg-base-200/30 transition-colors border-b border-base-300">
				<!-- Project label -->
				<a
					href="{base}/tasks/{project.id}"
					class="w-40 md:w-56 shrink-0 flex items-center gap-2 pl-4 py-2.5 truncate hover:underline"
					title={project.name}
				>
					<span class="shrink-0" style:color={project.color || '#6b7280'}>
						<ProjectIcon name={project.icon || 'folder-kanban'} size={16} />
					</span>
					<span class="text-sm font-medium truncate hidden md:inline">{project.name}</span>
				</a>

				<!-- Timeline area -->
				<div class="flex-1 relative h-10 overflow-visible">
					<!-- Month gridlines -->
					{#each monthTicks as tick}
						<div
							class="absolute top-0 bottom-0 w-px bg-base-300/50"
							style:left="{tick.pct}%"
						></div>
					{/each}

					<!-- Day-aggregated dots -->
					{#each buckets as bucket}
						{@const pct = dateKeyToPct(bucket.dateKey)}
						{@const size = dotSize(bucket.count)}
						{@const popKey = `${project.id}:${bucket.dateKey}`}
						{@const doneTasks = bucket.tasks.filter(t => t.status === 'done').length}
						{@const allDone = bucket.tasks.length > 0 && doneTasks === bucket.tasks.length && bucket.notes.length === 0}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							class="absolute -translate-x-1/2 -translate-y-1/2 top-1/2 z-10 cursor-pointer"
							style:left="{pct}%"
							onclick={(e) => togglePopover(popKey, bucket, e)}
							onkeydown={(e) => e.key === 'Enter' && togglePopover(popKey, bucket, e as unknown as MouseEvent)}
							role="button"
							tabindex="0"
						>
							<div
								class="rounded-full transition-transform hover:scale-150 {openPopoverKey === popKey ? 'scale-150' : ''}"
								style:width="{size}px"
								style:height="{size}px"
								style:background-color={project.color || '#6b7280'}
								style:opacity={allDone ? '0.35' : '0.85'}
							></div>
						</div>
					{/each}
				</div>
			</div>
		{/each}
		</div>

		<!-- Legend -->
		<div class="flex items-center gap-4 px-4 pt-3 pb-4 text-[10px] text-base-content/40">
			<span class="flex items-center gap-1.5">
				<span class="inline-block w-2 h-2 rounded-full bg-base-content/30"></span>
				Fewer items
			</span>
			<span class="flex items-center gap-1.5">
				<span class="inline-block w-3 h-3 rounded-full bg-base-content/60"></span>
				More items
			</span>
			<span class="text-base-content/30">Click a dot to see details</span>
		</div>
	</div>
{/if}

<!-- Fixed popover (rendered outside overflow containers) -->
{#if openPopoverKey && popoverBucket}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<div
		class="fixed z-[100] bg-base-100 border border-base-300 rounded-lg shadow-lg p-2 min-w-48 max-w-64 -translate-x-1/2"
		style:left="{popoverPos.x}px"
		style:top="{popoverPos.y}px"
		onclick={(e) => e.stopPropagation()}
	>
		<p class="text-[10px] text-base-content/40 px-1 mb-1">{formatDateLabel(popoverBucket.dateKey)}</p>
		<div class="flex flex-col">
			{#each popoverBucket.tasks as task}
				<a
					href="{base}/tasks/{task.project_id}?task={task.id}"
					class="flex items-center gap-1.5 px-1 py-1 rounded text-xs hover:bg-base-200 transition-colors"
				>
					{#if task.status === 'done'}
						<CircleCheckBig size={12} class="shrink-0 text-success" />
					{:else}
						<Circle size={12} class="shrink-0 text-base-content/40" />
					{/if}
					<span class="truncate">{task.title}</span>
				</a>
			{/each}
			{#each popoverBucket.notes as note}
				<a
					href="{base}/notes/{note.id}"
					class="flex items-center gap-1.5 px-1 py-1 rounded text-xs hover:bg-base-200 transition-colors"
				>
					<FileText size={12} class="shrink-0 text-base-content/40" />
					<span class="truncate">{note.title}</span>
				</a>
			{/each}
		</div>
	</div>
{/if}
