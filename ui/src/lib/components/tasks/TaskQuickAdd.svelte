<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { TaskCreate, TaskResponse } from '$lib/types';
	import { Plus } from 'lucide-svelte';

	interface Props {
		projectId: string;
		milestoneId: string | null;
		oncreated?: (task: TaskResponse) => void;
	}

	let { projectId, milestoneId, oncreated }: Props = $props();

	let title = $state('');
	let adding = $state(false);
	let showForm = $state(false);

	async function handleAdd() {
		if (!title.trim()) return;
		adding = true;
		try {
			const task = await api.post<TaskResponse>('/api/tasks', {
				title: title.trim(),
				project_id: projectId,
				milestone_id: milestoneId
			} satisfies TaskCreate);
			title = '';
			showForm = false;
			oncreated?.(task);
		} catch (e) {
			console.error('Failed to create task', e);
			toast.error('Failed to create task');
		} finally {
			adding = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleAdd();
		} else if (e.key === 'Escape') {
			showForm = false;
			title = '';
		}
	}
</script>

{#if showForm}
	<div class="flex items-center gap-1 mt-2">
		<!-- svelte-ignore a11y_autofocus -->
		<input
			type="text"
			class="input input-bordered input-sm flex-1"
			placeholder="Task title..."
			bind:value={title}
			onkeydown={handleKeydown}
			disabled={adding}
			autofocus
		/>
		<button class="btn btn-primary btn-sm" onclick={handleAdd} disabled={adding || !title.trim()}>
			{#if adding}
				<span class="loading loading-spinner loading-xs"></span>
			{:else}
				Add
			{/if}
		</button>
	</div>
{:else}
	<div class="flex items-center gap-1 mt-2">
		<button
			class="btn btn-ghost btn-sm flex-1 justify-start text-base-content/50"
			onclick={() => (showForm = true)}
		>
			<Plus size={14} />
			Add task
		</button>
	</div>
{/if}
