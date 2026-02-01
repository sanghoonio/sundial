<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { ProjectResponse, ProjectList, ProjectCreate, ProjectUpdate } from '$lib/types';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Plus, FolderKanban, CheckSquare } from 'lucide-svelte';

	let projects = $state<ProjectResponse[]>([]);
	let loading = $state(true);

	let statusFilter = $state('all');

	let createOpen = $state(false);
	let newId = $state('');
	let newName = $state('');
	let newDescription = $state('');
	let newColor = $state('#3b82f6');
	let creating = $state(false);

	const statusFilters = ['all', 'active', 'paused', 'completed', 'archived'] as const;

	let filteredProjects = $derived.by(() => {
		if (statusFilter === 'all') return projects;
		return projects.filter((p) => p.status === statusFilter);
	});

	async function loadProjects() {
		loading = true;
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
		} catch {
			toasts.error('Failed to load projects');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadProjects();
	});

	function openCreateModal() {
		newId = '';
		newName = '';
		newDescription = '';
		newColor = '#3b82f6';
		createOpen = true;
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
				color: newColor
			};
			const created = await api.post<ProjectResponse>('/api/projects', data);
			projects = [...projects, created];
			createOpen = false;
			toasts.success('Project created');
		} catch {
			toasts.error('Failed to create project');
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
		} catch {
			projects = projects.map((p) =>
				p.id === project.id ? { ...p, status: oldStatus } : p
			);
			toasts.error('Failed to update status');
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
</script>

<div class="absolute inset-0 flex flex-col overflow-hidden">
	<!-- Header toolbar -->
	<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
		<div class="flex items-center gap-1.5 flex-1 flex-wrap">
			{#each statusFilters as filter}
				<button
					class="btn btn-xs {statusFilter === filter ? 'btn-primary' : 'btn-ghost'}"
					onclick={() => (statusFilter = filter)}
				>
					{filter === 'all' ? 'All' : filter.charAt(0).toUpperCase() + filter.slice(1)}
					{#if filter !== 'all'}
						<span class="badge badge-xs {statusFilter === filter ? 'badge-primary-content' : 'badge-ghost'}">
							{projects.filter((p) => p.status === filter).length}
						</span>
					{/if}
				</button>
			{/each}
		</div>
		<button class="btn btn-primary btn-sm" onclick={openCreateModal}>
			<Plus size={16} />
			New Project
		</button>
	</div>

	<!-- Scrollable content -->
	<div class="flex-1 overflow-y-auto p-4">
		{#if loading}
			<div class="flex items-center justify-center py-20">
				<span class="loading loading-spinner loading-lg"></span>
			</div>
		{:else if filteredProjects.length > 0}
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each filteredProjects as project (project.id)}
					<a href="/projects/{project.id}" class="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow">
						<div class="card-body p-4 gap-2">
							<div class="flex items-center gap-2">
								{#if project.color}
									<div class="w-2.5 h-2.5 rounded-full shrink-0" style:background-color={project.color}></div>
								{/if}
								<h3 class="font-semibold text-sm truncate flex-1 min-w-0">{project.name}</h3>
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<!-- svelte-ignore a11y_click_events_have_key_events -->
								<div onclick={(e) => e.preventDefault()}>
									<select
										class="select select-bordered select-xs min-h-0 h-5 leading-none text-xs {statusBadge(project.status)}"
										value={project.status}
										onchange={(e) => handleStatusChange(e, project)}
									>
										<option value="active">Active</option>
										<option value="paused">Paused</option>
										<option value="completed">Completed</option>
										<option value="archived">Archived</option>
									</select>
								</div>
							</div>
							{#if project.description}
								<p class="text-xs text-base-content/60 line-clamp-2">{project.description}</p>
							{/if}
							<div class="flex items-center gap-4 text-xs text-base-content/50 pt-1">
								<span class="flex items-center gap-1">
									<CheckSquare size={12} />
									{project.task_count} tasks
								</span>
								<span class="flex items-center gap-1">
									<FolderKanban size={12} />
									{project.milestones.length} milestones
								</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{:else if projects.length > 0}
			<div class="text-center py-20">
				<p class="text-base-content/40">No {statusFilter} projects</p>
			</div>
		{:else}
			<div class="text-center py-20">
				<FolderKanban size={40} class="mx-auto text-base-content/20 mb-3" />
				<p class="text-base-content/40 mb-4">No projects yet</p>
				<button class="btn btn-primary btn-sm" onclick={openCreateModal}>
					<Plus size={16} />
					Create your first project
				</button>
			</div>
		{/if}
	</div>
</div>

<Modal bind:open={createOpen} title="New Project" onclose={() => (createOpen = false)}>
	<div class="flex flex-col gap-3">
		<Input placeholder="Project name" bind:value={newName} />
		<Input placeholder="Project ID (auto-generated from name)" bind:value={newId} />
		<div>
			<textarea
				class="textarea textarea-bordered w-full text-sm"
				rows="3"
				placeholder="Description (optional)"
				bind:value={newDescription}
			></textarea>
		</div>
		<div>
			<p class="text-xs text-base-content/60 mb-1">Color</p>
			<div class="flex items-center gap-3">
				<input type="color" class="w-8 h-8 rounded cursor-pointer border-0" bind:value={newColor} />
				{#each ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#6b7280'] as color}
					<button
						class="w-6 h-6 rounded-full border-2 transition-transform {newColor === color ? 'border-base-content scale-110' : 'border-transparent'}"
						style:background-color={color}
						onclick={() => (newColor = color)}
						title={color}
					></button>
				{/each}
			</div>
		</div>
		<Button variant="primary" loading={creating} onclick={handleCreate}>
			Create Project
		</Button>
	</div>
</Modal>
