<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import TaskCard from './TaskCard.svelte';
	import TaskQuickAdd from './TaskQuickAdd.svelte';
	import { Inbox, Trash2, GripVertical } from 'lucide-svelte';

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
	}

	let { milestone, tasks, projectId, selectedTaskId = null, ontaskclick, ondrop, ontaskcreated, onrename, ondelete }: Props = $props();

	let dragOver = $state(false);
	let dropIndex = $state<number | null>(null);
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

	function handleDelete() {
		if (confirm(`Delete column "${milestone.name}"? Tasks in this column will need to be reassigned.`)) {
			ondelete?.(milestone.id);
		}
	}

	let columnEl = $state<HTMLElement | null>(null);

	function handleColumnDragStart(e: DragEvent) {
		if (e.dataTransfer) {
			e.dataTransfer.setData('application/column-id', milestone.id);
			e.dataTransfer.effectAllowed = 'move';
			if (columnEl) {
				const rect = columnEl.getBoundingClientRect();
				e.dataTransfer.setDragImage(columnEl, e.clientX - rect.left, e.clientY - rect.top);
			}
		}
	}

	function handleDragOver(e: DragEvent) {
		// Ignore column drags on the column itself (handled at board level)
		if (e.dataTransfer?.types.includes('application/column-id')) return;
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOver = true;

		// Calculate drop position based on mouse Y
		const target = e.currentTarget as HTMLElement;
		const listEl = target.querySelector('[data-task-list]') as HTMLElement;
		if (listEl) {
			const cards = Array.from(listEl.querySelectorAll('[data-task-card]'));
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
		// Only leave if we're actually leaving the column
		const related = e.relatedTarget as Node | null;
		const col = e.currentTarget as HTMLElement;
		if (related && col.contains(related)) return;
		dragOver = false;
		dropIndex = null;
	}

	function handleDrop(e: DragEvent) {
		// Ignore column drops (handled at board level)
		if (e.dataTransfer?.types.includes('application/column-id')) return;
		e.preventDefault();
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
		const card = wrapper.querySelector('.card') as HTMLElement;
		if (e.dataTransfer) {
			e.dataTransfer.setData('text/plain', task.id);
			e.dataTransfer.effectAllowed = 'move';
			if (card) {
				// Clone card offscreen so the drag image has no surrounding background
				const clone = card.cloneNode(true) as HTMLElement;
				clone.style.position = 'absolute';
				clone.style.top = '-9999px';
				clone.style.left = '-9999px';
				clone.style.width = card.offsetWidth + 'px';
				document.body.appendChild(clone);
				const rect = card.getBoundingClientRect();
				e.dataTransfer.setDragImage(clone, e.clientX - rect.left, e.clientY - rect.top);
				requestAnimationFrame(() => clone.remove());
			}
		}
		requestAnimationFrame(() => {
			wrapper.style.opacity = '0.4';
		});
	}

	function handleDragEnd(e: DragEvent) {
		const target = e.currentTarget as HTMLElement;
		target.style.opacity = '1';
	}
</script>

<div
	bind:this={columnEl}
	class="flex flex-col bg-base-200 rounded-lg p-3 w-[calc(100vw-3rem)] sm:w-auto sm:min-w-72 sm:max-w-72 h-fit max-h-full {dragOver ? 'ring-2 ring-primary/50' : ''}"
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
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<span
				class="text-base-content/30 p-1"
				data-grab
				draggable="true"
				ondragstart={handleColumnDragStart}
			>
				<GripVertical size={14} />
			</span>
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
				<div class="h-0.5 bg-primary rounded-full mx-2 my-0.5"></div>
			{/if}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				draggable="true"
				ondragstart={(e) => handleDragStart(e, task)}
				ondragend={handleDragEnd}
				role="listitem"
				data-task-card
			>
				<TaskCard
					{task}
					draggable
					selected={task.id === selectedTaskId}
					onclick={() => ontaskclick?.(task)}
				/>
			</div>
		{/each}
		{#if dragOver && dropIndex === tasks.length}
			<div class="h-0.5 bg-primary rounded-full mx-2 my-0.5"></div>
		{/if}
	</div>

	<TaskQuickAdd
		{projectId}
		milestoneId={milestone.id}
		oncreated={ontaskcreated}
	/>
</div>
