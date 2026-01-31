<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { TaskResponse, TaskUpdate, ChecklistItemCreate } from '$lib/types';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Trash2, Plus, Square, CheckSquare } from 'lucide-svelte';

	interface Props {
		task: TaskResponse | null;
		open: boolean;
		onclose?: () => void;
		onsaved?: (task: TaskResponse) => void;
		ondeleted?: (taskId: string) => void;
	}

	let { task, open = $bindable(false), onclose, onsaved, ondeleted }: Props = $props();

	let title = $state('');
	let description = $state('');
	let priority = $state('medium');
	let dueDate = $state('');
	let checklist = $state<ChecklistItemCreate[]>([]);
	let newCheckItem = $state('');
	let saving = $state(false);

	$effect(() => {
		if (task) {
			title = task.title;
			description = task.description;
			priority = task.priority;
			dueDate = task.due_date ? task.due_date.slice(0, 10) : '';
			checklist = task.checklist.map((c) => ({ text: c.text, is_checked: c.is_checked }));
		}
	});

	async function handleSave() {
		if (!task || !title.trim()) return;
		saving = true;
		try {
			const update: TaskUpdate = {
				title: title.trim(),
				description,
				priority,
				due_date: dueDate ? new Date(dueDate).toISOString() : null,
				checklist
			};
			const updated = await api.put<TaskResponse>(`/api/tasks/${task.id}`, update);
			toasts.success('Task updated');
			onsaved?.(updated);
			open = false;
		} catch {
			toasts.error('Failed to update task');
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!task || !confirm('Delete this task?')) return;
		try {
			await api.delete(`/api/tasks/${task.id}`);
			toasts.success('Task deleted');
			ondeleted?.(task.id);
			open = false;
		} catch {
			toasts.error('Failed to delete task');
		}
	}

	function addCheckItem() {
		if (!newCheckItem.trim()) return;
		checklist = [...checklist, { text: newCheckItem.trim(), is_checked: false }];
		newCheckItem = '';
	}

	function toggleCheckItem(index: number) {
		checklist = checklist.map((c, i) =>
			i === index ? { ...c, is_checked: !c.is_checked } : c
		);
	}

	function removeCheckItem(index: number) {
		checklist = checklist.filter((_, i) => i !== index);
	}
</script>

<Modal bind:open title="Edit Task" {onclose}>
	{#if task}
		<div class="flex flex-col gap-3">
			<Input placeholder="Task title" bind:value={title} />

			<textarea
				class="textarea textarea-bordered w-full text-sm"
				rows="3"
				placeholder="Description..."
				bind:value={description}
			></textarea>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<p class="text-xs text-base-content/60 mb-1">Priority</p>
					<select class="select select-bordered select-sm w-full" bind:value={priority}>
						<option value="low">Low</option>
						<option value="medium">Medium</option>
						<option value="high">High</option>
						<option value="urgent">Urgent</option>
					</select>
				</div>
				<div>
					<p class="text-xs text-base-content/60 mb-1">Due date</p>
					<input type="date" class="input input-bordered input-sm w-full" bind:value={dueDate} />
				</div>
			</div>

			<!-- Checklist -->
			<div>
				<p class="text-xs text-base-content/60 mb-1">Checklist</p>
				{#each checklist as item, i}
					<div class="flex items-center gap-2 py-1">
						<button class="btn btn-ghost btn-xs btn-square" onclick={() => toggleCheckItem(i)}>
							{#if item.is_checked}
								<CheckSquare size={16} class="text-success" />
							{:else}
								<Square size={16} />
							{/if}
						</button>
						<span class="flex-1 text-sm {item.is_checked ? 'line-through text-base-content/40' : ''}">
							{item.text}
						</span>
						<button class="btn btn-ghost btn-xs text-error" onclick={() => removeCheckItem(i)}>
							<Trash2 size={14} />
						</button>
					</div>
				{/each}
				<div class="flex items-center gap-1 mt-1">
					<input
						type="text"
						class="input input-bordered input-sm flex-1"
						placeholder="Add item..."
						bind:value={newCheckItem}
						onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCheckItem(); } }}
					/>
					<button class="btn btn-ghost btn-sm" onclick={addCheckItem} disabled={!newCheckItem.trim()}>
						<Plus size={14} />
					</button>
				</div>
			</div>

			<div class="flex items-center gap-2 mt-2">
				<Button variant="primary" loading={saving} onclick={handleSave}>Save</Button>
				<div class="flex-1"></div>
				<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
					<Trash2 size={16} />
					Delete
				</button>
			</div>
		</div>
	{/if}
</Modal>
