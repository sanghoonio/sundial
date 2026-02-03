<script lang="ts">
	import type { TaskResponse, DashboardTask } from '$lib/types';
	import { AlertCircle, GripVertical, StickyNote, CalendarDays, Check, X } from 'lucide-svelte';

	interface Props {
		task: TaskResponse | DashboardTask;
		compact?: boolean;
		draggable?: boolean;
		selected?: boolean;
		onclick?: () => void;
		onaccept?: () => void;
		ondismiss?: () => void;
	}

	let { task, compact = false, draggable = false, selected = false, onclick, onaccept, ondismiss }: Props = $props();

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
	let hasLinkedNote = $derived(fullTask?.source_note_id != null);
	let hasLinkedEvent = $derived(fullTask?.calendar_event_id != null);
	let overdue = $derived(isOverdue(task.due_date));
	let hasPriorityIcon = $derived(task.priority === 'urgent' || task.priority === 'high');
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	class="card border border-base-300 {selected ? 'bg-primary/5' : 'bg-base-100'} {onclick ? 'cursor-pointer hover:border-base-content/30' : ''} {isAiSuggested ? 'border-dashed border-primary/40' : ''} transition-colors"
	onclick={onclick}
	onkeydown={(e) => { if (e.key === 'Enter' && onclick) onclick(); }}
	role={onclick ? 'button' : undefined}
	tabindex={onclick ? 0 : undefined}
>
	<div class="card-body {compact ? 'p-3' : 'p-3 gap-1.5'}">
		<div class="flex items-center gap-2">
			{#if draggable}
				<span class="text-base-content/30 shrink-0" data-grab><GripVertical size={14} /></span>
			{/if}
			<span class="font-medium truncate text-sm flex-1 min-w-0">{task.title}</span>
			{#if hasLinkedNote}
				<span class="text-base-content/40 shrink-0" title="Linked note"><StickyNote size={12} /></span>
			{/if}
			{#if hasPriorityIcon}
				<span class="{priorityColors[task.priority]} shrink-0">
					<AlertCircle size={14} />
				</span>
			{/if}
		</div>

		{#if !compact && fullTask?.description}
			<p class="text-xs text-base-content/50 line-clamp-2">{fullTask.description}</p>
		{/if}

		{#if !compact}
			{@const hasMetadata = task.due_date || hasLinkedEvent}
			{#if hasMetadata}
				<div class="flex items-center gap-2 flex-wrap">
					{#if task.due_date}
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
