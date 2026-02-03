<script lang="ts">
	import { api } from '$lib/services/api';
	import type { TaskResponse, TaskUpdate, ChecklistItemCreate, MilestoneResponse, ProjectResponse, NoteResponse, NoteList, EventResponse } from '$lib/types';
	import { Trash2, Plus, Square, CheckSquare, StickyNote, CalendarDays, Clock, X, Save, Check, Link } from 'lucide-svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';

	interface Props {
		task: TaskResponse;
		projects?: ProjectResponse[];
		milestones?: MilestoneResponse[];
		onclose: () => void;
		onsaved?: (task: TaskResponse) => void;
		ondeleted?: (taskId: string) => void;
	}

	let { task, projects = [], milestones = [], onclose, onsaved, ondeleted }: Props = $props();

	let title = $state('');
	let description = $state('');
	let status = $state('open');
	let priority = $state('medium');
	let dueDate = $state('');
	let projectId = $state('');
	let milestoneId = $state<string | null>(null);
	let checklist = $state<ChecklistItemCreate[]>([]);
	let noteIds = $state<string[]>([]);

	let currentProject = $derived(projects.find((p) => p.id === projectId));
	let availableMilestones = $derived(currentProject?.milestones ?? milestones);
	let newCheckItem = $state('');
	let editingCheckIndex = $state<number | null>(null);
	let saving = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;
	let loaded = $state(false);
	let lastSavedSnapshot = $state('');

	let linkedEventTitle = $state<string | null>(null);

	// Note linking
	let linkedNoteTitles = $state<Record<string, string>>({});
	let showNoteSelector = $state(false);
	let availableNotes = $state<{ id: string; title: string }[]>([]);
	let noteSearchQuery = $state('');
	let loadingNotes = $state(false);
	let fetchedNoteIds = new Set<string>();

	// Fetch linked event title
	$effect(() => {
		const eventId = task.calendar_event_id;
		if (eventId) {
			api.get<EventResponse>(`/api/calendar/events/${eventId}`).then((e) => (linkedEventTitle = e.title)).catch(() => (linkedEventTitle = null));
		} else {
			linkedEventTitle = null;
		}
	});

	// Fetch titles for linked notes
	$effect(() => {
		const ids = noteIds;
		if (ids.length === 0) {
			linkedNoteTitles = {};
			fetchedNoteIds.clear();
			return;
		}
		for (const id of ids) {
			if (!fetchedNoteIds.has(id)) {
				fetchedNoteIds.add(id);
				api.get<NoteResponse>(`/api/notes/${id}`)
					.then((n) => { linkedNoteTitles[id] = n.title; linkedNoteTitles = linkedNoteTitles; })
					.catch(() => { linkedNoteTitles[id] = 'Unknown note'; linkedNoteTitles = linkedNoteTitles; });
			}
		}
	});

	async function loadAvailableNotes() {
		loadingNotes = true;
		try {
			const res = await api.get<NoteList>(`/api/notes?limit=50${noteSearchQuery ? `&q=${encodeURIComponent(noteSearchQuery)}` : ''}`);
			availableNotes = res.notes.map((n) => ({ id: n.id, title: n.title }));
		} catch {
			availableNotes = [];
		} finally {
			loadingNotes = false;
		}
	}

	function openNoteSelector() {
		showNoteSelector = true;
		noteSearchQuery = '';
		loadAvailableNotes();
	}

	function linkNote(noteId: string) {
		if (!noteIds.includes(noteId)) {
			noteIds = [...noteIds, noteId];
		}
		showNoteSelector = false;
	}

	function unlinkNote(noteId: string) {
		noteIds = noteIds.filter((id) => id !== noteId);
	}

	let checklistDone = $derived(checklist.filter((c) => c.is_checked).length);
	let checklistTotal = $derived(checklist.length);
	let checklistPct = $derived(checklistTotal > 0 ? Math.round((checklistDone / checklistTotal) * 100) : 0);

	function loadFromTask(t: TaskResponse) {
		loaded = false;
		title = t.title;
		description = t.description;
		status = t.status;
		priority = t.priority;
		dueDate = t.due_date ? t.due_date.slice(0, 10) : '';
		projectId = t.project_id;
		milestoneId = t.milestone_id;
		checklist = t.checklist.map((c) => ({ text: c.text, is_checked: c.is_checked }));
		// Merge source_note_id into noteIds for uniform handling
		const ids = t.note_ids ?? [];
		if (t.source_note_id && !ids.includes(t.source_note_id)) {
			ids.push(t.source_note_id);
		}
		noteIds = ids;
		linkedNoteTitles = {};
		fetchedNoteIds.clear();
		editingCheckIndex = null;
		newCheckItem = '';
		showNoteSelector = false;
		saveStatus = 'idle';
		showSavedText = false;
		lastSavedSnapshot = currentSnapshot();
		loaded = true;
	}

	// Only reload form state when a different task is selected
	let lastTaskId = $state('');
	$effect(() => {
		const id = task.id;
		if (id !== lastTaskId) {
			lastTaskId = id;
			loadFromTask(task);
		}
	});

	function currentSnapshot(): string {
		return JSON.stringify({ title, description, status, priority, dueDate, projectId, milestoneId, checklist, noteIds });
	}

	async function handleSave() {
		if (!title.trim()) return;
		saving = true;
		saveStatus = 'saving';
		try {
			const update: TaskUpdate = {
				title: title.trim(),
				description,
				status,
				priority,
				due_date: dueDate ? new Date(dueDate).toISOString() : null,
				project_id: projectId,
				milestone_id: milestoneId,
				checklist,
				note_ids: noteIds
			};
			const updated = await api.put<TaskResponse>(`/api/tasks/${task.id}`, update);
			lastSavedSnapshot = currentSnapshot();
			onsaved?.(updated);
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => {
				showSavedText = false;
				saveStatus = 'idle';
			}, 2000);
		} catch (e) {
			saveStatus = 'error';
			console.error('Failed to update task', e);
		} finally {
			saving = false;
		}
	}

	// Auto-save: debounce 500ms after any actual change
	let autoSaveTimer: ReturnType<typeof setTimeout>;

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

	async function handleDelete() {
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
		} catch (e) {
			console.error('Failed to delete task', e);
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

<aside class="w-96 shrink-0 border-l border-base-300 bg-base-100 flex flex-col overflow-hidden">
	<!-- Header -->
	<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
		<input
			type="text"
			bind:value={title}
			placeholder="Task title"
			class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 truncate"
		/>
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
		<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete} title="Delete task">
			<Trash2 size={16} />
		</button>
		<button class="btn btn-ghost btn-sm btn-square" onclick={onclose} title="Close">
			<X size={16} />
		</button>
	</div>

	<!-- Scrollable body -->
	<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
		<!-- Description -->
		<textarea
			class="textarea textarea-bordered w-full text-sm"
			rows="3"
			placeholder="Description..."
			bind:value={description}
		></textarea>

		<!-- Project -->
		{#if projects.length > 0}
			<div>
				<p class="text-xs text-base-content/60 mb-1">Project</p>
				<select class="select select-bordered select-sm w-full" bind:value={projectId} onchange={() => { milestoneId = null; }}>
					{#each projects as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
			</div>
		{/if}

		<!-- Fields grid -->
		<div class="grid grid-cols-2 gap-3">
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
				<input type="date" class="input input-bordered input-sm w-full" bind:value={dueDate} />
			</div>
			{#if availableMilestones.length > 0}
				<div>
					<p class="text-xs text-base-content/60 mb-1">Milestone</p>
					<select class="select select-bordered select-sm w-full" bind:value={milestoneId}>
						<option value={null}>None</option>
						{#each availableMilestones as ms}
							<option value={ms.id}>{ms.name}</option>
						{/each}
					</select>
				</div>
			{/if}
		</div>

		<!-- Linked items -->
		<div>
			<div class="flex items-center justify-between mb-1">
				<p class="text-xs text-base-content/60">Linked items</p>
				<button class="btn btn-ghost btn-xs gap-1" onclick={openNoteSelector}>
					<Link size={12} />
					Link note
				</button>
			</div>

			<!-- Note selector dropdown -->
			{#if showNoteSelector}
				<div class="mb-2 p-2 border border-base-300 rounded-lg bg-base-200">
					<input
						type="text"
						class="input input-bordered input-xs w-full mb-2"
						placeholder="Search notes..."
						bind:value={noteSearchQuery}
						oninput={() => loadAvailableNotes()}
					/>
					{#if loadingNotes}
						<div class="flex justify-center py-2">
							<span class="loading loading-spinner loading-xs"></span>
						</div>
					{:else if availableNotes.length > 0}
						<div class="max-h-32 overflow-y-auto flex flex-col gap-0.5">
							{#each availableNotes.filter((n) => !noteIds.includes(n.id)) as note}
								<button
									class="text-left text-xs px-2 py-1 rounded hover:bg-base-300 truncate"
									onclick={() => linkNote(note.id)}
								>
									{note.title}
								</button>
							{/each}
						</div>
					{:else}
						<p class="text-xs text-base-content/50 text-center py-2">No notes found</p>
					{/if}
					<button class="btn btn-ghost btn-xs w-full mt-1" onclick={() => (showNoteSelector = false)}>
						Cancel
					</button>
				</div>
			{/if}

			<div class="flex flex-col gap-1 text-xs text-base-content/60">
				{#each noteIds as noteId}
					<div class="flex items-center gap-1 group">
						<a href="/notes/{noteId}" class="inline-flex items-center gap-1 hover:text-primary transition-colors truncate">
							<StickyNote size={12} class="shrink-0" />
							<span class="truncate">{linkedNoteTitles[noteId] ?? 'Loading...'}</span>
						</a>
						<button
							class="opacity-0 group-hover:opacity-100 hover:text-error transition-all cursor-pointer shrink-0"
							onclick={() => unlinkNote(noteId)}
							title="Unlink note"
						>
							<X size={12} />
						</button>
					</div>
				{/each}

				{#if task.calendar_event_id}
					<a href="/calendar" class="inline-flex items-center gap-1 hover:text-primary transition-colors">
						<CalendarDays size={12} />
						{linkedEventTitle ?? 'Calendar event'}
					</a>
				{/if}

				{#if noteIds.length === 0 && !task.calendar_event_id}
					<p class="text-base-content/40 text-xs">No linked items</p>
				{/if}
			</div>
		</div>

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
					onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCheckItem(); } }}
					data-checklist-add
				/>
				<button class="btn btn-ghost btn-sm" onclick={addCheckItem} disabled={!newCheckItem.trim()}>
					<Plus size={14} />
				</button>
			</div>
		</div>

		<!-- Timestamps -->
		{#if task.created_at || task.updated_at}
			<div class="flex flex-col gap-1 text-xs text-base-content/40 pt-2 border-t border-base-200">
				<span class="flex items-center gap-1">
					<Clock size={11} />
					Created {formatTimestamp(task.created_at)}
				</span>
				{#if task.updated_at !== task.created_at}
					<span class="ml-4">Updated {formatTimestamp(task.updated_at)}</span>
				{/if}
			</div>
		{/if}
	</div>
</aside>
