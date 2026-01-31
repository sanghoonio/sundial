<script lang="ts">
	import type { TaskResponse, MilestoneResponse } from '$lib/types';
	import KanbanColumn from './KanbanColumn.svelte';

	interface Props {
		milestones: MilestoneResponse[];
		tasks: TaskResponse[];
		projectId: string;
		ontaskclick?: (task: TaskResponse) => void;
		ondrop?: (taskId: string, milestoneId: string, position: number) => void;
		ontaskcreated?: (task: TaskResponse) => void;
	}

	let { milestones, tasks, projectId, ontaskclick, ondrop, ontaskcreated }: Props = $props();

	function tasksForMilestone(msId: string): TaskResponse[] {
		return tasks
			.filter((t) => t.milestone_id === msId)
			.sort((a, b) => a.position - b.position);
	}
</script>

<div class="flex gap-4 overflow-x-auto pb-4 h-full">
	{#each milestones.toSorted((a, b) => a.position - b.position) as ms (ms.id)}
		<KanbanColumn
			milestone={ms}
			tasks={tasksForMilestone(ms.id)}
			{projectId}
			{ontaskclick}
			{ondrop}
			{ontaskcreated}
		/>
	{/each}
</div>
