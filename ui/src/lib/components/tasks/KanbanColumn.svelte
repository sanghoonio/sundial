<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import TaskCard from './TaskCard.svelte';
	import TaskQuickAdd from './TaskQuickAdd.svelte';
	import { Inbox, Trash2, GripVertical, Lock } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	interface Props {
		milestone: MilestoneResponse;
		tasks: TaskResponse[];
		projectId: string;
		selectedTaskId?: string | null;
		ontaskclick?: (task: TaskResponse) => void;
		ondrop?: (taskId: string, milestoneId: string, position: number) => void;
		ontaskcreated?: (task: TaskResponse) => void;
		onrename?: (milestoneId: string, newName: string) => void;
		ondelete?: (milestoneId: string) => void;
		oncolumndragstart?: (milestoneId: string, width: number, height: number) => void;
		oncolumndragend?: () => void;
		ontaskdragstart?: (height: number) => void;
		ontaskdelete?: (taskId: string) => void;
		draggedTaskHeight?: number;
	}

	let { milestone, tasks, projectId, selectedTaskId = null, ontaskclick, ondrop, ontaskcreated, onrename, ondelete, oncolumndragstart, oncolumndragend, ontaskdragstart, ontaskdelete, draggedTaskHeight = 0 }: Props = $props();

	let dragOver = $state(false);
	let dropIndex = $state<number | null>(null);
	let dragLeaveTimer: ReturnType<typeof setTimeout>;
	let draggingTaskId = $state<string | null>(null);
	// svelte-ignore state_referenced_locally
	let editingName = $state(milestone.name);

	// Keep editingName in sync when milestone prop changes
	$effect(() => {
		editingName = milestone.name;
	});

	function commitRename() {
		const trimmed = editingName.trim();
		if (trimmed && trimmed !== milestone.name) {
			onrename?.(milestone.id, trimmed);
		} else {
			editingName = milestone.name;
		}
	}

	function handleNameKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			(e.currentTarget as HTMLInputElement).blur();
		} else if (e.key === 'Escape') {
			editingName = milestone.name;
			(e.currentTarget as HTMLInputElement).blur();
		}
	}

	async function handleDelete() {
		const confirmed = await confirmModal.confirm({
			title: 'Delete Column',
			message: `Delete column "${milestone.name}"? Tasks in this column will need to be reassigned.`,
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (confirmed) {
			ondelete?.(milestone.id);
		}
	}

	let columnEl = $state<HTMLElement | null>(null);

	function handleColumnDragStart(e: DragEvent) {
		if (e.dataTransfer) {
			e.dataTransfer.setData('application/column-id', milestone.id);
			e.dataTransfer.effectAllowed = 'move';
			if (columnEl) {
				const width = columnEl.offsetWidth;
				const height = columnEl.offsetHeight;
				const rect = columnEl.getBoundingClientRect();
				// Clone over the original: in-viewport so Safari paints it,
				// isolated from siblings so Chrome doesn't capture surroundings.
				// Explicit dimensions prevent flex layout collapse in the detached clone.
				const clone = columnEl.cloneNode(true) as HTMLElement;
				clone.style.position = 'fixed';
				clone.style.top = rect.top + 'px';
				clone.style.left = rect.left + 'px';
				clone.style.width = width + 'px';
				clone.style.height = height + 'px';
				clone.style.overflow = 'hidden';
				clone.style.pointerEvents = 'none';
				document.body.appendChild(clone);
				e.dataTransfer.setDragImage(clone, e.clientX - rect.left, e.clientY - rect.top);
				requestAnimationFrame(() => clone.remove());
				// Delay callback to ensure drag image is captured before column is hidden
				requestAnimationFrame(() => {
					oncolumndragstart?.(milestone.id, width, height);
				});
			}
		}
	}

	function handleColumnDragEnd() {
		oncolumndragend?.();
	}

	function handleDragOver(e: DragEvent) {
		// Ignore column drags on the column itself (handled at board level)
		if (e.dataTransfer?.types.includes('application/column-id')) return;
		clearTimeout(dragLeaveTimer);
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOver = true;

		// Calculate drop position based on mouse Y
		const target = e.currentTarget as HTMLElement;
		const listEl = target.querySelector('[data-task-list]') as HTMLElement;
		if (listEl) {
			const cards = Array.from(listEl.querySelectorAll('[data-task-card]:not([data-dragging])'));
			let idx = cards.length;
			for (let i = 0; i < cards.length; i++) {
				const rect = cards[i].getBoundingClientRect();
				if (e.clientY < rect.top + rect.height / 2) {
					idx = i;
					break;
				}
			}
			dropIndex = idx;
		}
	}

	function handleDragLeave(e: DragEvent) {
		if (e.dataTransfer?.types.includes('application/column-id')) return;
		clearTimeout(dragLeaveTimer);
		dragLeaveTimer = setTimeout(() => {
			dragOver = false;
			dropIndex = null;
		}, 50);
	}

	function handleDrop(e: DragEvent) {
		// Ignore column drops (handled at board level)
		if (e.dataTransfer?.types.includes('application/column-id')) return;
		e.preventDefault();
		clearTimeout(dragLeaveTimer);
		dragOver = false;
		const taskId = e.dataTransfer?.getData('text/plain');
		const position = dropIndex ?? tasks.length;
		dropIndex = null;
		if (taskId) {
			ondrop?.(taskId, milestone.id, position);
		}
	}

	function handleDragStart(e: DragEvent, task: TaskResponse) {
		const wrapper = e.currentTarget as HTMLElement;
		if (e.dataTransfer) {
			e.dataTransfer.setData('text/plain', task.id);
			e.dataTransfer.effectAllowed = 'move';
			ontaskdragstart?.(wrapper.offsetHeight);
			// Clone wrapper offscreen so the drag image has no surrounding background
			const clone = wrapper.cloneNode(true) as HTMLElement;
			clone.style.position = 'absolute';
			clone.style.top = '-9999px';
			clone.style.left = '-9999px';
			clone.style.width = wrapper.offsetWidth + 'px';
			document.body.appendChild(clone);
			const rect = wrapper.getBoundingClientRect();
			e.dataTransfer.setDragImage(clone, e.clientX - rect.left, e.clientY - rect.top);
			requestAnimationFrame(() => clone.remove());
		}
		requestAnimationFrame(() => {
			draggingTaskId = task.id;
		});
	}

	function handleDragEnd(e: DragEvent) {
		draggingTaskId = null;
	}
</script>

<div
	bind:this={columnEl}
	class="flex flex-col bg-base-200 rounded-lg p-3 w-[calc(100vw-6rem)] sm:w-auto sm:min-w-72 sm:max-w-72 h-fit max-h-full {dragOver ? 'ring-2 ring-primary/50' : ''}"
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	ondrop={handleDrop}
	role="group"
	aria-label="{milestone.name} column"
>
	<div class="flex items-center justify-between mb-3" data-column-drag>
		<input
			type="text"
			class="font-semibold text-sm bg-transparent border-none outline-none focus:bg-base-300 rounded px-1 -ml-1 w-full"
			bind:value={editingName}
			onblur={commitRename}
			onkeydown={handleNameKeydown}
		/>
		<div class="flex items-center shrink-0 ml-1">
			{#if oncolumndragstart}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class="text-base-content/30 p-1 cursor-grab"
					data-grab
					draggable="true"
					ondragstart={handleColumnDragStart}
					ondragend={handleColumnDragEnd}
				>
					<GripVertical size={14} />
				</span>
			{:else}
				<span class="text-base-content/20 p-1" title="This column cannot be reordered">
					<Lock size={14} />
				</span>
			{/if}
			{#if ondelete}
				<button
					class="btn btn-ghost btn-xs btn-square text-base-content/30 hover:text-error"
					onclick={handleDelete}
					title="Delete column"
				>
					<Trash2 size={14} />
				</button>
			{/if}
		</div>
	</div>

	<div class="flex flex-col gap-2 flex-1 overflow-auto" data-task-list>
		{#if tasks.length === 0 && !dragOver}
			<div class="flex flex-col items-center justify-center py-6 text-base-content/30">
				<Inbox size={20} />
				<span class="text-xs mt-1">No tasks</span>
			</div>
		{/if}
		{#each tasks as task, i (task.id)}
			{#if dragOver && dropIndex === i}
				<div
					class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg min-h-[60px]"
					style="height: {draggedTaskHeight || 60}px;"
				></div>
			{/if}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				draggable="true"
				ondragstart={(e) => handleDragStart(e, task)}
				ondragend={handleDragEnd}
				role="listitem"
				data-task-card
				data-dragging={draggingTaskId === task.id ? '' : undefined}
			>
				{#if draggingTaskId !== task.id}
					<TaskCard
						{task}
						draggable
						selected={task.id === selectedTaskId}
						onclick={() => ontaskclick?.(task)}
						ondelete={() => ontaskdelete?.(task.id)}
					/>
				{/if}
			</div>
		{/each}
		{#if dragOver && dropIndex === tasks.length}
			<div
				class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg min-h-[60px]"
				style="height: {draggedTaskHeight || 60}px;"
			></div>
		{/if}
	</div>

	<TaskQuickAdd
		{projectId}
		milestoneId={milestone.id === '__unsorted__' ? null : milestone.id}
		oncreated={ontaskcreated}
	/>
</div>
