<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type {
		ProjectResponse,
		ProjectList,
		ProjectCreate,
		ProjectUpdate,
		TaskList,
		NoteListItem,
		NoteList
	} from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import IconPicker from '$lib/components/ui/IconPicker.svelte';
	import ProjectIcon from '$lib/components/ui/ProjectIcon.svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';
	import {
		Plus, FolderKanban, CheckSquare, ExternalLink,
		Trash2, Save, Check, Clock, X, ArrowLeft, GripVertical, GanttChart
	} from 'lucide-svelte';
	import ProjectTimeline from '$lib/components/projects/ProjectTimeline.svelte';

	let projects = $state<ProjectResponse[]>([]);
	let loading = $state(true);

	let statusFilter = $state('all');
	let viewMode = $state<'grid' | 'timeline'>(page.url.searchParams.get('view') === 'timeline' ? 'timeline' : 'grid');

	// Create state (sidebar)
	let isCreating = $state(false);
	let newId = $state('');
	let newName = $state('');
	let newDescription = $state('');
	let newColor = $state('#3b82f6');
	let newIcon = $state('folder-kanban');
	let creating = $state(false);

	const statusFilters = ['all', 'active', 'paused', 'completed', 'archived'] as const;
	const colorPresets = [
		'#3b82f6', '#6366f1', '#8b5cf6', '#ec4899',
		'#ef4444', '#f97316', '#f59e0b', '#22c55e',
		'#14b8a6', '#06b6d4', '#0ea5e9', '#6b7280',
	];

	// Selected project sidebar
	let selectedProjectId = $state<string | null>(page.url.searchParams.get('id'));
	let selectedProject = $state<ProjectResponse | null>(null);
	let sidebarTasks = $state<{ done: number; total: number }>({ done: 0, total: 0 });
	let sidebarNotes = $state<NoteListItem[]>([]);
	let sidebarLoading = $state(false);

	// Sidebar edit state
	let editName = $state('');
	let editDescription = $state('');
	let editColor = $state('');
	let editIcon = $state('folder-kanban');
	let editStatus = $state('active');

	// Auto-save state
	let sidebarLoaded = $state(false);
	let saving = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;
	let lastSavedSnapshot = $state('');
	let autoSaveTimer: ReturnType<typeof setTimeout>;

	let completionPct = $derived(sidebarTasks.total > 0 ? Math.round((sidebarTasks.done / sidebarTasks.total) * 100) : 0);

	// Drag state for project reordering
	let draggingProjectId = $state<string | null>(null);
	let draggedProjectWidth = $state(0);
	let draggedProjectHeight = $state(0);
	let projectDragOverIndex = $state<number | null>(null);
	let gridDragLeaveTimer: ReturnType<typeof setTimeout>;

	let filteredProjects = $derived.by(() => {
		let filtered = statusFilter === 'all' ? projects : projects.filter((p) => p.status === statusFilter);
		return filtered.slice().sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
	});

	async function loadProjects() {
		loading = true;
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
		} catch (e) {
			console.error('Failed to load projects', e);
			toast.error('Failed to load projects');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadProjects();
	});

	// Load sidebar data when a project is selected
	$effect(() => {
		const id = selectedProjectId;
		if (!id) {
			selectedProject = null;
			sidebarLoaded = false;
			return;
		}
		loadSidebarProject(id);
	});

	async function loadSidebarProject(id: string) {
		sidebarLoading = true;
		sidebarLoaded = false;
		try {
			const [p, t] = await Promise.all([
				api.get<ProjectResponse>(`/api/projects/${id}`),
				api.get<TaskList>(`/api/tasks?project_id=${id}&limit=200`)
			]);
			selectedProject = p;
			const done = t.tasks.filter((tk) => tk.status === 'done').length;
			sidebarTasks = { done, total: t.tasks.length };
			editName = p.name;
			editDescription = p.description || '';
			editColor = p.color || '#3b82f6';
			editIcon = p.icon || 'folder-kanban';
			editStatus = p.status;
			saveStatus = 'idle';
			showSavedText = false;
			lastSavedSnapshot = currentSnapshot();
			sidebarLoaded = true;
			try {
				const n = await api.get<NoteList>(`/api/notes?project_id=${id}`);
				sidebarNotes = n.notes;
			} catch {
				sidebarNotes = [];
			}
		} catch (e) {
			console.error('Failed to load project', e);
			toast.error('Failed to load project');
			selectedProjectId = null;
		} finally {
			sidebarLoading = false;
		}
	}

	function selectProject(id: string) {
		if (selectedProjectId === id) {
			closeSidebar();
		} else {
			selectedProjectId = id;
			goto(`${base}/projects?id=${id}`, { replaceState: true });
		}
	}

	function closeSidebar() {
		selectedProjectId = null;
		selectedProject = null;
		isCreating = false;
		sidebarLoaded = false;
		goto(`${base}/projects`, { replaceState: true });
	}

	function currentSnapshot(): string {
		return JSON.stringify({ editName, editDescription, editColor, editIcon, editStatus });
	}

	async function handleSave() {
		if (!selectedProject || !editName.trim()) return;
		saving = true;
		saveStatus = 'saving';
		try {
			const updated = await api.put<ProjectResponse>(`/api/projects/${selectedProjectId}`, {
				name: editName.trim(),
				description: editDescription.trim(),
				color: editColor,
				icon: editIcon,
				status: editStatus
			} as ProjectUpdate);
			selectedProject = { ...selectedProject, ...updated };
			projects = projects.map((p) => (p.id === updated.id ? { ...p, ...updated } : p));
			lastSavedSnapshot = currentSnapshot();
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => {
				showSavedText = false;
				saveStatus = 'idle';
			}, 2000);
		} catch (e) {
			saveStatus = 'error';
			console.error('Failed to update project', e);
			toast.error('Failed to update project');
		} finally {
			saving = false;
		}
	}

	// Auto-save: debounce 500ms after any change
	$effect(() => {
		if (!sidebarLoaded) return;
		const snap = currentSnapshot();
		if (snap === lastSavedSnapshot) return;

		saveStatus = 'idle';
		showSavedText = false;
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => handleSave(), 500);
		return () => clearTimeout(autoSaveTimer);
	});

	async function handleDeleteProject() {
		if (!selectedProjectId) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Project',
			message: 'Are you sure you want to delete this project and all its tasks?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		try {
			await api.delete(`/api/projects/${selectedProjectId}`);
			projects = projects.filter((p) => p.id !== selectedProjectId);
			closeSidebar();
		} catch (e) {
			console.error('Failed to delete project', e);
			toast.error('Failed to delete project');
		}
	}

	function openCreateSidebar() {
		newId = '';
		newName = '';
		newDescription = '';
		newColor = '#3b82f6';
		newIcon = 'folder-kanban';
		selectedProjectId = null;
		selectedProject = null;
		sidebarLoaded = false;
		isCreating = true;
	}

	async function handleCreate() {
		if (!newName.trim()) return;
		creating = true;
		try {
			const slug = newId.trim() || newName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
			const data: ProjectCreate = {
				id: slug,
				name: newName.trim(),
				description: newDescription.trim() || undefined,
				color: newColor,
				icon: newIcon
			};
			const created = await api.post<ProjectResponse>('/api/projects', data);
			projects = [...projects, created];
			isCreating = false;
			selectProject(created.id);
		} catch (e) {
			console.error('Failed to create project', e);
			toast.error('Failed to create project');
		} finally {
			creating = false;
		}
	}

	async function handleStatusChange(e: Event, project: ProjectResponse) {
		e.preventDefault();
		e.stopPropagation();
		const newStatus = (e.target as HTMLSelectElement).value;
		const oldStatus = project.status;
		projects = projects.map((p) =>
			p.id === project.id ? { ...p, status: newStatus } : p
		);
		try {
			await api.put<ProjectResponse>(`/api/projects/${project.id}`, {
				status: newStatus
			} as ProjectUpdate);
		} catch (e) {
			projects = projects.map((p) =>
				p.id === project.id ? { ...p, status: oldStatus } : p
			);
			console.error('Failed to update status', e);
		}
	}

	function statusBadge(status: string): string {
		switch (status) {
			case 'active': return 'badge-success';
			case 'paused': return 'badge-warning';
			case 'completed': return 'badge-info';
			case 'archived': return 'badge-ghost';
			default: return 'badge-ghost';
		}
	}

	function formatTimestamp(iso: string): string {
		return new Date(iso).toLocaleDateString([], {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}

	function formatDateShort(iso: string): string {
		return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			if (selectedProject || isCreating) {
				e.preventDefault();
			}
		}
	}

	// Project drag-drop handlers
	function handleProjectDragStart(e: DragEvent, project: ProjectResponse) {
		const card = e.currentTarget as HTMLElement;
		if (e.dataTransfer) {
			e.dataTransfer.setData('application/project-id', project.id);
			e.dataTransfer.effectAllowed = 'move';

			const width = card.offsetWidth;
			const height = card.offsetHeight;
			const rect = card.getBoundingClientRect();

			// Clone for drag image
			const clone = card.cloneNode(true) as HTMLElement;
			clone.style.position = 'absolute';
			clone.style.top = '-9999px';
			clone.style.left = '-9999px';
			clone.style.width = width + 'px';
			document.body.appendChild(clone);
			e.dataTransfer.setDragImage(clone, e.clientX - rect.left, e.clientY - rect.top);
			requestAnimationFrame(() => clone.remove());

			requestAnimationFrame(() => {
				draggingProjectId = project.id;
				draggedProjectWidth = width;
				draggedProjectHeight = height;
			});
		}
	}

	function handleProjectDragEnd() {
		draggingProjectId = null;
		projectDragOverIndex = null;
	}

	function handleGridDragOver(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/project-id')) return;
		clearTimeout(gridDragLeaveTimer);
		e.preventDefault();
		e.dataTransfer.dropEffect = 'move';

		const grid = e.currentTarget as HTMLElement;
		const cards = Array.from(grid.querySelectorAll('[data-project-id]')) as HTMLElement[];

		// Use 75% threshold - easier to trigger insertion point
		for (let i = 0; i < cards.length; i++) {
			const card = cards[i];
			if (card.dataset.projectId === draggingProjectId) continue;
			const rect = card.getBoundingClientRect();
			const threshold = rect.left + rect.width * 0.85;
			if (e.clientX < threshold) {
				// Find the index in filteredProjects
				const proj = filteredProjects.find(p => p.id === card.dataset.projectId);
				if (proj) {
					projectDragOverIndex = filteredProjects.indexOf(proj);
				}
				return;
			}
		}
		// Past all cards - drop at end
		projectDragOverIndex = filteredProjects.length;
	}

	function handleGridDragLeave(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/project-id')) return;
		clearTimeout(gridDragLeaveTimer);
		gridDragLeaveTimer = setTimeout(() => {
			projectDragOverIndex = null;
		}, 50);
	}

	async function handleGridDrop(e: DragEvent) {
		if (!e.dataTransfer?.types.includes('application/project-id')) return;
		e.preventDefault();

		const draggedId = e.dataTransfer.getData('application/project-id');
		const dropIdx = projectDragOverIndex;
		clearTimeout(gridDragLeaveTimer);
		projectDragOverIndex = null;
		draggingProjectId = null;

		if (!draggedId || dropIdx === null) return;

		// Build new order: all projects sorted by position, then move dragged to new position
		const sorted = [...projects].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
		const draggedIndex = sorted.findIndex(p => p.id === draggedId);
		if (draggedIndex === -1) return;

		const [dragged] = sorted.splice(draggedIndex, 1);
		// Adjust drop index if we removed from before it
		const adjustedIdx = dropIdx > draggedIndex ? dropIdx - 1 : dropIdx;
		sorted.splice(adjustedIdx, 0, dragged);

		// Update positions locally
		projects = sorted.map((p, i) => ({ ...p, position: i }));

		// Save to backend
		try {
			await api.put<ProjectList>('/api/projects/reorder', {
				project_ids: sorted.map(p => p.id)
			});
		} catch (e) {
			console.error('Failed to reorder projects', e);
			toast.error('Failed to reorder projects');
			loadProjects(); // Reload to restore correct order
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="absolute inset-0 flex overflow-hidden">
	<!-- Main content -->
	<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
		<!-- Header toolbar -->
		<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
			<div class="flex items-center gap-1 md:gap-2 flex-1 overflow-x-auto">
				{#each statusFilters as filter}
					<button
						class="btn btn-ghost btn-xs md:btn-sm shrink-0 {statusFilter === filter ? 'btn-active' : ''}"
						onclick={() => (statusFilter = filter)}
					>
						{filter === 'all' ? 'All' : filter.charAt(0).toUpperCase() + filter.slice(1)}
						{#if filter !== 'all'}
							<span class="badge badge-xs badge-ghost hidden md:inline-flex">
								{projects.filter((p) => p.status === filter).length}
							</span>
						{/if}
					</button>
				{/each}
			</div>
			<button
				class="btn btn-sm shrink-0 {viewMode === 'timeline' ? 'btn-primary' : 'btn-ghost'}"
				onclick={() => {
					viewMode = viewMode === 'timeline' ? 'grid' : 'timeline';
					const url = new URL(window.location.href);
					if (viewMode === 'timeline') url.searchParams.set('view', 'timeline');
					else url.searchParams.delete('view');
					goto(url.pathname + url.search, { replaceState: true });
				}}
				title={viewMode === 'timeline' ? 'Grid view' : 'Timeline view'}
			>
				<GanttChart size={14} />
				<span class="hidden sm:inline text-xs">Timeline</span>
			</button>
			<button class="btn btn-primary btn-sm shrink-0" onclick={openCreateSidebar}>
				<Plus size={16} />
				<span class="hidden md:inline">New Project</span>
			</button>
		</div>

		<!-- Scrollable content -->
		<div class="flex-1 overflow-y-auto {viewMode === 'timeline' ? 'pb-20 md:pb-4' : 'p-4 pb-20 md:pb-4'}">
			{#if loading}
				<div class="flex items-center justify-center py-20">
					<span class="loading loading-spinner loading-lg"></span>
				</div>
			{:else if viewMode === 'timeline'}
				{#if filteredProjects.length > 0}
					<ProjectTimeline projects={filteredProjects} />
				{:else if projects.length > 0}
					<div class="text-center py-20">
						<p class="text-base-content/40">No {statusFilter} projects</p>
					</div>
				{:else}
					<div class="text-center py-20">
						<FolderKanban size={40} class="mx-auto text-base-content/20 mb-3" />
						<p class="text-base-content/40 mb-4">No projects yet</p>
						<button class="btn btn-primary btn-sm" onclick={openCreateSidebar}>
							<Plus size={16} />
							Create your first project
						</button>
					</div>
				{/if}
			{:else if filteredProjects.length > 0}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="grid grid-cols-2 gap-3 md:grid-cols-[repeat(auto-fill,180px)]"
					ondragover={handleGridDragOver}
					ondragleave={handleGridDragLeave}
					ondrop={handleGridDrop}
				>
					{#each filteredProjects as project, i (project.id)}
						{#if projectDragOverIndex === i && draggingProjectId !== project.id}
							<div
								class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg aspect-square"
								style="width: {draggedProjectWidth}px; height: {draggedProjectHeight}px;"
							></div>
						{/if}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							data-project-id={project.id}
							draggable="true"
							ondragstart={(e) => handleProjectDragStart(e, project)}
							ondragend={handleProjectDragEnd}
							class="card bg-base-100 border border-base-300 text-left transition-all aspect-square cursor-pointer
								{selectedProjectId === project.id
									? 'bg-primary/5'
									: 'hover:border-base-content/30'}"
							style={draggingProjectId === project.id ? 'display: none;' : ''}
							onclick={() => selectProject(project.id)}
							role="button"
							tabindex="0"
							onkeydown={(e) => e.key === 'Enter' && selectProject(project.id)}
						>
							<div class="card-body p-4 flex flex-col justify-between h-full">
								<div class="flex-1">
									<div class="flex items-start gap-2">
										<div class="shrink-0 mt-0.5" style:color={project.color || '#6b7280'}>
											<ProjectIcon name={project.icon || 'folder-kanban'} size={18} />
										</div>
										<h3 class="font-semibold text-sm line-clamp-2 flex-1 min-w-0">{project.name}</h3>
										<span class="shrink-0 text-base-content/20 hover:text-base-content/40 cursor-grab hidden md:inline">
											<GripVertical size={14} />
										</span>
									</div>
									{#if project.description}
										<p class="text-xs text-base-content/50 line-clamp-3 md:line-clamp-5 mt-2">{project.description}</p>
									{/if}
								</div>
								<div class="flex items-center justify-between mt-auto pt-3">
									<span class="badge badge-xs {statusBadge(project.status)}">{project.status}</span>
									<div class="flex items-center gap-3 text-xs text-base-content/50">
										<span class="flex items-center gap-1">
											<CheckSquare size={11} />
											{project.task_count}
										</span>
										<span class="flex items-center gap-0.5">
											<FolderKanban size={11} />
											{project.milestones.length}
										</span>
									</div>
								</div>
							</div>
						</div>
					{/each}
					{#if projectDragOverIndex === filteredProjects.length}
						<div
							class="bg-primary/10 border-2 border-dashed border-primary/40 rounded-lg aspect-square"
							style="width: {draggedProjectWidth}px; height: {draggedProjectHeight}px;"
						></div>
					{/if}
				</div>
			{:else if projects.length > 0}
				<div class="text-center py-20">
					<p class="text-base-content/40">No {statusFilter} projects</p>
				</div>
			{:else}
				<div class="text-center py-20">
					<FolderKanban size={40} class="mx-auto text-base-content/20 mb-3" />
					<p class="text-base-content/40 mb-4">No projects yet</p>
					<button class="btn btn-primary btn-sm" onclick={openCreateSidebar}>
						<Plus size={16} />
						Create your first project
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- Right sidebar: project settings / new project (hidden in timeline mode) -->
	{#if (selectedProject || isCreating) && viewMode === 'grid'}
		<aside class="
			fixed inset-0 z-50 bg-base-100 flex flex-col overflow-hidden
			md:relative md:inset-auto md:z-auto md:w-80 lg:w-96 md:shrink-0 md:border-l md:border-base-300
		">
			<!-- Sidebar header -->
			<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
				<button class="btn btn-ghost btn-sm btn-square md:hidden" onclick={closeSidebar} title="Back">
					<ArrowLeft size={18} />
				</button>
				{#if isCreating}
					<h2 class="flex-1 font-semibold text-sm">New Project</h2>
				{:else}
					<input
						type="text"
						bind:value={editName}
						placeholder="Project name"
						class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 text-sm truncate"
					/>
					<button
						class="btn btn-ghost btn-sm btn-square"
						onclick={() => handleSave()}
						disabled={saving}
						title="Save"
					>
						{#if saveStatus === 'saving'}
							<span class="loading loading-spinner loading-xs"></span>
						{:else if saveStatus === 'saved'}
							<Check size={16} class="text-success" />
						{:else if saveStatus === 'error'}
							<Save size={16} class="text-error" />
						{:else}
							<Save size={16} />
						{/if}
					</button>
					<button
						class="btn btn-ghost btn-sm btn-square text-error"
						onclick={handleDeleteProject}
						title="Delete project"
					>
						<Trash2 size={16} />
					</button>
				{/if}
				<button class="btn btn-ghost btn-sm btn-square hidden md:flex" onclick={closeSidebar} title="Close">
					<X size={16} />
				</button>
			</div>

			<!-- Sidebar body -->
			<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
				{#if isCreating}
					<!-- New project form -->
					<Input placeholder="Project name" bind:value={newName} />
					<Input placeholder="Project ID (auto-generated from name)" bind:value={newId} />
					<textarea
						class="textarea textarea-bordered w-full text-sm"
						rows="3"
						placeholder="Description (optional)"
						bind:value={newDescription}
					></textarea>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<p class="text-xs text-base-content/60 mb-1">Color</p>
							<div class="flex items-center gap-1.5 flex-wrap">
								<input type="color" class="w-7 h-7 rounded cursor-pointer border-0" bind:value={newColor} />
								{#each colorPresets as color}
									<button
										class="w-4 h-4 rounded-full border-2 transition-transform {newColor === color ? 'border-base-content scale-110' : 'border-transparent'}"
										style:background-color={color}
										onclick={() => (newColor = color)}
										aria-label="Select {color}"
									></button>
								{/each}
							</div>
						</div>
						<div>
							<p class="text-xs text-base-content/60 mb-1">Icon</p>
							<IconPicker bind:value={newIcon} />
						</div>
					</div>
					<Button variant="primary" loading={creating} onclick={handleCreate}>
						Create Project
					</Button>
				{:else if sidebarLoading}
					<div class="flex items-center justify-center py-10">
						<span class="loading loading-spinner loading-md"></span>
					</div>
				{:else}
					<!-- Open Board link -->
					<a
						href="{base}/tasks/{selectedProjectId}"
						class="btn btn-sm w-full gap-1.5 bg-base-100 border hover:bg-base-200"
					>
						Open Board
						<ExternalLink size={14} />
					</a>

					<!-- Description -->
					<textarea
						class="textarea textarea-bordered w-full text-sm"
						rows="3"
						placeholder="Description..."
						bind:value={editDescription}
					></textarea>

					<!-- Status + Color + Icon -->
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
							<div class="flex items-center gap-1.5 flex-wrap">
								<input type="color" class="w-7 h-7 rounded cursor-pointer border-0" bind:value={editColor} />
								{#each colorPresets as color}
									<button
										class="w-4 h-4 rounded-full border-2 transition-transform {editColor === color ? 'border-base-content scale-110' : 'border-transparent'}"
										style:background-color={color}
										onclick={() => (editColor = color)}
										aria-label="Select {color}"
									></button>
								{/each}
							</div>
						</div>
					</div>
					<div>
						<p class="text-xs text-base-content/60 mb-1">Icon</p>
						<IconPicker bind:value={editIcon} />
					</div>

					<!-- Task progress -->
					<div>
						<div class="flex items-center justify-between mb-1">
							<p class="text-xs text-base-content/60">Task completions</p>
							<span class="text-xs text-base-content/50 tabular-nums">{sidebarTasks.done}/{sidebarTasks.total}</span>
						</div>
						{#if sidebarTasks.total > 0}
							<div class="flex items-center gap-2">
								<div class="flex-1 h-2 bg-base-300 rounded-full overflow-hidden">
									<div
										class="h-full rounded-full transition-all {completionPct === 100 ? 'bg-success' : 'bg-primary'}"
										style:width="{completionPct}%"
									></div>
								</div>
								<span class="text-xs tabular-nums text-base-content/50">{completionPct}%</span>
							</div>
						{:else}
							<p class="text-xs text-base-content/40">No tasks yet</p>
						{/if}
					</div>

					<!-- Notes -->
					{#if sidebarNotes.length > 0}
						<div>
							<p class="text-xs text-base-content/60 mb-1">Linked Notes</p>
							<div class="flex flex-col divide-y divide-base-200">
								{#each sidebarNotes as note}
									<a
										href="{base}/notes/{note.id}"
										class="flex items-center gap-2 py-1.5 text-xs hover:bg-base-200/50 transition-colors rounded px-1"
									>
										<span class="flex-1 min-w-0 truncate">{note.title}</span>
										<span class="text-base-content/40 shrink-0">{formatDateShort(note.updated_at)}</span>
									</a>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Timestamps -->
					{#if selectedProject}
						<div class="flex flex-col gap-1 text-xs text-base-content/40 pt-2 border-t border-base-200">
							<span class="flex items-center gap-1">
								<Clock size={11} />
								Created {formatTimestamp(selectedProject.created_at)}
							</span>
							{#if selectedProject.updated_at !== selectedProject.created_at}
								<span class="ml-4">Updated {formatTimestamp(selectedProject.updated_at)}</span>
							{/if}
						</div>
					{/if}

				{/if}
			</div>
		</aside>
	{/if}
</div>
