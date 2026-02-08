<script lang="ts">
	import type { TaskResponse, DashboardTask, MilestoneResponse } from '$lib/types';
	import { AlertCircle, GripVertical, StickyNote, CalendarDays, Check, X, Trash2, MoreVertical } from 'lucide-svelte';

	interface Props {
		task: TaskResponse | DashboardTask;
		compact?: boolean;
		draggable?: boolean;
		selected?: boolean;
		milestones?: MilestoneResponse[];
		onclick?: () => void;
		onaccept?: () => void;
		ondismiss?: () => void;
		ondelete?: () => void;
		onmove?: (taskId: string, milestoneId: string | null) => void;
		onstatustoggle?: (taskId: string, newStatus: string) => void;
	}

	let { task, compact = false, draggable = false, selected = false, milestones = [], onclick, onaccept, ondismiss, ondelete, onmove, onstatustoggle }: Props = $props();

	// Get current milestone ID for filtering
	let currentMilestoneId = $derived('milestone_id' in task ? (task as TaskResponse).milestone_id : null);

	// Swipe-to-delete state
	let swipeRevealed = $state(false);
	let swipeOffset = $state(0);
	let isSettling = $state(false);
	let hideTimeout: ReturnType<typeof setTimeout>;
	let settleTimeout: ReturnType<typeof setTimeout>;
	let containerEl: HTMLDivElement;

	// Touch swipe state
	let touchStartX = 0;
	let touchStartY = 0;
	let isTouchSwiping = false;

	const MAX_OFFSET = 48;

	$effect(() => {
		if (!containerEl) return;
		containerEl.addEventListener('wheel', handleWheel, { passive: false });
		return () => containerEl.removeEventListener('wheel', handleWheel);
	});

	function handleWheel(e: WheelEvent) {
		if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) {
			return;
		}

		e.preventDefault();
		isSettling = false;

		swipeOffset = Math.max(-MAX_OFFSET, Math.min(0, swipeOffset - e.deltaX));

		clearTimeout(settleTimeout);
		settleTimeout = setTimeout(() => {
			isSettling = true;
			if (swipeOffset < -MAX_OFFSET / 2) {
				swipeRevealed = true;
				swipeOffset = -MAX_OFFSET;
				resetHideTimer();
			} else {
				swipeRevealed = false;
				swipeOffset = 0;
				clearTimeout(hideTimeout);
			}
		}, 100);
	}

	function resetHideTimer() {
		clearTimeout(hideTimeout);
		hideTimeout = setTimeout(() => {
			isSettling = true;
			swipeRevealed = false;
			swipeOffset = 0;
		}, 10000);
	}

	function handleTouchStart(e: TouchEvent) {
		const touch = e.touches[0];
		touchStartX = touch.clientX;
		touchStartY = touch.clientY;
		isTouchSwiping = false;
	}

	function handleTouchMove(e: TouchEvent) {
		const touch = e.touches[0];
		const deltaX = touch.clientX - touchStartX;
		const deltaY = touch.clientY - touchStartY;

		// Only track horizontal swipes
		if (!isTouchSwiping && Math.abs(deltaX) > 10 && Math.abs(deltaX) > Math.abs(deltaY)) {
			isTouchSwiping = true;
		}

		if (isTouchSwiping) {
			e.preventDefault();
			isSettling = false;
			swipeOffset = Math.max(-MAX_OFFSET, Math.min(0, deltaX));
		}
	}

	function handleTouchEnd() {
		if (!isTouchSwiping) return;
		isSettling = true;
		if (swipeOffset < -MAX_OFFSET / 2) {
			swipeRevealed = true;
			swipeOffset = -MAX_OFFSET;
			resetHideTimer();
		} else {
			swipeRevealed = false;
			swipeOffset = 0;
		}
		isTouchSwiping = false;
	}

	function handleDelete(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		swipeRevealed = false;
		swipeOffset = 0;
		clearTimeout(hideTimeout);
		ondelete?.();
	}

	const priorityColors: Record<string, string> = {
		urgent: 'text-error',
		high: 'text-warning',
		medium: 'text-base-content/40',
		low: 'text-base-content/30'
	};

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	function isOverdue(iso: string | null): boolean {
		if (!iso) return false;
		const due = new Date(iso);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		due.setHours(0, 0, 0, 0);
		return due < today;
	}

	let fullTask = $derived('checklist' in task ? (task as TaskResponse) : null);
	let hasChecklist = $derived(fullTask && fullTask.checklist?.length > 0);
	let checklistDone = $derived(
		hasChecklist ? fullTask!.checklist.filter((c) => c.is_checked).length : 0
	);
	let checklistTotal = $derived(hasChecklist ? fullTask!.checklist.length : 0);
	let checklistPct = $derived(checklistTotal > 0 ? Math.round((checklistDone / checklistTotal) * 100) : 0);
	let isAiSuggested = $derived(fullTask?.ai_suggested ?? false);
	let hasLinkedNote = $derived((fullTask?.note_ids?.length ?? 0) > 0);
	let hasLinkedEvent = $derived(fullTask?.calendar_event_id != null);
	let isDone = $derived(task.status === 'done');
	let overdue = $derived(task.status !== 'done' && isOverdue(task.due_date));
	let hasPriorityIcon = $derived(task.priority === 'urgent' || task.priority === 'high');
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="relative overflow-hidden"
	bind:this={containerEl}
	style="overscroll-behavior-x: contain; touch-action: pan-y;"
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div
		class="rounded-lg {selected ? 'bg-primary/5 hover:bg-primary/10' : 'bg-base-100'} {onclick && !selected ? 'hover:bg-base-100/80' : ''} {onclick ? 'cursor-pointer' : ''} {isAiSuggested ? 'border border-dashed border-primary/40' : ''} transition-colors"
		onclick={onclick}
		onkeydown={(e) => { if (e.key === 'Enter' && onclick) onclick(); }}
		role={onclick ? 'button' : undefined}
		tabindex={onclick ? 0 : undefined}
	>
		<div class="{compact ? 'p-3' : 'p-3 flex flex-col gap-1.5'}">
			<div class="flex items-center gap-2">
				{#if draggable}
					<span class="text-base-content/30 shrink-0 hidden md:block" data-grab><GripVertical size={14} /></span>
				{/if}
					<!-- Checkmark toggle (hidden — uncomment to re-enable)
				{#if onstatustoggle}
					<button
						class="w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-colors {isDone ? 'bg-success border-success' : 'border-base-content/30 hover:border-primary'}"
						onclick={(e) => { e.stopPropagation(); onstatustoggle(task.id, isDone ? 'in_progress' : 'done'); }}
						title={isDone ? 'Mark incomplete' : 'Mark complete'}
					>
						{#if isDone}
							<Check size={12} class="text-success-content" />
						{/if}
					</button>
				{/if}
				-->
				<span class="font-medium truncate text-sm flex-1 min-w-0 {isDone ? 'line-through text-base-content/40' : ''}">{task.title}</span>
				{#if hasLinkedNote}
					<span class="text-base-content/40 shrink-0" title="Linked note"><StickyNote size={12} /></span>
				{/if}
				{#if hasPriorityIcon}
					<span class="{priorityColors[task.priority]} shrink-0">
						<AlertCircle size={14} />
					</span>
				{/if}
				<!-- Mobile move menu -->
				{#if onmove && milestones.length > 0}
					<div class="dropdown dropdown-end md:hidden">
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<button tabindex="0" class="btn btn-ghost btn-xs btn-square" onclick={(e) => e.stopPropagation()}>
							<MoreVertical size={14} />
						</button>
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-40 p-1">
							<li class="menu-title text-xs">Move to</li>
							{#each milestones.filter(ms => ms.id !== currentMilestoneId) as ms}
								<li><button onclick={(e) => { e.stopPropagation(); onmove(task.id, ms.id); }}>{ms.name}</button></li>
							{/each}
							{#if currentMilestoneId}
								<li><button onclick={(e) => { e.stopPropagation(); onmove(task.id, null); }}>No milestone</button></li>
							{/if}
						</ul>
					</div>
				{/if}
			</div>


			{#if !compact}
				{@const hasMetadata = (task.due_date && !isDone) || hasLinkedEvent}
				{#if hasMetadata}
					<div class="flex items-center gap-2 flex-wrap">
						{#if task.due_date && !isDone}
							<span class="badge badge-xs {overdue ? 'badge-error' : 'badge-ghost'}">
								{overdue ? 'Overdue' : 'Due'} {formatDate(task.due_date)}
							</span>
						{/if}
						{#if hasLinkedEvent}
							<span class="text-base-content/40" title="Calendar event"><CalendarDays size={12} /></span>
						{/if}
					</div>
				{/if}
			{/if}

			<!-- Checklist progress (hidden — uncomment to re-enable)
			{#if hasChecklist && !compact}
				<div class="flex items-center gap-2">
					<div class="flex-1 h-1.5 bg-base-300 rounded-full overflow-hidden">
						<div
							class="h-full rounded-full transition-all {checklistPct === 100 ? 'bg-success' : 'bg-primary'}"
							style:width="{checklistPct}%"
						></div>
					</div>
					<span class="text-xs text-base-content/50 tabular-nums">{checklistDone}/{checklistTotal}</span>
				</div>
			{/if}
			-->

			{#if isAiSuggested && (onaccept || ondismiss)}
				<div class="flex items-center gap-1.5 pt-1.5 border-t border-base-200">
					<span class="text-xs text-primary/70 flex-1">AI suggested</span>
					{#if onaccept}
						<button
							class="btn btn-ghost btn-xs text-success"
							onclick={(e) => { e.stopPropagation(); onaccept!(); }}
							title="Accept"
						>
							<Check size={14} />
						</button>
					{/if}
					{#if ondismiss}
						<button
							class="btn btn-ghost btn-xs text-error"
							onclick={(e) => { e.stopPropagation(); ondismiss!(); }}
							title="Dismiss"
						>
							<X size={14} />
						</button>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Trash button - slides in from the right -->
	<button
		class="absolute top-0 bottom-0 right-0 w-12 bg-error flex items-center justify-center rounded-r-lg {isSettling ? 'transition-transform duration-150' : ''}"
		style:transform="translateX({MAX_OFFSET + swipeOffset}px)"
		onclick={handleDelete}
		title="Delete task"
	>
		<Trash2 size={18} class="text-white" />
	</button>
</div>
