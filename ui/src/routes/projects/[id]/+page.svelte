<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type {
		ProjectResponse,
		ProjectUpdate,
		TaskResponse,
		TaskList,
		NoteListItem,
		NoteList
	} from '$lib/types';
	import TaskCard from '$lib/components/tasks/TaskCard.svelte';
	import { ArrowLeft, Trash2, ExternalLink, Plus, Save, Check, Clock } from 'lucide-svelte';

	let project = $state<ProjectResponse | null>(null);
	let tasks = $state<TaskResponse[]>([]);
	let notes = $state<NoteListItem[]>([]);
	let loading = $state(true);

	// Sidebar edit state
	let editName = $state('');
	let editDescription = $state('');
	let editColor = $state('');
	let editStatus = $state('active');

	// Auto-save state
	let loaded = $state(false);
	let saving = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;
	let lastSavedSnapshot = $state('');
	let autoSaveTimer: ReturnType<typeof setTimeout>;

	let projectId = $derived(page.params.id ?? '');
	let completedCount = $derived(tasks.filter((t) => t.status === 'done').length);
	let completionPct = $derived(tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0);

	const statusBadgeClass: Record<string, string> = {
		active: 'badge-success',
		paused: 'badge-warning',
		completed: 'badge-info',
		archived: 'badge-ghost'
	};

	// Milestone stats
	let milestoneStats = $derived.by(() => {
		if (!project) return [];
		return [...project.milestones]
			.sort((a, b) => a.position - b.position)
			.map((m) => {
				const mTasks = tasks.filter((t) => t.milestone_id === m.id);
				const done = mTasks.filter((t) => t.status === 'done').length;
				return { ...m, done, total: mTasks.length, pct: mTasks.length > 0 ? Math.round((done / mTasks.length) * 100) : 0 };
			});
	});

	// Recent tasks: last 5 by updated_at
	let recentTasks = $derived(
		[...tasks].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 5)
	);

	function currentSnapshot(): string {
		return JSON.stringify({ editName, editDescription, editColor, editStatus });
	}

	async function load() {
		loading = true;
		loaded = false;
		try {
			const [p, t] = await Promise.all([
				api.get<ProjectResponse>(`/api/projects/${projectId}`),
				api.get<TaskList>(`/api/tasks?project_id=${projectId}&limit=200`)
			]);
			project = p;
			tasks = t.tasks;
			editName = p.name;
			editDescription = p.description || '';
			editColor = p.color || '#3b82f6';
			editStatus = p.status;
			saveStatus = 'idle';
			showSavedText = false;
			lastSavedSnapshot = currentSnapshot();
			loaded = true;
			// Notes fetch is non-critical
			try {
				const n = await api.get<NoteList>(`/api/notes?project_id=${projectId}`);
				notes = n.notes;
			} catch {
				notes = [];
			}
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

	async function handleSave() {
		if (!project || !editName.trim()) return;
		saving = true;
		saveStatus = 'saving';
		try {
			const updated = await api.put<ProjectResponse>(`/api/projects/${projectId}`, {
				name: editName.trim(),
				description: editDescription.trim(),
				color: editColor,
				status: editStatus
			} as ProjectUpdate);
			project = { ...project, ...updated };
			lastSavedSnapshot = currentSnapshot();
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => {
				showSavedText = false;
				saveStatus = 'idle';
			}, 2000);
		} catch {
			saveStatus = 'error';
			toasts.error('Failed to update project');
		} finally {
			saving = false;
		}
	}

	// Auto-save: debounce 500ms after any change
	$effect(() => {
		if (!loaded) return;
		const snap = currentSnapshot();
		if (snap === lastSavedSnapshot) return;

		saveStatus = 'idle';
		showSavedText = false;
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => handleSave(), 500);
		return () => clearTimeout(autoSaveTimer);
	});

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
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if project}
	<div class="absolute inset-0 flex overflow-hidden">
		<!-- Left: main content -->
		<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
			<!-- Header bar -->
			<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
				<a href="/projects" class="btn btn-ghost btn-sm btn-square">
					<ArrowLeft size={18} />
				</a>
				{#if project.color}
					<div class="w-2.5 h-2.5 rounded-full shrink-0" style:background-color={project.color}></div>
				{/if}
				<input
					type="text"
					bind:value={editName}
					placeholder="Project name"
					class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 truncate"
				/>
				<span class="badge badge-xs {statusBadgeClass[project.status] ?? 'badge-ghost'}">{project.status}</span>
				<span class="text-xs text-base-content/50 tabular-nums shrink-0">{completedCount}/{tasks.length} tasks</span>
			</div>

			<!-- Scrollable content -->
			<div class="flex-1 overflow-y-auto">
				<div class="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-6">

					<!-- Task progress section -->
					<div>
						<div class="flex items-center justify-between mb-2">
							<h3 class="text-sm font-semibold text-base-content/70">Task Progress</h3>
							<a href="/tasks?project={projectId}" class="link link-primary text-xs flex items-center gap-1">
								Open in Kanban <ExternalLink size={12} />
							</a>
						</div>
						{#if tasks.length > 0}
							<div class="flex items-center gap-3">
								<div class="flex-1 h-2.5 bg-base-300 rounded-full overflow-hidden">
									<div
										class="h-full rounded-full transition-all {completionPct === 100 ? 'bg-success' : 'bg-primary'}"
										style:width="{completionPct}%"
									></div>
								</div>
								<span class="text-sm font-medium tabular-nums text-base-content/60">{completionPct}%</span>
							</div>
							<p class="text-xs text-base-content/40 mt-1">{completedCount} of {tasks.length} tasks completed</p>
						{:else}
							<p class="text-xs text-base-content/40">No tasks yet</p>
						{/if}
					</div>

					<!-- Milestones section -->
					{#if milestoneStats.length > 0}
						<div>
							<h3 class="text-sm font-semibold text-base-content/70 mb-2">Milestones</h3>
							<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
								{#each milestoneStats as ms}
									<div class="card bg-base-100 shadow-sm border border-base-300">
										<div class="card-body p-3 gap-1.5">
											<div class="flex items-center justify-between">
												<span class="text-sm font-medium truncate">{ms.name}</span>
												<span class="text-xs text-base-content/50 tabular-nums shrink-0 ml-2">{ms.done}/{ms.total}</span>
											</div>
											<div class="h-1.5 bg-base-300 rounded-full overflow-hidden">
												<div
													class="h-full rounded-full transition-all {ms.pct === 100 ? 'bg-success' : 'bg-primary'}"
													style:width="{ms.pct}%"
												></div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Notes section -->
					<div>
						<div class="flex items-center justify-between mb-2">
							<h3 class="text-sm font-semibold text-base-content/70">Notes</h3>
							<a href="/notes/new?project={projectId}" class="btn btn-ghost btn-xs gap-1">
								<Plus size={14} />
								New Note
							</a>
						</div>
						{#if notes.length > 0}
							<div class="card bg-base-100 shadow-sm border border-base-300 divide-y divide-base-300">
								{#each notes as note}
									<a
										href="/notes/{note.id}"
										class="flex items-center gap-3 px-3 py-2.5 hover:bg-base-200/50 transition-colors first:rounded-t-2xl last:rounded-b-2xl"
									>
										<span class="flex-1 min-w-0 text-sm truncate">{note.title}</span>
										{#if note.tags.length > 0}
											<div class="flex gap-1 shrink-0">
												{#each note.tags.slice(0, 2) as tag}
													<span class="badge badge-xs badge-ghost">{tag}</span>
												{/each}
											</div>
										{/if}
										<span class="text-xs text-base-content/40 shrink-0">{formatDateShort(note.updated_at)}</span>
									</a>
								{/each}
							</div>
						{:else}
							<p class="text-xs text-base-content/40">No notes linked to this project</p>
						{/if}
					</div>

					<!-- Recent tasks section -->
					{#if recentTasks.length > 0}
						<div>
							<h3 class="text-sm font-semibold text-base-content/70 mb-2">Recent Tasks</h3>
							<div class="flex flex-col gap-2">
								{#each recentTasks as task}
									<TaskCard {task} compact />
								{/each}
							</div>
						</div>
					{/if}

				</div>
			</div>
		</div>

		<!-- Right: project settings sidebar -->
		<aside class="w-80 shrink-0 border-l border-base-300 bg-base-100 flex flex-col overflow-hidden">
			<!-- Sidebar header -->
			<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
				<span class="text-sm font-medium text-base-content/70 flex-1">Settings</span>
				<button
					class="btn btn-ghost btn-sm"
					onclick={() => handleSave()}
					disabled={saving}
					title="Save"
				>
					{#if saveStatus === 'saving'}
						<span class="loading loading-spinner loading-xs"></span>
					{:else if saveStatus === 'saved'}
						<Check size={16} class="text-success" />
						{#if showSavedText}
							<span class="text-xs">Saved!</span>
						{/if}
					{:else if saveStatus === 'error'}
						<Save size={16} class="text-error" />
					{:else}
						<Save size={16} />
					{/if}
				</button>
				<button class="btn btn-ghost btn-sm text-error" onclick={handleDeleteProject} title="Delete project">
					<Trash2 size={16} />
				</button>
			</div>

			<!-- Sidebar body -->
			<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
				<!-- Description -->
				<textarea
					class="textarea textarea-bordered w-full text-sm"
					rows="3"
					placeholder="Description..."
					bind:value={editDescription}
				></textarea>

				<!-- Fields grid -->
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

				<!-- Timestamps -->
				<div class="flex flex-col gap-1 text-xs text-base-content/40 pt-2 border-t border-base-200">
					<span class="flex items-center gap-1">
						<Clock size={11} />
						Created {formatTimestamp(project.created_at)}
					</span>
					{#if project.updated_at !== project.created_at}
						<span class="ml-4">Updated {formatTimestamp(project.updated_at)}</span>
					{/if}
				</div>
			</div>
		</aside>
	</div>
{/if}
