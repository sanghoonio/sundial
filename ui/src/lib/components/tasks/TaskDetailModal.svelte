<script lang="ts">
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { TaskResponse, TaskUpdate, ChecklistItemCreate, MilestoneResponse, NoteResponse, EventResponse } from '$lib/types';
	import { toLocalISOString } from '$lib/utils/calendar';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Trash2, Plus, Square, CheckSquare, StickyNote, CalendarDays, Clock, X } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	interface Props {
		task: TaskResponse | null;
		open: boolean;
		milestones?: MilestoneResponse[];
		onclose?: () => void;
		onsaved?: (task: TaskResponse) => void;
		ondeleted?: (taskId: string) => void;
	}

	let { task, open = $bindable(false), milestones = [], onclose, onsaved, ondeleted }: Props = $props();

	let title = $state('');
	let description = $state('');
	let status = $state('open');
	let priority = $state('medium');
	let dueDate = $state('');
	let milestoneId = $state<string | null>(null);
	let checklist = $state<ChecklistItemCreate[]>([]);
	let newCheckItem = $state('');
	let editingCheckIndex = $state<number | null>(null);
	let saving = $state(false);

	let checklistDone = $derived(checklist.filter((c) => c.is_checked).length);
	let checklistTotal = $derived(checklist.length);
	let checklistPct = $derived(checklistTotal > 0 ? Math.round((checklistDone / checklistTotal) * 100) : 0);

	let linkedNoteTitles = $state<Record<string, string>>({});
	let linkedEventTitle = $state<string | null>(null);

	// Fetch linked note titles
	$effect(() => {
		const noteIds = task?.note_ids ?? [];
		if (noteIds.length === 0) {
			linkedNoteTitles = {};
			return;
		}
		Promise.all(
			noteIds.map((id) =>
				api.get<NoteResponse>(`/api/notes/${id}`)
					.then((n) => ({ id, title: n.title }))
					.catch(() => ({ id, title: 'Unknown note' }))
			)
		).then((results) => {
			const titles: Record<string, string> = {};
			results.forEach(({ id, title }) => {
				titles[id] = title;
			});
			linkedNoteTitles = titles;
		});
	});

	$effect(() => {
		const eventId = task?.calendar_event_id;
		if (eventId) {
			api.get<EventResponse>(`/api/calendar/events/${eventId}`).then((e) => (linkedEventTitle = e.title)).catch(() => (linkedEventTitle = null));
		} else {
			linkedEventTitle = null;
		}
	});

	$effect(() => {
		if (task) {
			title = task.title;
			description = task.description;
			status = task.status;
			priority = task.priority;
			dueDate = task.due_date ? task.due_date.slice(0, 10) : '';
			milestoneId = task.milestone_id;
			checklist = task.checklist.map((c) => ({ text: c.text, is_checked: c.is_checked }));
			editingCheckIndex = null;
			newCheckItem = '';
		}
	});

	async function handleSave() {
		if (!task || !title.trim()) return;
		saving = true;
		try {
			const update: TaskUpdate = {
				title: title.trim(),
				description,
				status,
				priority,
				due_date: dueDate ? toLocalISOString(dueDate) : null,
				milestone_id: milestoneId,
				checklist
			};
			const updated = await api.put<TaskResponse>(`/api/tasks/${task.id}`, update);
			onsaved?.(updated);
			open = false;
		} catch (e) {
			console.error('Failed to update task', e);
			toast.error('Failed to update task');
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!task) return;
		const confirmed = await confirmModal.confirm({
			title: 'Delete Task',
			message: 'Are you sure you want to delete this task?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		try {
			await api.delete(`/api/tasks/${task.id}`);
			ondeleted?.(task.id);
			open = false;
		} catch (e) {
			console.error('Failed to delete task', e);
			toast.error('Failed to delete task');
		}
	}

	function addCheckItem() {
		if (!newCheckItem.trim()) return;
		checklist = [...checklist, { text: newCheckItem.trim(), is_checked: false }];
		newCheckItem = '';
	}

	function handleCheckItemKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addCheckItem();
		}
	}

	function toggleCheckItem(index: number) {
		checklist = checklist.map((c, i) =>
			i === index ? { ...c, is_checked: !c.is_checked } : c
		);
	}

	function removeCheckItem(index: number) {
		checklist = checklist.filter((_, i) => i !== index);
		if (editingCheckIndex === index) editingCheckIndex = null;
	}

	function startEditCheckItem(index: number) {
		editingCheckIndex = index;
	}

	function finishEditCheckItem(index: number, newText: string) {
		if (newText.trim()) {
			checklist = checklist.map((c, i) =>
				i === index ? { ...c, text: newText.trim() } : c
			);
		} else {
			removeCheckItem(index);
		}
		editingCheckIndex = null;
	}

	function handleEditKeydown(e: KeyboardEvent, index: number) {
		if (e.key === 'Enter') {
			e.preventDefault();
			const input = e.target as HTMLInputElement;
			finishEditCheckItem(index, input.value);
			// Focus the new item input
			const addInput = document.querySelector('[data-checklist-add]') as HTMLInputElement;
			addInput?.focus();
		} else if (e.key === 'Escape') {
			editingCheckIndex = null;
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
</script>

<Modal bind:open title="Edit Task" size="wide" {onclose}>
	{#if task}
		<div class="flex flex-col gap-4">
			<Input placeholder="Task title" bind:value={title} />

			<textarea
				class="textarea textarea-bordered w-full text-sm"
				rows="3"
				placeholder="Description..."
				bind:value={description}
			></textarea>

			<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
				<div>
					<p class="text-xs text-base-content/60 mb-1">Status</p>
					<select class="select select-bordered select-sm w-full" bind:value={status}>
						<option value="open">Open</option>
						<option value="in_progress">In Progress</option>
						<option value="done">Done</option>
					</select>
				</div>
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
					<div class="flex gap-1">
						<input type="date" class="input input-bordered input-sm flex-1" bind:value={dueDate} />
						{#if dueDate}
							<button type="button" class="btn btn-ghost btn-sm btn-square text-error" onclick={() => dueDate = ''} title="Clear due date">
								<X size={14} />
							</button>
						{/if}
					</div>
				</div>
			</div>

			{#if milestones.length > 0}
				<div>
					<p class="text-xs text-base-content/60 mb-1">Milestone</p>
					<select class="select select-bordered select-sm w-full" bind:value={milestoneId}>
						{#each milestones as ms}
							<option value={ms.id}>{ms.name}</option>
						{/each}
					</select>
				</div>
			{/if}

			<!-- Linked items -->
			{#if (task.note_ids?.length ?? 0) > 0 || task.calendar_event_id}
				<div class="flex flex-col gap-1 text-xs text-base-content/60">
					{#each task.note_ids ?? [] as noteId}
						<a href="{base}/notes/{noteId}" class="flex items-center gap-1 hover:text-primary transition-colors" onclick={(e) => e.stopPropagation()}>
							<StickyNote size={12} />
							{linkedNoteTitles[noteId] ?? 'Linked note'}
						</a>
					{/each}
					{#if task.calendar_event_id}
						<a href="{base}/calendar" class="flex items-center gap-1 hover:text-primary transition-colors" onclick={(e) => e.stopPropagation()}>
							<CalendarDays size={12} />
							{linkedEventTitle ?? 'Calendar event'}
						</a>
					{/if}
				</div>
			{/if}

			<!-- Checklist -->
			<div>
				<div class="flex items-center justify-between mb-1">
					<p class="text-xs text-base-content/60">Checklist</p>
					{#if checklistTotal > 0}
						<span class="text-xs text-base-content/50 tabular-nums">{checklistDone}/{checklistTotal}</span>
					{/if}
				</div>
				{#if checklistTotal > 0}
					<div class="h-1.5 bg-base-300 rounded-full overflow-hidden mb-2">
						<div
							class="h-full rounded-full transition-all {checklistPct === 100 ? 'bg-success' : 'bg-primary'}"
							style:width="{checklistPct}%"
						></div>
					</div>
				{/if}
				{#each checklist as item, i}
					<div class="flex items-center gap-2 py-1 group">
						<button class="btn btn-ghost btn-xs btn-square shrink-0" onclick={() => toggleCheckItem(i)}>
							{#if item.is_checked}
								<CheckSquare size={16} class="text-success" />
							{:else}
								<Square size={16} />
							{/if}
						</button>
						{#if editingCheckIndex === i}
							<input
								type="text"
								class="input input-bordered input-xs flex-1"
								value={item.text}
								onblur={(e) => finishEditCheckItem(i, (e.target as HTMLInputElement).value)}
								onkeydown={(e) => handleEditKeydown(e, i)}
								autofocus
							/>
						{:else}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<span
								class="flex-1 text-sm {item.is_checked ? 'line-through text-base-content/40' : ''} cursor-text"
								ondblclick={() => startEditCheckItem(i)}
							>
								{item.text}
							</span>
						{/if}
						<button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onclick={() => removeCheckItem(i)}>
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
						onkeydown={handleCheckItemKeydown}
						data-checklist-add
					/>
					<button class="btn btn-ghost btn-sm" onclick={addCheckItem} disabled={!newCheckItem.trim()}>
						<Plus size={14} />
					</button>
				</div>
			</div>

			<!-- Timestamps -->
			{#if task.created_at || task.updated_at}
				<div class="flex items-center gap-4 text-xs text-base-content/40 pt-2 border-t border-base-200">
					<span class="flex items-center gap-1">
						<Clock size={11} />
						Created {formatTimestamp(task.created_at)}
					</span>
					{#if task.updated_at !== task.created_at}
						<span>Updated {formatTimestamp(task.updated_at)}</span>
					{/if}
				</div>
			{/if}

			<div class="flex items-center gap-2 mt-1">
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
