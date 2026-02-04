<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { TaskCreate, TaskResponse, MilestoneResponse, ChecklistItemCreate, ProjectResponse } from '$lib/types';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Plus, Trash2, Square, CheckSquare, StickyNote, CalendarDays } from 'lucide-svelte';

	interface Props {
		open: boolean;
		projectId: string;
		milestoneId?: string | null;
		milestones?: MilestoneResponse[];
		projects?: ProjectResponse[];
		initialNoteId?: string | null;
		calendarEventId?: string | null;
		onclose?: () => void;
		oncreated?: (task: TaskResponse) => void;
	}

	let { open = $bindable(false), projectId, milestoneId = null, milestones = [], projects = [], initialNoteId = null, calendarEventId = null, onclose, oncreated }: Props = $props();

	let title = $state('');
	let description = $state('');
	let priority = $state('medium');
	let dueDate = $state('');
	let selectedProjectId = $state('');
	let selectedMilestoneId = $state<string | null>(null);
	let checklist = $state<ChecklistItemCreate[]>([]);
	let newCheckItem = $state('');
	let creating = $state(false);

	let selectedProject = $derived(projects.find((p) => p.id === selectedProjectId));
	let availableMilestones = $derived(
		projects.length > 0 ? (selectedProject?.milestones ?? []) : milestones
	);

	$effect(() => {
		if (open) {
			title = '';
			description = '';
			priority = 'medium';
			dueDate = '';
			selectedProjectId = projectId;
			selectedMilestoneId = milestoneId ?? null;
			checklist = [];
			newCheckItem = '';
		}
	});

	async function handleCreate() {
		if (!title.trim()) return;
		creating = true;
		try {
			const data: TaskCreate = {
				title: title.trim(),
				project_id: selectedProjectId || projectId,
				milestone_id: selectedMilestoneId
			};
			if (description.trim()) data.description = description.trim();
			if (priority !== 'medium') data.priority = priority;
			if (dueDate) data.due_date = new Date(dueDate).toISOString();
			if (checklist.length > 0) data.checklist = checklist;
			if (initialNoteId) data.note_ids = [initialNoteId];
			if (calendarEventId) data.calendar_event_id = calendarEventId;

			const task = await api.post<TaskResponse>('/api/tasks', data);
			oncreated?.(task);
			open = false;
		} catch (e) {
			console.error('Failed to create task', e);
			toast.error('Failed to create task');
		} finally {
			creating = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
			e.preventDefault();
			handleCreate();
		}
	}

	function addCheckItem() {
		if (!newCheckItem.trim()) return;
		checklist = [...checklist, { text: newCheckItem.trim(), is_checked: false }];
		newCheckItem = '';
	}

	function removeCheckItem(index: number) {
		checklist = checklist.filter((_, i) => i !== index);
	}

	function toggleCheckItem(index: number) {
		checklist = checklist.map((c, i) =>
			i === index ? { ...c, is_checked: !c.is_checked } : c
		);
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div onkeydown={handleKeydown}>
<Modal bind:open title="New Task" size="wide" {onclose}>
	<div class="flex flex-col gap-4">
		<Input placeholder="Task title" bind:value={title} autofocus />

		<textarea
			class="textarea textarea-bordered w-full text-sm"
			rows="3"
			placeholder="Description (optional)..."
			bind:value={description}
		></textarea>

		{#if projects.length > 0}
			<div>
				<p class="text-xs text-base-content/60 mb-1">Project</p>
				<select class="select select-bordered select-sm w-full" bind:value={selectedProjectId} onchange={() => (selectedMilestoneId = null)}>
					{#each projects as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
			</div>
		{/if}

		<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
			{#if availableMilestones.length > 0}
				<div>
					<p class="text-xs text-base-content/60 mb-1">Milestone</p>
					<select class="select select-bordered select-sm w-full" bind:value={selectedMilestoneId}>
						<option value={null}>None</option>
						{#each availableMilestones as ms}
							<option value={ms.id}>{ms.name}</option>
						{/each}
					</select>
				</div>
			{/if}
		</div>

		<!-- Checklist -->
		<div>
			<p class="text-xs text-base-content/60 mb-1">Checklist</p>
			{#each checklist as item, i}
				<div class="flex items-center gap-2 py-1 group">
					<button class="btn btn-ghost btn-xs btn-square shrink-0" onclick={() => toggleCheckItem(i)}>
						{#if item.is_checked}
							<CheckSquare size={16} class="text-success" />
						{:else}
							<Square size={16} />
						{/if}
					</button>
					<span class="flex-1 text-sm {item.is_checked ? 'line-through text-base-content/40' : ''}">
						{item.text}
					</span>
					<button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onclick={() => removeCheckItem(i)}>
						<Trash2 size={14} />
					</button>
				</div>
			{/each}
			<div class="flex items-center gap-1 mt-1">
				<input
					type="text"
					class="input input-bordered input-sm flex-1"
					placeholder="Add checklist item..."
					bind:value={newCheckItem}
					onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCheckItem(); } }}
				/>
				<button class="btn btn-ghost btn-sm" onclick={addCheckItem} disabled={!newCheckItem.trim()}>
					<Plus size={14} />
				</button>
			</div>
		</div>

		{#if initialNoteId || calendarEventId}
			<div class="flex items-center gap-3 text-xs text-base-content/60">
				{#if initialNoteId}
					<span class="flex items-center gap-1"><StickyNote size={12} /> Linked to note</span>
				{/if}
				{#if calendarEventId}
					<span class="flex items-center gap-1"><CalendarDays size={12} /> Linked to event</span>
				{/if}
			</div>
		{/if}

		<div class="flex items-center gap-2 mt-1">
			<Button variant="primary" loading={creating} onclick={handleCreate}>
				Create Task
			</Button>
			<span class="text-xs text-base-content/40">
				{navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}+Enter
			</span>
		</div>
	</div>
</Modal>
</div>
