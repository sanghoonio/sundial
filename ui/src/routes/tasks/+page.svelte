<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { ProjectResponse, ProjectList, TaskResponse, TaskList, TaskMove } from '$lib/types';
	import KanbanBoard from '$lib/components/tasks/KanbanBoard.svelte';
	import TaskDetailModal from '$lib/components/tasks/TaskDetailModal.svelte';

	let projects = $state<ProjectResponse[]>([]);
	let selectedProjectId = $state('');
	let tasks = $state<TaskResponse[]>([]);
	let loading = $state(true);

	let selectedTask = $state<TaskResponse | null>(null);
	let modalOpen = $state(false);

	let selectedProject = $derived(projects.find((p) => p.id === selectedProjectId));

	async function loadProjects() {
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
			if (projects.length > 0 && !selectedProjectId) {
				selectedProjectId = projects[0].id;
			}
		} catch {
			toasts.error('Failed to load projects');
			loading = false;
		}
	}

	async function loadTasks(projectId: string) {
		loading = true;
		try {
			const res = await api.get<TaskList>(
				`/api/tasks?project_id=${projectId}&limit=200`
			);
			tasks = res.tasks;
		} catch {
			toasts.error('Failed to load tasks');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadProjects();
	});

	$effect(() => {
		const projectId = selectedProjectId;
		if (projectId) {
			loadTasks(projectId);
		}
	});

	async function handleDrop(taskId: string, milestoneId: string, position: number) {
		try {
			const move: TaskMove = { milestone_id: milestoneId, position };
			const updated = await api.put<TaskResponse>(`/api/tasks/${taskId}/move`, move);
			tasks = tasks.map((t) => (t.id === taskId ? updated : t));
		} catch {
			toasts.error('Failed to move task');
		}
	}

	function handleTaskClick(task: TaskResponse) {
		selectedTask = task;
		modalOpen = true;
	}

	function handleTaskCreated(task: TaskResponse) {
		tasks = [...tasks, task];
	}

	function handleTaskSaved(task: TaskResponse) {
		tasks = tasks.map((t) => (t.id === task.id ? task : t));
		selectedTask = null;
	}

	function handleTaskDeleted(taskId: string) {
		tasks = tasks.filter((t) => t.id !== taskId);
		selectedTask = null;
	}
</script>

<div class="flex items-center gap-3 mb-4">
	<select
		class="select select-bordered select-sm"
		bind:value={selectedProjectId}
	>
		{#each projects as project}
			<option value={project.id}>{project.name}</option>
		{/each}
	</select>
</div>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if selectedProject}
	<div class="h-[calc(100vh-12rem)] overflow-hidden">
		<KanbanBoard
			milestones={selectedProject.milestones}
			{tasks}
			projectId={selectedProjectId}
			ontaskclick={handleTaskClick}
			ondrop={handleDrop}
			ontaskcreated={handleTaskCreated}
		/>
	</div>
{:else}
	<p class="text-base-content/40 text-center py-20">No projects found</p>
{/if}

<TaskDetailModal
	task={selectedTask}
	bind:open={modalOpen}
	onsaved={handleTaskSaved}
	ondeleted={handleTaskDeleted}
/>
