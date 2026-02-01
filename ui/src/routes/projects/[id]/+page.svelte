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
		TaskMove,
		MilestoneCreate
	} from '$lib/types';
	import KanbanBoard from '$lib/components/tasks/KanbanBoard.svelte';
	import TaskDetailModal from '$lib/components/tasks/TaskDetailModal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ArrowLeft, Settings2, Trash2, Plus } from 'lucide-svelte';

	let project = $state<ProjectResponse | null>(null);
	let tasks = $state<TaskResponse[]>([]);
	let loading = $state(true);

	let selectedTask = $state<TaskResponse | null>(null);
	let taskModalOpen = $state(false);

	let settingsOpen = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editMilestones = $state<{ id?: string; name: string; position: number }[]>([]);
	let saving = $state(false);
	let newMilestoneName = $state('');

	let projectId = $derived(page.params.id);

	async function load() {
		loading = true;
		try {
			const [p, t] = await Promise.all([
				api.get<ProjectResponse>(`/api/projects/${projectId}`),
				api.get<TaskList>(`/api/tasks?project_id=${projectId}&limit=200`)
			]);
			project = p;
			tasks = t.tasks;
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
		taskModalOpen = true;
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

	function openSettings() {
		if (!project) return;
		editName = project.name;
		editDescription = project.description || '';
		editMilestones = project.milestones.map((m) => ({
			id: m.id,
			name: m.name,
			position: m.position
		}));
		newMilestoneName = '';
		settingsOpen = true;
	}

	function addMilestone() {
		if (!newMilestoneName.trim()) return;
		editMilestones = [
			...editMilestones,
			{ name: newMilestoneName.trim(), position: editMilestones.length }
		];
		newMilestoneName = '';
	}

	function removeMilestone(index: number) {
		editMilestones = editMilestones.filter((_, i) => i !== index).map((m, i) => ({ ...m, position: i }));
	}

	async function saveSettings() {
		if (!project || !editName.trim()) return;
		saving = true;
		try {
			// Update project name/description
			const updated = await api.put<ProjectResponse>(`/api/projects/${projectId}`, {
				name: editName.trim(),
				description: editDescription.trim()
			} as ProjectUpdate);

			// Update milestones
			const milestoneData: MilestoneCreate[] = editMilestones.map((m) => ({
				name: m.name,
				position: m.position
			}));
			const withMilestones = await api.put<ProjectResponse>(
				`/api/projects/${projectId}/milestones`,
				{ milestones: milestoneData }
			);

			project = withMilestones;
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
	<div class="flex items-center gap-3 mb-4">
		<a href="/projects" class="btn btn-ghost btn-sm btn-square">
			<ArrowLeft size={18} />
		</a>
		<div class="flex-1">
			<h2 class="font-semibold">{project.name}</h2>
			{#if project.description}
				<p class="text-sm text-base-content/60">{project.description}</p>
			{/if}
		</div>
		<button class="btn btn-ghost btn-sm" onclick={openSettings}>
			<Settings2 size={16} />
		</button>
	</div>

	<div class="h-[calc(100vh-14rem)] overflow-hidden">
		<KanbanBoard
			milestones={project.milestones}
			{tasks}
			projectId={projectId}
			ontaskclick={handleTaskClick}
			ondrop={handleDrop}
			ontaskcreated={handleTaskCreated}
		/>
	</div>

	<TaskDetailModal
		task={selectedTask}
		bind:open={taskModalOpen}
		onsaved={handleTaskSaved}
		ondeleted={handleTaskDeleted}
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

			<div>
				<h4 class="text-sm font-medium mb-2">Milestones (columns)</h4>
				<div class="flex flex-col gap-1.5">
					{#each editMilestones as ms, i}
						<div class="flex items-center gap-2">
							<span class="text-sm flex-1">{ms.name}</span>
							<button class="btn btn-ghost btn-xs text-error" onclick={() => removeMilestone(i)}>
								<Trash2 size={14} />
							</button>
						</div>
					{/each}
				</div>
				<div class="flex items-center gap-2 mt-2">
					<input
						type="text"
						class="input input-bordered input-sm flex-1"
						placeholder="New milestone name"
						bind:value={newMilestoneName}
						onkeydown={(e) => e.key === 'Enter' && addMilestone()}
					/>
					<button class="btn btn-ghost btn-sm" onclick={addMilestone}>
						<Plus size={14} />
					</button>
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
