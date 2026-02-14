<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { ProjectResponse, ProjectList, TaskResponse, TaskList, TaskMove, MilestoneCreate } from '$lib/types';
	import KanbanBoard from '$lib/components/tasks/KanbanBoard.svelte';
	import TaskDetailPanel from '$lib/components/tasks/TaskDetailPanel.svelte';
	import TaskCreateModal from '$lib/components/tasks/TaskCreateModal.svelte';
	import TaskFilterBar from '$lib/components/tasks/TaskFilterBar.svelte';
	import ProjectIcon from '$lib/components/ui/ProjectIcon.svelte';
	import { ChevronLeft, ChevronRight, CircleCheckBig } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';
	import { ws } from '$lib/stores/websocket.svelte';

	let projects = $state<ProjectResponse[]>([]);
	let sidebarExpanded = $state(false);
	let selectedProjectId = $derived(page.params.projectId ?? '');
	let tasks = $state<TaskResponse[]>([]);
	let loading = $state(true);

	function selectProject(id: string) {
		goto(`${base}/tasks/${id}`);
	}

	let selectedTask = $state<TaskResponse | null>(null);

	let createModalOpen = $state(false);
	let createMilestoneId = $state<string | null>(null);

	// Filter state
	let search = $state('');
	let priorityFilter = $state('all');
	let dueDateFilter = $state('all');
	let sortBy = $state('position');
	let sortDir = $state('asc');
	let showCompleted = $state(false);

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
		} catch (e) {
			console.error('Failed to load projects', e);
			toast.error('Failed to load projects');
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
			toast.error('Failed to load tasks');
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

	// WebSocket: silently refresh tasks when modified externally (no loading spinner)
	$effect(() => {
		const projectId = selectedProjectId;
		return ws.on(
			['task_created', 'task_updated', 'task_deleted', 'project_updated', 'project_reordered'],
			async () => {
				if (projectId) {
					try {
						const res = await api.get<TaskList>(`/api/tasks?project_id=${projectId}&limit=200`);
						tasks = res.tasks;
						// Update selectedTask in-place if it's still present
						if (selectedTask) {
							const updated = res.tasks.find((t) => t.id === selectedTask!.id);
							if (updated) selectedTask = updated;
						}
					} catch { /* ignore */ }
				}
				try {
					const res = await api.get<ProjectList>('/api/projects');
					projects = res.projects;
				} catch { /* ignore */ }
			},
			500
		);
	});

	// Auto-select task from URL query param (for linked task navigation)
	$effect(() => {
		const taskId = page.url.searchParams.get('task');
		if (taskId && tasks.length > 0 && !loading) {
			const task = tasks.find(t => t.id === taskId);
			if (task) {
				selectedTask = task;
				// Clear the query param from URL to avoid re-selecting on navigation
				const url = new URL(window.location.href);
				url.searchParams.delete('task');
				goto(url.pathname, { replaceState: true });
			}
		}
	});

	async function handleDrop(taskId: string, milestoneId: string | null, position: number) {
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
			toast.error('Failed to move task');
		}
	}

	function handleTaskClick(task: TaskResponse) {
		selectedTask = selectedTask?.id === task.id ? null : task;
	}

	function handleTaskCreated(task: TaskResponse) {
		tasks = [...tasks, task];
	}

	function handleTaskSaved(task: TaskResponse) {
		const oldTask = tasks.find((t) => t.id === task.id);
		if (task.project_id !== selectedProjectId) {
			tasks = tasks.filter((t) => t.id !== task.id);
			selectedTask = null;
		} else {
			tasks = tasks.map((t) => (t.id === task.id ? task : t));
			selectedTask = task;
		}
		// Recurring task just completed → refetch to pick up spawned next instance
		if (task.status === 'done' && task.recurrence_rule && oldTask?.status !== 'done') {
			loadTasks(selectedProjectId);
		}
	}

	function handleTaskDeleted(taskId: string) {
		tasks = tasks.filter((t) => t.id !== taskId);
		selectedTask = null;
	}

	async function handleTaskDeleteFromSwipe(taskId: string) {
		const task = tasks.find((t) => t.id === taskId);
		const confirmed = await confirmModal.confirm({
			title: 'Delete Task',
			message: `Delete "${task?.title}"?`,
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;

		try {
			await api.delete(`/api/tasks/${taskId}`);
			handleTaskDeleted(taskId);
		} catch (e) {
			console.error('Failed to delete task', e);
			toast.error('Failed to delete task');
		}
	}

	async function handleStatusToggle(taskId: string, newStatus: string) {
		const oldTasks = [...tasks];
		const oldTask = tasks.find((t) => t.id === taskId);
		tasks = tasks.map((t) => t.id === taskId ? { ...t, status: newStatus } : t);
		try {
			const updated = await api.put<TaskResponse>(`/api/tasks/${taskId}`, { status: newStatus });
			tasks = tasks.map((t) => (t.id === taskId ? updated : t));
			if (selectedTask?.id === taskId) selectedTask = updated;
			// Recurring task completed → refetch to pick up the spawned next instance
			if (newStatus === 'done' && oldTask?.recurrence_rule) {
				await loadTasks(selectedProjectId);
			}
		} catch (e) {
			tasks = oldTasks;
			console.error('Failed to update task status', e);
			toast.error('Failed to update task status');
		}
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
			id: m.id,
			name: m.id === milestoneId ? newName : m.name,
			position: m.position
		}));
		try {
			await saveMilestones(milestones);
		} catch (e) {
			console.error('Failed to rename column', e);
			toast.error('Failed to rename column');
		}
	}

	async function handleColumnDelete(milestoneId: string) {
		if (!selectedProject) return;
		const milestones: MilestoneCreate[] = selectedProject.milestones
			.filter((m) => m.id !== milestoneId)
			.sort((a, b) => a.position - b.position)
			.map((m, i) => ({ id: m.id, name: m.name, position: i }));
		try {
			await saveMilestones(milestones);
			await loadTasks(selectedProjectId);
		} catch (e) {
			console.error('Failed to delete column', e);
			toast.error('Failed to delete column');
		}
	}

	async function handleColumnCreate(name: string) {
		if (!selectedProject) return;
		const milestones: MilestoneCreate[] = [
			...selectedProject.milestones.map((m) => ({ id: m.id, name: m.name, position: m.position })),
			{ name, position: selectedProject.milestones.length }
		];
		try {
			await saveMilestones(milestones);
		} catch (e) {
			console.error('Failed to create column', e);
			toast.error('Failed to create column');
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
			id: m.id,
			name: m.name,
			position: i
		}));
		try {
			await saveMilestones(milestones);
		} catch (e) {
			console.error('Failed to reorder columns', e);
			toast.error('Failed to reorder columns');
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Ctrl/Cmd+S: prevent browser save when task sidebar is open
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			if (selectedTask) {
				e.preventDefault();
			}
			return;
		}

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
	<!-- Project sidebar (collapsible) -->
	<div class="{sidebarExpanded ? 'w-56' : 'w-16'} shrink-0 border-r border-base-300 flex flex-col transition-all duration-200 overflow-hidden">
		<div class="flex-1 flex flex-col gap-1 px-2 py-2 overflow-y-auto">
			<button
				class="rounded-lg flex items-center justify-center transition-colors shrink-0 h-9 px-3
					hover:bg-base-300 text-base-content/90"
				onclick={() => (sidebarExpanded = !sidebarExpanded)}
				title={sidebarExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
			>
				{#if sidebarExpanded}
					<ChevronLeft size={18} />
				{:else}
					<ChevronRight size={18} />
				{/if}
			</button>
			{#each projects as project (project.id)}
				<button
					class="rounded-lg flex items-center transition-colors shrink-0 relative group h-9
						{sidebarExpanded ? 'w-full px-3 gap-3' : 'px-3 justify-center'}
						{selectedProjectId === project.id
							? 'text-base-100'
							: 'hover:bg-base-300 text-base-content/90'}"
					onclick={() => selectProject(project.id)}
					title={sidebarExpanded ? undefined : project.name}
					style={selectedProjectId === project.id
						? `background-color: ${project.color || '#6b7280'}`
						: undefined}
				>
					<div
						class="shrink-0"
						style={selectedProjectId !== project.id
							? `color: ${project.color || '#6b7280'}`
							: undefined}
					>
						<ProjectIcon name={project.icon || 'folder-kanban'} size={18} />
					</div>
					{#if sidebarExpanded}
						<span class="text-sm truncate min-w-0">{project.name}</span>
					{:else}
						<!-- Tooltip -->
						<span class="absolute left-full ml-2 px-2 py-1 text-xs bg-base-300 text-base-content rounded shadow-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-20">
							{project.name}
						</span>
					{/if}
				</button>
			{/each}
		</div>
	</div>

	<!-- Main: toolbar + kanban -->
	<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
		<!-- Toolbar -->
		<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
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
			<button
				class="btn btn-ghost btn-xs sm:btn-sm {showCompleted ? 'btn-active' : ''}"
				onclick={() => (showCompleted = !showCompleted)}
				title={showCompleted ? 'Hide completed' : 'Show completed'}
			>
				<CircleCheckBig size={14} />
				<span class="hidden sm:inline text-xs">Completed</span>
			</button>
		</div>

		<!-- Kanban -->
		<div class="flex-1 overflow-hidden">
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
						{showCompleted}
						ontaskclick={handleTaskClick}
						ondrop={handleDrop}
						ontaskcreated={handleTaskCreated}
						oncolumnrename={handleColumnRename}
						oncolumndelete={handleColumnDelete}
						oncolumncreate={handleColumnCreate}
						oncolumnreorder={handleColumnReorder}
						ontaskdelete={handleTaskDeleteFromSwipe}
						onstatustoggle={handleStatusToggle}
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
