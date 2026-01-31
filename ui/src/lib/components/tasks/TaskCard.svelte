<script lang="ts">
	import type { TaskResponse, DashboardTask } from '$lib/types';
	import { CheckSquare, AlertCircle, GripVertical } from 'lucide-svelte';

	interface Props {
		task: TaskResponse | DashboardTask;
		compact?: boolean;
		draggable?: boolean;
		onclick?: () => void;
	}

	let { task, compact = false, draggable = false, onclick }: Props = $props();

	const priorityColors: Record<string, string> = {
		urgent: 'text-error',
		high: 'text-warning',
		medium: 'text-info',
		low: 'text-base-content/40'
	};

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	let hasChecklist = $derived('checklist' in task && (task as TaskResponse).checklist?.length > 0);
	let checklistDone = $derived(
		hasChecklist
			? (task as TaskResponse).checklist.filter((c) => c.is_checked).length
			: 0
	);
	let checklistTotal = $derived(
		hasChecklist ? (task as TaskResponse).checklist.length : 0
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	class="card bg-base-100 border border-base-300 {draggable ? 'cursor-grab active:cursor-grabbing' : ''} {onclick ? 'cursor-pointer hover:shadow-md' : ''} transition-shadow"
	{draggable}
	onclick={onclick}
	onkeydown={(e) => { if (e.key === 'Enter' && onclick) onclick(); }}
	role={onclick ? 'button' : undefined}
	tabindex={onclick ? 0 : undefined}
>
	<div class="card-body {compact ? 'p-3' : 'p-4'}">
		<div class="flex items-start gap-2">
			{#if draggable}
				<span class="text-base-content/30 mt-0.5"><GripVertical size={16} /></span>
			{/if}
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2">
					<span class={priorityColors[task.priority] ?? ''}>
						{#if task.priority === 'urgent'}
							<AlertCircle size={16} />
						{:else}
							<CheckSquare size={16} />
						{/if}
					</span>
					<span class="font-medium truncate text-sm">{task.title}</span>
				</div>
				{#if !compact && task.due_date}
					<p class="text-xs text-base-content/50 mt-1">
						Due {formatDate(task.due_date)}
					</p>
				{/if}
				{#if hasChecklist && !compact}
					<p class="text-xs text-base-content/50 mt-1">
						{checklistDone}/{checklistTotal} items
					</p>
				{/if}
			</div>
		</div>
	</div>
</div>
