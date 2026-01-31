<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import TaskCard from './TaskCard.svelte';
	import TaskQuickAdd from './TaskQuickAdd.svelte';

	interface Props {
		milestone: MilestoneResponse;
		tasks: TaskResponse[];
		projectId: string;
		ontaskclick?: (task: TaskResponse) => void;
		ondrop?: (taskId: string, milestoneId: string, position: number) => void;
		ontaskcreated?: (task: TaskResponse) => void;
	}

	let { milestone, tasks, projectId, ontaskclick, ondrop, ontaskcreated }: Props = $props();

	let dragOver = $state(false);

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const taskId = e.dataTransfer?.getData('text/plain');
		if (taskId) {
			ondrop?.(taskId, milestone.id, tasks.length);
		}
	}

	function handleDragStart(e: DragEvent, task: TaskResponse) {
		if (e.dataTransfer) {
			e.dataTransfer.setData('text/plain', task.id);
			e.dataTransfer.effectAllowed = 'move';
		}
	}
</script>

<div
	class="flex flex-col bg-base-200 rounded-lg p-3 min-w-72 max-w-72 h-fit max-h-full {dragOver ? 'ring-2 ring-primary/50' : ''}"
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	ondrop={handleDrop}
	role="group"
	aria-label="{milestone.name} column"
>
	<div class="flex items-center justify-between mb-3">
		<h3 class="font-semibold text-sm">{milestone.name}</h3>
		<span class="badge badge-sm badge-ghost">{tasks.length}</span>
	</div>

	<div class="flex flex-col gap-2 flex-1 overflow-auto">
		{#each tasks as task (task.id)}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				draggable="true"
				ondragstart={(e) => handleDragStart(e, task)}
				role="listitem"
			>
				<TaskCard
					{task}
					draggable
					onclick={() => ontaskclick?.(task)}
				/>
			</div>
		{/each}
	</div>

	<TaskQuickAdd
		{projectId}
		milestoneId={milestone.id}
		oncreated={ontaskcreated}
	/>
</div>
