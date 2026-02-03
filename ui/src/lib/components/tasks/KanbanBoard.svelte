<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import KanbanColumn from './KanbanColumn.svelte';
	import { Plus, Check, X } from 'lucide-svelte';

	interface Props {
		milestones: MilestoneResponse[];
		tasks: TaskResponse[];
		projectId: string;
		selectedTaskId?: string | null;
		ontaskclick?: (task: TaskResponse) => void;
		ondrop?: (taskId: string, milestoneId: string, position: number) => void;
		ontaskcreated?: (task: TaskResponse) => void;
		oncolumnrename?: (milestoneId: string, newName: string) => void;
		oncolumndelete?: (milestoneId: string) => void;
		oncolumncreate?: (name: string) => void;
		oncolumnreorder?: (milestoneId: string, newPosition: number) => void;
	}

	let {
		milestones,
		tasks,
		projectId,
		selectedTaskId = null,
		ontaskclick,
		ondrop,
		ontaskcreated,
		oncolumnrename,
		oncolumndelete,
		oncolumncreate,
		oncolumnreorder
	}: Props = $props();

	let columnDragOverId = $state<string | null>(null);
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
			.filter((t) => t.milestone_id === msId)
			.sort((a, b) => a.position - b.position);
	}

	let unsortedTasks = $derived(
		tasks.filter((t) => !t.milestone_id).sort((a, b) => a.position - b.position)
	);

	let sortedMilestones = $derived(milestones.toSorted((a, b) => a.position - b.position));

	function handleBoardDragOver(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/column-id')) return;
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
			// Use 80% threshold for more responsive feel when dragging left
			const threshold = rect.left + rect.width * 0.8;
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
		const related = e.relatedTarget as Node | null;
		const board = e.currentTarget as HTMLElement;
		if (related && board.contains(related)) return;
		columnDragOverId = null;
	}

	function handleBoardDrop(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/column-id')) return;
		e.preventDefault();
		const draggedId = e.dataTransfer.getData('application/column-id');
		columnDragOverId = null;
		draggingColumnId = null;

		if (!draggedId || !oncolumnreorder) return;

		// Calculate new position (original logic)
		const sorted = sortedMilestones;
		const board = e.currentTarget as HTMLElement;
		const columns = Array.from(board.querySelectorAll('[data-column-id]')) as HTMLElement[];

		let newPos = sorted.length - 1;
		for (let i = 0; i < columns.length; i++) {
			const rect = columns[i].getBoundingClientRect();
			const midX = rect.left + rect.width / 2;
			if (e.clientX < midX) {
				newPos = i;
				break;
			}
		}

		// Adjust if dragging forward
		const oldPos = sorted.findIndex((m) => m.id === draggedId);
		if (oldPos < newPos) newPos--;
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

<div
	class="flex gap-4 overflow-x-auto p-4 h-full snap-x snap-mandatory md:snap-none"
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
			/>
		</div>
		{#if columnDragOverId === ms.id && columnDragSide === 'right'}
			<div
				class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-xl shrink-0"
				style="width: {draggedColumnWidth}px; height: {draggedColumnHeight}px;"
			></div>
		{/if}
	{/each}

	<!-- Add column placeholder -->
	{#if oncolumncreate}
		<div class="snap-start shrink-0">
			{#if addingColumn}
				<div class="flex flex-col bg-base-200/50 border-2 border-dashed border-base-300 rounded-lg p-3 w-[calc(100vw-3rem)] sm:w-auto sm:min-w-72 sm:max-w-72">
					<div class="flex items-center gap-1">
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
					class="flex flex-col items-center justify-center bg-base-200/30 border-2 border-dashed border-base-300 rounded-lg p-3 w-[calc(100vw-3rem)] sm:w-auto sm:min-w-72 sm:max-w-72 h-24 text-base-content/40 hover:text-base-content/60 hover:border-base-content/30 transition-colors cursor-pointer"
					onclick={() => (addingColumn = true)}
				>
					<Plus size={20} />
					<span class="text-xs mt-1">Add column</span>
				</button>
			{/if}
		</div>
	{/if}
</div>
