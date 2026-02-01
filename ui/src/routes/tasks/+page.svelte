<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/services/api';
	import type { ProjectResponse, ProjectList, TaskResponse, TaskList, TaskMove, MilestoneCreate } from '$lib/types';
	import KanbanBoard from '$lib/components/tasks/KanbanBoard.svelte';
	import TaskDetailPanel from '$lib/components/tasks/TaskDetailPanel.svelte';
	import TaskCreateModal from '$lib/components/tasks/TaskCreateModal.svelte';
	import TaskFilterBar from '$lib/components/tasks/TaskFilterBar.svelte';
	import { FolderKanban } from 'lucide-svelte';

	let projects = $state<ProjectResponse[]>([]);
	let selectedProjectId = $state('');
	let tasks = $state<TaskResponse[]>([]);
	let loading = $state(true);

	let selectedTask = $state<TaskResponse | null>(null);

	let createModalOpen = $state(false);
	let createMilestoneId = $state<string | null>(null);

	// Filter state
	let search = $state('');
	let priorityFilter = $state('all');
	let dueDateFilter = $state('all');
	let sortBy = $state('position');
	let sortDir = $state('asc');

	let filterBarRef = $state<ReturnType<typeof TaskFilterBar> | null>(null);

	let selectedProject = $derived(projects.find((p) => p.id === selectedProjectId));

	const priorityOrder: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3 };

	function isOverdue(d: string | null): boolean {
		if (!d) return false;
		const due = new Date(d);
		const today = new Date();
		due.setHours(0, 0, 0, 0);
		today.setHours(0, 0, 0, 0);
		return due < today;
	}

	function isToday(d: string | null): boolean {
		if (!d) return false;
		const due = new Date(d);
		const today = new Date();
		return due.toDateString() === today.toDateString();
	}

	function isThisWeek(d: string | null): boolean {
		if (!d) return false;
		const due = new Date(d);
		const today = new Date();
		const weekEnd = new Date(today);
		weekEnd.setDate(today.getDate() + (7 - today.getDay()));
		weekEnd.setHours(23, 59, 59, 999);
		return due <= weekEnd && due >= today;
	}

	let filteredTasks = $derived.by(() => {
		let result = tasks;

		if (search.trim()) {
			const q = search.toLowerCase();
			result = result.filter(
				(t) => t.title.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q)
			);
		}

		if (priorityFilter !== 'all') {
			result = result.filter((t) => t.priority === priorityFilter);
		}

		if (dueDateFilter === 'overdue') {
			result = result.filter((t) => isOverdue(t.due_date));
		} else if (dueDateFilter === 'today') {
			result = result.filter((t) => isToday(t.due_date));
		} else if (dueDateFilter === 'week') {
			result = result.filter((t) => isThisWeek(t.due_date));
		} else if (dueDateFilter === 'none') {
			result = result.filter((t) => !t.due_date);
		}

		result = [...result].sort((a, b) => {
			let cmp = 0;
			if (sortBy === 'position') {
				cmp = a.position - b.position;
			} else if (sortBy === 'due_date') {
				const aDate = a.due_date ?? '9999';
				const bDate = b.due_date ?? '9999';
				cmp = aDate.localeCompare(bDate);
			} else if (sortBy === 'priority') {
				cmp = (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2);
			} else if (sortBy === 'created_at') {
				cmp = a.created_at.localeCompare(b.created_at);
			}
			return sortDir === 'desc' ? -cmp : cmp;
		});

		return result;
	});

	let hasActiveFilters = $derived(
		search.trim() !== '' || priorityFilter !== 'all' || dueDateFilter !== 'all'
	);

	async function loadProjects() {
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
			if (projects.length > 0 && !selectedProjectId) {
				const paramProject = page.url.searchParams.get('project');
				const match = paramProject && projects.find((p) => p.id === paramProject);
				selectedProjectId = match ? match.id : projects[0].id;
			}
		} catch (e) {
			console.error('Failed to load projects', e);
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
		} catch (e) {
			console.error('Failed to load tasks', e);
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
		} catch (e) {
			tasks = oldTasks;
			console.error('Failed to move task', e);
		}
	}

	function handleTaskClick(task: TaskResponse) {
		selectedTask = selectedTask?.id === task.id ? null : task;
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
			`/api/projects/${selectedProjectId}/milestones`,
			{ milestones }
		);
		projects = projects.map((p) => (p.id === updated.id ? updated : p));
	}

	async function handleColumnRename(milestoneId: string, newName: string) {
		if (!selectedProject) return;
		const milestones: MilestoneCreate[] = selectedProject.milestones.map((m) => ({
			name: m.id === milestoneId ? newName : m.name,
			position: m.position
		}));
		try {
			await saveMilestones(milestones);
		} catch (e) {
			console.error('Failed to rename column', e);
		}
	}

	async function handleColumnDelete(milestoneId: string) {
		if (!selectedProject) return;
		const milestones: MilestoneCreate[] = selectedProject.milestones
			.filter((m) => m.id !== milestoneId)
			.sort((a, b) => a.position - b.position)
			.map((m, i) => ({ name: m.name, position: i }));
		try {
			await saveMilestones(milestones);
			await loadTasks(selectedProjectId);
		} catch (e) {
			console.error('Failed to delete column', e);
		}
	}

	async function handleColumnCreate(name: string) {
		if (!selectedProject) return;
		const milestones: MilestoneCreate[] = [
			...selectedProject.milestones.map((m) => ({ name: m.name, position: m.position })),
			{ name, position: selectedProject.milestones.length }
		];
		try {
			await saveMilestones(milestones);
		} catch (e) {
			console.error('Failed to create column', e);
		}
	}

	async function handleColumnReorder(milestoneId: string, newPosition: number) {
		if (!selectedProject) return;
		const sorted = [...selectedProject.milestones].sort((a, b) => a.position - b.position);
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
		} catch (e) {
			console.error('Failed to reorder columns', e);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
		if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
			e.preventDefault();
			filterBarRef?.focusSearch();
		} else if (e.key === 'N' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
			e.preventDefault();
			createMilestoneId = selectedProject?.milestones[0]?.id ?? null;
			createModalOpen = true;
		} else if (e.key === 'Escape' && selectedTask) {
			selectedTask = null;
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="absolute inset-0 flex overflow-hidden">
	<!-- Left: toolbar + kanban -->
	<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
		<!-- Toolbar -->
		<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
			<div class="dropdown">
				<button tabindex="0" class="btn btn-sm btn-ghost gap-1.5">
					<FolderKanban size={14} />
					<span class="max-w-32 truncate">{selectedProject?.name ?? 'Project'}</span>
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-52 p-1 border border-base-300 mt-1">
					{#each projects as project}
						<li>
							<button
								class={selectedProjectId === project.id ? 'active' : ''}
								onclick={() => (selectedProjectId = project.id)}
							>
								{#if project.color}
									<div class="w-2 h-2 rounded-full shrink-0" style:background-color={project.color}></div>
								{/if}
								{project.name}
							</button>
						</li>
					{/each}
				</ul>
			</div>

			<div class="flex-1 min-w-0">
				<TaskFilterBar
					bind:this={filterBarRef}
					bind:search
					bind:priorityFilter
					bind:dueDateFilter
					bind:sortBy
					bind:sortDir
					filteredCount={filteredTasks.length}
					totalCount={tasks.length}
				/>
			</div>
		</div>

		<!-- Kanban -->
		<div class="flex-1 overflow-hidden pt-4">
			{#if loading}
				<div class="flex items-center justify-center py-20">
					<span class="loading loading-spinner loading-lg"></span>
				</div>
			{:else if selectedProject}
				<div class="h-full overflow-hidden">
					<KanbanBoard
						milestones={selectedProject.milestones}
						tasks={hasActiveFilters ? filteredTasks : tasks}
						projectId={selectedProjectId}
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
			{:else}
				<p class="text-base-content/40 text-center py-20">No projects found</p>
			{/if}
		</div>
	</div>

	<!-- Right: task detail sidebar (full height, sibling of content column) -->
	{#if selectedTask}
		<TaskDetailPanel
			task={selectedTask}
			{projects}
			milestones={selectedProject?.milestones ?? []}
			onclose={() => (selectedTask = null)}
			onsaved={handleTaskSaved}
			ondeleted={handleTaskDeleted}
		/>
	{/if}
</div>

<TaskCreateModal
	bind:open={createModalOpen}
	projectId={selectedProjectId}
	milestoneId={createMilestoneId}
	milestones={selectedProject?.milestones ?? []}
	oncreated={handleTaskCreated}
/>
