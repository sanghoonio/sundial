<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type {
		ProjectResponse,
		ProjectUpdate,
		ProjectList,
		TaskResponse,
		TaskList,
		TaskMove,
		MilestoneCreate
	} from '$lib/types';
	import KanbanBoard from '$lib/components/tasks/KanbanBoard.svelte';
	import TaskDetailPanel from '$lib/components/tasks/TaskDetailPanel.svelte';
	import TaskCreateModal from '$lib/components/tasks/TaskCreateModal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ArrowLeft, Settings2, Trash2, CheckSquare } from 'lucide-svelte';

	let project = $state<ProjectResponse | null>(null);
	let allProjects = $state<ProjectResponse[]>([]);
	let tasks = $state<TaskResponse[]>([]);
	let loading = $state(true);

	let selectedTask = $state<TaskResponse | null>(null);

	let createModalOpen = $state(false);
	let createMilestoneId = $state<string | null>(null);

	let settingsOpen = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editColor = $state('');
	let editStatus = $state('active');
	let saving = $state(false);

	let projectId = $derived(page.params.id ?? '');
	let completedCount = $derived(tasks.filter((t) => t.status === 'done').length);
	let completionPct = $derived(tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0);

	const statusBadgeClass: Record<string, string> = {
		active: 'badge-success',
		paused: 'badge-warning',
		completed: 'badge-info',
		archived: 'badge-ghost'
	};

	async function load() {
		loading = true;
		try {
			const [p, t, pl] = await Promise.all([
				api.get<ProjectResponse>(`/api/projects/${projectId}`),
				api.get<TaskList>(`/api/tasks?project_id=${projectId}&limit=200`),
				api.get<ProjectList>('/api/projects?limit=100')
			]);
			project = p;
			tasks = t.tasks;
			allProjects = pl.projects;
		} catch {
			toasts.error('Failed to load project');
			goto('/projects');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		projectId;
		load();
	});

	async function handleDrop(taskId: string, milestoneId: string, position: number) {
		const movingTask = tasks.find((t) => t.id === taskId);
		if (!movingTask) return;

		// Skip if dropped in the same spot
		if (movingTask.milestone_id === milestoneId) {
			const columnTasks = tasks
				.filter((t) => t.milestone_id === milestoneId)
				.sort((a, b) => a.position - b.position);
			const currentIndex = columnTasks.findIndex((t) => t.id === taskId);
			if (position === currentIndex || position === currentIndex + 1) return;
		}

		const oldTasks = [...tasks];
		tasks = tasks.map((t) =>
			t.id === taskId ? { ...t, milestone_id: milestoneId, position } : t
		);
		try {
			const move: TaskMove = { milestone_id: milestoneId, position };
			const updated = await api.put<TaskResponse>(`/api/tasks/${taskId}/move`, move);
			tasks = tasks.map((t) => (t.id === taskId ? updated : t));
		} catch {
			tasks = oldTasks;
			toasts.error('Failed to move task');
		}
	}

	function handleTaskClick(task: TaskResponse) {
		selectedTask = task;
	}

	function handleTaskCreated(task: TaskResponse) {
		tasks = [...tasks, task];
	}

	function handleTaskSaved(task: TaskResponse) {
		tasks = tasks.map((t) => (t.id === task.id ? task : t));
		selectedTask = task;
	}

	function handleTaskDeleted(taskId: string) {
		tasks = tasks.filter((t) => t.id !== taskId);
		selectedTask = null;
	}

	// Column operations

	async function saveMilestones(milestones: MilestoneCreate[]) {
		const updated = await api.put<ProjectResponse>(
			`/api/projects/${projectId}/milestones`,
			{ milestones }
		);
		project = updated;
	}

	async function handleColumnRename(milestoneId: string, newName: string) {
		if (!project) return;
		const milestones: MilestoneCreate[] = project.milestones.map((m) => ({
			name: m.id === milestoneId ? newName : m.name,
			position: m.position
		}));
		try {
			await saveMilestones(milestones);
		} catch {
			toasts.error('Failed to rename column');
		}
	}

	async function handleColumnDelete(milestoneId: string) {
		if (!project) return;
		const milestones: MilestoneCreate[] = project.milestones
			.filter((m) => m.id !== milestoneId)
			.sort((a, b) => a.position - b.position)
			.map((m, i) => ({ name: m.name, position: i }));
		try {
			await saveMilestones(milestones);
		} catch {
			toasts.error('Failed to delete column');
		}
	}

	async function handleColumnCreate(name: string) {
		if (!project) return;
		const milestones: MilestoneCreate[] = [
			...project.milestones.map((m) => ({ name: m.name, position: m.position })),
			{ name, position: project.milestones.length }
		];
		try {
			await saveMilestones(milestones);
		} catch {
			toasts.error('Failed to create column');
		}
	}

	async function handleColumnReorder(milestoneId: string, newPosition: number) {
		if (!project) return;
		const sorted = [...project.milestones].sort((a, b) => a.position - b.position);
		const oldIndex = sorted.findIndex((m) => m.id === milestoneId);
		if (oldIndex === -1) return;
		const [moved] = sorted.splice(oldIndex, 1);
		sorted.splice(newPosition, 0, moved);
		const milestones: MilestoneCreate[] = sorted.map((m, i) => ({
			name: m.name,
			position: i
		}));
		try {
			await saveMilestones(milestones);
		} catch {
			toasts.error('Failed to reorder columns');
		}
	}

	function openSettings() {
		if (!project) return;
		editName = project.name;
		editDescription = project.description || '';
		editColor = project.color || '#3b82f6';
		editStatus = project.status;
		settingsOpen = true;
	}

	async function saveSettings() {
		if (!project || !editName.trim()) return;
		saving = true;
		try {
			const updated = await api.put<ProjectResponse>(`/api/projects/${projectId}`, {
				name: editName.trim(),
				description: editDescription.trim(),
				color: editColor,
				status: editStatus
			} as ProjectUpdate);

			project = { ...project, ...updated };
			settingsOpen = false;
			toasts.success('Project updated');
		} catch {
			toasts.error('Failed to update project');
		} finally {
			saving = false;
		}
	}

	async function handleDeleteProject() {
		if (!confirm('Delete this project and all its tasks?')) return;
		try {
			await api.delete(`/api/projects/${projectId}`);
			toasts.success('Project deleted');
			goto('/projects');
		} catch {
			toasts.error('Failed to delete project');
		}
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if project}
	<div class="absolute inset-0 flex overflow-hidden">
		<!-- Left: header + kanban -->
		<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
			<!-- Header -->
			<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
				<a href="/projects" class="btn btn-ghost btn-sm btn-square">
					<ArrowLeft size={18} />
				</a>
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2">
						{#if project.color}
							<div class="w-3 h-3 rounded-full shrink-0" style:background-color={project.color}></div>
						{/if}
						<h2 class="font-semibold truncate">{project.name}</h2>
						<span class="badge badge-sm {statusBadgeClass[project.status] ?? 'badge-ghost'}">{project.status}</span>
					</div>
					{#if project.description}
						<p class="text-sm text-base-content/60 truncate">{project.description}</p>
					{/if}
				</div>
				<div class="flex items-center gap-2 text-xs text-base-content/50 shrink-0">
					<CheckSquare size={14} />
					<span>{completedCount}/{tasks.length}</span>
					{#if tasks.length > 0}
						<span class="text-base-content/40">({completionPct}%)</span>
					{/if}
				</div>
				<button class="btn btn-ghost btn-sm" onclick={openSettings}>
					<Settings2 size={16} />
				</button>
			</div>

			{#if tasks.length > 0}
				<div class="h-1 bg-base-300 shrink-0">
					<div
						class="h-full transition-all {completionPct === 100 ? 'bg-success' : 'bg-primary'}"
						style:width="{completionPct}%"
					></div>
				</div>
			{/if}

			<!-- Kanban -->
			<div class="flex-1 overflow-hidden py-4">
				<div class="h-full overflow-hidden">
					<KanbanBoard
						milestones={project.milestones}
						{tasks}
						projectId={projectId}
						selectedTaskId={selectedTask?.id}
						ontaskclick={handleTaskClick}
						ondrop={handleDrop}
						ontaskcreated={handleTaskCreated}
						oncolumnrename={handleColumnRename}
						oncolumndelete={handleColumnDelete}
						oncolumncreate={handleColumnCreate}
						oncolumnreorder={handleColumnReorder}
					/>
				</div>
			</div>
		</div>

		<!-- Right: task detail sidebar (full height) -->
		{#if selectedTask}
			<TaskDetailPanel
				task={selectedTask}
				projects={allProjects}
				milestones={project?.milestones ?? []}
				onclose={() => (selectedTask = null)}
				onsaved={handleTaskSaved}
				ondeleted={handleTaskDeleted}
			/>
		{/if}
	</div>

	<TaskCreateModal
		bind:open={createModalOpen}
		projectId={projectId}
		milestoneId={createMilestoneId}
		milestones={project?.milestones ?? []}
		oncreated={handleTaskCreated}
	/>

	<Modal bind:open={settingsOpen} title="Project Settings" onclose={() => (settingsOpen = false)}>
		<div class="flex flex-col gap-3">
			<Input placeholder="Project name" bind:value={editName} />
			<textarea
				class="textarea textarea-bordered w-full text-sm"
				rows="2"
				placeholder="Description"
				bind:value={editDescription}
			></textarea>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<p class="text-xs text-base-content/60 mb-1">Status</p>
					<select class="select select-bordered select-sm w-full" bind:value={editStatus}>
						<option value="active">Active</option>
						<option value="paused">Paused</option>
						<option value="completed">Completed</option>
						<option value="archived">Archived</option>
					</select>
				</div>
				<div>
					<p class="text-xs text-base-content/60 mb-1">Color</p>
					<div class="flex items-center gap-2">
						<input type="color" class="w-8 h-8 rounded cursor-pointer border-0" bind:value={editColor} />
						<span class="text-xs text-base-content/50">{editColor}</span>
					</div>
				</div>
			</div>

			<div class="flex items-center gap-2 mt-2">
				<Button variant="primary" loading={saving} onclick={saveSettings}>
					Save
				</Button>
				<button class="btn btn-ghost btn-sm text-error" onclick={handleDeleteProject}>
					<Trash2 size={16} />
					Delete Project
				</button>
			</div>
		</div>
	</Modal>
{/if}
