<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import KanbanColumn from './KanbanColumn.svelte';
	import TaskCard from './TaskCard.svelte';
	import { Plus, Check, X, CircleCheckBig } from 'lucide-svelte';

	interface Props {
		milestones: MilestoneResponse[];
		tasks: TaskResponse[];
		projectId: string;
		selectedTaskId?: string | null;
		showCompleted?: boolean;
		ontaskclick?: (task: TaskResponse) => void;
		ondrop?: (taskId: string, milestoneId: string | null, position: number) => void;
		ontaskcreated?: (task: TaskResponse) => void;
		oncolumnrename?: (milestoneId: string, newName: string) => void;
		oncolumndelete?: (milestoneId: string) => void;
		oncolumncreate?: (name: string) => void;
		oncolumnreorder?: (milestoneId: string, newPosition: number) => void;
		ontaskdelete?: (taskId: string) => void;
		onstatustoggle?: (taskId: string, newStatus: string) => void;
	}

	let {
		milestones,
		tasks,
		projectId,
		selectedTaskId = null,
		showCompleted = false,
		ontaskclick,
		ondrop,
		ontaskcreated,
		oncolumnrename,
		oncolumndelete,
		oncolumncreate,
		oncolumnreorder,
		ontaskdelete,
		onstatustoggle
	}: Props = $props();

	let columnDragOverId = $state<string | null>(null);
	let boardDragLeaveTimer: ReturnType<typeof setTimeout>;
	let columnDragSide = $state<'left' | 'right'>('left');
	let addingColumn = $state(false);
	let newColumnName = $state('');

	// Dragged task dimensions for placeholder box (shared across all columns)
	let draggedTaskHeight = $state(0);

	// Dragged column tracking for placeholder sizing and hiding original
	let draggingColumnId = $state<string | null>(null);
	let draggedColumnWidth = $state(0);
	let draggedColumnHeight = $state(0);

	function handleTaskDragStart(height: number) {
		draggedTaskHeight = height;
	}

	function handleUnsortedDrop(taskId: string, _milestoneId: string, position: number) {
		ondrop?.(taskId, null, position);
	}

	function handleColumnDragStart(columnId: string, width: number, height: number) {
		draggingColumnId = columnId;
		draggedColumnWidth = width;
		draggedColumnHeight = height;
	}

	function handleColumnDragEnd() {
		draggingColumnId = null;
		columnDragOverId = null;
	}

	function tasksForMilestone(msId: string): TaskResponse[] {
		return tasks
			.filter((t) => t.milestone_id === msId && t.status !== 'done')
			.sort((a, b) => a.position - b.position);
	}

	let unsortedTasks = $derived(
		tasks.filter((t) => !t.milestone_id && t.status !== 'done').sort((a, b) => a.position - b.position)
	);

	let doneTasks = $derived(
		tasks.filter((t) => t.status === 'done').sort((a, b) => {
			const aTime = a.completed_at ?? a.updated_at;
			const bTime = b.completed_at ?? b.updated_at;
			return bTime.localeCompare(aTime);
		})
	);

	let sortedMilestones = $derived(milestones.toSorted((a, b) => a.position - b.position));

	function handleBoardDragOver(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/column-id')) return;
		clearTimeout(boardDragLeaveTimer);
		e.preventDefault();
		e.dataTransfer.dropEffect = 'move';

		// Find which column gap we're closest to (skip the dragged column for visual feedback)
		const board = e.currentTarget as HTMLElement;
		const columns = Array.from(board.querySelectorAll('[data-column-id]')) as HTMLElement[];

		let lastNonDragged: HTMLElement | null = null;
		for (const col of columns) {
			if (col.dataset.columnId === draggingColumnId) continue; // Skip dragged column
			lastNonDragged = col;
			const rect = col.getBoundingClientRect();
			// Use 85% threshold for more responsive feel when dragging left
			const threshold = rect.left + rect.width * 0.85;
			if (e.clientX < threshold) {
				columnDragOverId = col.dataset.columnId!;
				columnDragSide = 'left';
				return;
			}
		}
		// Past all columns — drop at the end
		if (lastNonDragged) {
			columnDragOverId = lastNonDragged.dataset.columnId!;
			columnDragSide = 'right';
		}
	}

	function handleBoardDragLeave(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/column-id')) return;
		clearTimeout(boardDragLeaveTimer);
		boardDragLeaveTimer = setTimeout(() => {
			columnDragOverId = null;
		}, 50);
	}

	function handleBoardDrop(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/column-id')) return;
		e.preventDefault();
		const draggedId = e.dataTransfer.getData('application/column-id');
		clearTimeout(boardDragLeaveTimer);
		columnDragOverId = null;
		draggingColumnId = null;

		if (!draggedId || !oncolumnreorder) return;

		// Calculate new position using same logic as handleBoardDragOver
		const board = e.currentTarget as HTMLElement;
		const columns = Array.from(board.querySelectorAll('[data-column-id]')) as HTMLElement[];

		// Skip the dragged column when calculating position (matches dragover behavior)
		const nonDraggedColumns = columns.filter((col) => col.dataset.columnId !== draggedId);
		let newPos = nonDraggedColumns.length; // default: end position

		for (let i = 0; i < nonDraggedColumns.length; i++) {
			const col = nonDraggedColumns[i];
			const rect = col.getBoundingClientRect();
			// Use 85% threshold to match handleBoardDragOver
			const threshold = rect.left + rect.width * 0.85;
			if (e.clientX < threshold) {
				newPos = i;
				break;
			}
		}

		// Get old position
		const oldPos = sortedMilestones.findIndex((m) => m.id === draggedId);
		if (oldPos === newPos) return;

		oncolumnreorder(draggedId, newPos);
	}

	function handleAddColumn() {
		const name = newColumnName.trim();
		if (!name) return;
		oncolumncreate?.(name);
		newColumnName = '';
		addingColumn = false;
	}

	function handleAddKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleAddColumn();
		} else if (e.key === 'Escape') {
			addingColumn = false;
			newColumnName = '';
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="flex gap-4 overflow-x-auto p-4 scroll-pl-4 h-full snap-x snap-mandatory md:snap-none"
	ondragover={handleBoardDragOver}
	ondragleave={handleBoardDragLeave}
	ondrop={handleBoardDrop}
>
	{#if unsortedTasks.length > 0}
		<div class="snap-start">
			<KanbanColumn
				milestone={{ id: '__unsorted__', name: 'Unsorted', position: -1 }}
				tasks={unsortedTasks}
				{projectId}
				{selectedTaskId}
				{ontaskclick}
				{draggedTaskHeight}
				ontaskdragstart={handleTaskDragStart}
				ondrop={handleUnsortedDrop}
				{ontaskcreated}
				{ontaskdelete}
				{onstatustoggle}
			/>
		</div>
	{/if}

	{#each sortedMilestones as ms (ms.id)}
		{#if columnDragOverId === ms.id && columnDragSide === 'left'}
			<div
				class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-xl shrink-0"
				style="width: {draggedColumnWidth}px; height: {draggedColumnHeight}px;"
			></div>
		{/if}
		<div
			class="snap-start"
			data-column-id={ms.id}
			style={draggingColumnId === ms.id ? 'display: none;' : ''}
		>
			<KanbanColumn
				milestone={ms}
				tasks={tasksForMilestone(ms.id)}
				{projectId}
				{selectedTaskId}
				{ontaskclick}
				{ondrop}
				{ontaskcreated}
				onrename={oncolumnrename}
				ondelete={oncolumndelete}
				{draggedTaskHeight}
				ontaskdragstart={handleTaskDragStart}
				oncolumndragstart={handleColumnDragStart}
				oncolumndragend={handleColumnDragEnd}
				{ontaskdelete}
				{onstatustoggle}
			/>
		</div>
		{#if columnDragOverId === ms.id && columnDragSide === 'right'}
			<div
				class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-xl shrink-0"
				style="width: {draggedColumnWidth}px; height: {draggedColumnHeight}px;"
			></div>
		{/if}
	{/each}

	<!-- Done column (virtual — collects all completed tasks) -->
	{#if showCompleted && doneTasks.length > 0}
		<div class="snap-start">
			<div class="flex flex-col bg-base-200/60 rounded-lg p-3 w-[calc(100vw-6rem)] sm:w-auto sm:min-w-72 sm:max-w-72 h-fit max-h-full" role="group" aria-label="Done column">
				<div class="flex items-center gap-2 mb-3">
					<CircleCheckBig size={14} class="text-success" />
					<span class="font-semibold text-sm text-base-content/60">Completed</span>
					<span class="text-xs text-base-content/40 ml-auto">{doneTasks.length}</span>
				</div>
				<div class="flex flex-col gap-2 flex-1 overflow-auto">
					{#each doneTasks as task (task.id)}
						<div class="opacity-50">
							<TaskCard
								{task}
								selected={task.id === selectedTaskId}
								onclick={() => ontaskclick?.(task)}
								ondelete={() => ontaskdelete?.(task.id)}
								{onstatustoggle}
							/>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<!-- Add column placeholder -->
	{#if oncolumncreate}
		<div class="snap-start shrink-0">
			{#if addingColumn}
				<div class="flex flex-col bg-base-200/50 border-2 border-dashed border-base-300 rounded-lg p-3 w-[calc(100vw-6rem)] sm:w-auto sm:min-w-72 sm:max-w-72">
					<div class="flex items-center gap-1">
						<!-- svelte-ignore a11y_autofocus -->
					<input
							type="text"
							class="input input-bordered input-sm flex-1"
							placeholder="Column name..."
							bind:value={newColumnName}
							onkeydown={handleAddKeydown}
							autofocus
						/>
						<button
							class="btn btn-primary btn-sm btn-square"
							onclick={handleAddColumn}
							disabled={!newColumnName.trim()}
						>
							<Check size={14} />
						</button>
						<button
							class="btn btn-ghost btn-sm btn-square"
							onclick={() => { addingColumn = false; newColumnName = ''; }}
						>
							<X size={14} />
						</button>
					</div>
				</div>
			{:else}
				<button
					class="flex flex-col items-center justify-center bg-base-200/30 border-2 border-dashed border-base-300 rounded-lg p-3 w-[calc(100vw-6rem)] sm:w-auto sm:min-w-72 sm:max-w-72 h-24 text-base-content/40 hover:text-base-content/60 hover:border-base-content/30 transition-colors cursor-pointer"
					onclick={() => (addingColumn = true)}
				>
					<Plus size={20} />
					<span class="text-xs mt-1">Add column</span>
				</button>
			{/if}
		</div>
	{/if}
</div>
