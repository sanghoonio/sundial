<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { ProjectResponse, ProjectList, ProjectCreate } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Plus, FolderKanban, CheckSquare } from 'lucide-svelte';

	let projects = $state<ProjectResponse[]>([]);
	let loading = $state(true);

	let createOpen = $state(false);
	let newId = $state('');
	let newName = $state('');
	let newDescription = $state('');
	let creating = $state(false);

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
				description: newDescription.trim() || undefined
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

	function statusBadge(status: string): string {
		switch (status) {
			case 'active': return 'badge-success';
			case 'completed': return 'badge-info';
			case 'archived': return 'badge-ghost';
			default: return 'badge-ghost';
		}
	}
</script>

<div class="flex items-center justify-end mb-6">
	<button class="btn btn-primary btn-sm" onclick={openCreateModal}>
		<Plus size={16} />
		New Project
	</button>
</div>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if projects.length > 0}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each projects as project (project.id)}
			<a href="/projects/{project.id}" class="block">
				<Card hoverable>
					<div class="flex items-start justify-between">
						<div class="flex items-center gap-2">
							{#if project.color}
								<div class="w-3 h-3 rounded-full" style:background-color={project.color}></div>
							{/if}
							<h3 class="font-semibold">{project.name}</h3>
						</div>
						<span class="badge badge-sm {statusBadge(project.status)}">{project.status}</span>
					</div>
					{#if project.description}
						<p class="text-sm text-base-content/60 mt-1 line-clamp-2">{project.description}</p>
					{/if}
					<div class="flex items-center gap-4 mt-3 text-xs text-base-content/50">
						<span class="flex items-center gap-1">
							<CheckSquare size={12} />
							{project.task_count} tasks
						</span>
						<span class="flex items-center gap-1">
							<FolderKanban size={12} />
							{project.milestones.length} milestones
						</span>
					</div>
				</Card>
			</a>
		{/each}
	</div>
{:else}
	<div class="text-center py-20">
		<p class="text-base-content/40 mb-4">No projects yet</p>
		<button class="btn btn-primary btn-sm" onclick={openCreateModal}>
			<Plus size={16} />
			Create your first project
		</button>
	</div>
{/if}

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
		<Button variant="primary" loading={creating} onclick={handleCreate}>
			Create Project
		</Button>
	</div>
</Modal>
