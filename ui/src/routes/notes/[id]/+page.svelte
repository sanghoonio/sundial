<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { NoteCreate, NoteResponse, NoteUpdate, LinksResponse, NoteBlock, NoteListItem, ProjectList, ProjectResponse, TaskList } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';
	import TaskCreatePanel from '$lib/components/tasks/TaskCreatePanel.svelte';
	import { ArrowLeft, Trash2, Eye, Pencil, Sparkles, Save, Check, Info, Download, Plus, CalendarDays, ArrowUpLeft, X, Link, EllipsisVertical, Maximize, Minimize } from 'lucide-svelte';
	import { fullscreen } from '$lib/stores/fullscreen.svelte';
	import { notesSearch } from '$lib/stores/notesSearch.svelte';
	import FindBar from '$lib/components/notes/FindBar.svelte';
	import type { TaskResponse } from '$lib/types';
	import { ws } from '$lib/stores/websocket.svelte';

	let note = $state<NoteResponse | null>(null);
	let links = $state<LinksResponse | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let preview = $state(false);
	let analyzing = $state(false);
	let showMeta = $state(false);

	let title = $state('');
	let blocks = $state<NoteBlock[]>([]);
	let tags = $state<string[]>([]);
	let projectId = $state<string | null>(null);

	let createTaskOpen = $state(false);
	let createTaskProjectId = $state('');
	let createTaskProjects = $state<ProjectResponse[]>([]);

	// Find bar
	let findOpen = $state(false);
	let editorContentEl = $state<HTMLElement | null>(null);
	let findBar = $state<ReturnType<typeof FindBar> | null>(null);

	// Link existing task
	let showTaskSelector = $state(false);
	let availableTasks = $state<{ id: string; title: string }[]>([]);
	let taskSearchQuery = $state('');
	let loadingTasks = $state(false);

	// Reset fullscreen when navigating away
	$effect(() => () => fullscreen.exit());

	// Keep store in sync so MarkdownBlock can hide float toolbar
	$effect(() => { notesSearch.findOpen = findOpen; });

	let noteId = $derived(page.params.id);
	let isNew = $derived(noteId === 'new');
	let loaded = $state(false);
	let creating = $state(false);
	let justCreated = $state(false);

	async function load() {
		loading = true;
		loaded = false;
		try {
			const [n, lnks] = await Promise.all([
				api.get<NoteResponse>(`/api/notes/${noteId}`),
				api.get<LinksResponse>(`/api/notes/${noteId}/links`)
			]);
			note = n;
			links = lnks;
			title = n.title;
			tags = [...n.tags];
			projectId = n.project_id;

			// Resolve projects for task creation
			try {
				const pl = await api.get<ProjectList>('/api/projects');
				createTaskProjects = pl.projects;
				createTaskProjectId = n.project_id && pl.projects.some((p) => p.id === n.project_id)
					? n.project_id
					: pl.projects.length > 0 ? pl.projects[0].id : '';
			} catch {
				createTaskProjects = [];
				createTaskProjectId = '';
			}

			// Use blocks from API response, fallback to single md block
			if (n.blocks && n.blocks.length > 0) {
				blocks = n.blocks.map((b) => ({ ...b }));
			} else {
				blocks = [{ id: newBlockId(), type: 'md', content: n.content || '' }];
			}
		} catch (e) {
			console.error('Failed to load note', e);
			toast.error('Failed to load note');
			goto(`${base}/notes`);
		} finally {
			loading = false;
			// Snapshot the loaded state so auto-save only fires on real changes
			lastSavedSnapshot = currentSnapshot();
			loaded = true;
		}
	}

	function initCreateMode() {
		note = null;
		links = null;
		loading = false;
		loaded = true;
		creating = false;
		title = '';
		blocks = [{ id: newBlockId(), type: 'md', content: '' }];
		tags = [];
		projectId = page.url.searchParams.get('project') ?? null;
		lastSavedSnapshot = currentSnapshot();
	}

	$effect(() => {
		noteId; // track — only noteId should trigger this effect
		untrack(() => {
			findOpen = false;
			if (isNew) {
				initCreateMode();
			} else if (justCreated) {
				// After auto-create goto, skip re-fetching — just load links in background
				justCreated = false;
				api.get<LinksResponse>(`/api/notes/${noteId}/links`).then((l) => (links = l)).catch(() => {});
			} else {
				load();
			}
		});
	});

	// --- Create-mode: auto-create after 1s when content exists ---
	let autoCreateTimer: ReturnType<typeof setTimeout>;

	function hasContent(): boolean {
		return blocks.some((b) => {
			if (b.type === 'md') return b.content.trim().length > 0;
			if (b.type === 'chat') return (b.messages?.length ?? 0) > 0;
			return false;
		});
	}

	async function handleCreate() {
		if (creating || !hasContent()) return;
		creating = true;
		saveStatus = 'saving';
		try {
			const data: NoteCreate = { title: title.trim() || 'Untitled', blocks, tags, project_id: projectId };
			const created = await api.post<NoteResponse>('/api/notes', data);
			note = created;
			notesList.refresh();
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => { showSavedText = false; saveStatus = 'idle'; }, 2000);
			lastSavedSnapshot = currentSnapshot();
			// Navigate to real ID — component stays mounted since both match [id] route
			justCreated = true;
			goto(`${base}/notes/${created.id}`, { replaceState: true });
		} catch (e) {
			console.error('Failed to create note', e);
			toast.error('Failed to create note');
			saveStatus = 'error';
			creating = false;
		}
	}

	$effect(() => {
		if (!isNew || creating) return;
		// Track reactive deps
		title;
		blocks;

		clearTimeout(autoCreateTimer);
		if (hasContent()) {
			autoCreateTimer = setTimeout(() => handleCreate(), 1000);
		}
		return () => clearTimeout(autoCreateTimer);
	});

	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;

	async function handleSave() {
		if (isNew) { handleCreate(); return; }
		if (!title.trim()) return;
		clearTimeout(autoSaveTimer);
		saving = true;
		saveStatus = 'saving';
		try {
			const update: NoteUpdate = {
				title: title.trim(),
				blocks,
				tags,
				project_id: projectId
			};
			note = await api.put<NoteResponse>(`/api/notes/${noteId}`, update);
			lastSavedSnapshot = currentSnapshot();
			// Patch the list item in-place (no full re-fetch / no spinner)
			const firstMdBlock = blocks.find((b) => b.type === 'md');
			const previewText = (firstMdBlock?.content || '').slice(0, 80);
			notesList.patchNote({
				id: note.id,
				title: note.title,
				filepath: note.filepath,
				tags: note.tags,
				project_id: note.project_id,
				linked_tasks: note.linked_tasks,
				linked_events: note.linked_events,
				preview: previewText,
				created_at: note.created_at,
				updated_at: note.updated_at
			} satisfies NoteListItem);
			// Re-fetch links so wiki-link changes are reflected
			links = await api.get<LinksResponse>(`/api/notes/${noteId}/links`);
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			savedTextTimer = setTimeout(() => {
				showSavedText = false;
				saveStatus = 'idle';
			}, 2000);
		} catch {
			saveStatus = 'error';
		} finally {
			saving = false;
		}
	}

	// Auto-save: debounce 500ms after any actual change
	let autoSaveTimer: ReturnType<typeof setTimeout>;
	let lastSavedSnapshot = $state('');

	function currentSnapshot(): string {
		return JSON.stringify({ title, blocks, tags, projectId });
	}

	$effect(() => {
		if (!loaded || !note || isNew) return;
		const snap = currentSnapshot();
		if (snap === lastSavedSnapshot) return;

		saveStatus = 'idle';
		showSavedText = false;
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => handleSave(), 500);
		return () => clearTimeout(autoSaveTimer);
	});

	// WebSocket: reload note if updated externally (only when no unsaved changes)
	$effect(() => {
		const id = noteId;
		const unsub = ws.on(
			['note_updated', 'ai_tags_suggested'],
			(data) => {
				if (data.id !== id || isNew) return;
				if (currentSnapshot() !== lastSavedSnapshot) return;
				load();
			},
			1000
		);
		return unsub;
	});

	// WebSocket: navigate away if this note is deleted externally
	$effect(() => {
		const id = noteId;
		const unsub = ws.on(
			['note_deleted'],
			(data) => {
				if (data.id !== id) return;
				toast.info('This note was deleted');
				goto(`${base}/notes`);
			},
			0
		);
		return unsub;
	});

	async function handleDelete() {
		const confirmed = await confirmModal.confirm({
			title: 'Delete Note',
			message: 'Are you sure you want to delete this note?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		try {
			await api.delete(`/api/notes/${noteId}`);
			notesList.refresh();
			goto(`${base}/notes`);
		} catch (e) {
			console.error('Failed to delete note', e);
			toast.error('Failed to delete note');
		}
	}

	interface AnalyzeNoteResponse {
		suggested_tags: string[];
		extracted_tasks: { title: string; description: string; priority: string }[];
		linked_events: string[];
	}

	async function handleAnalyze() {
		analyzing = true;
		try {
			const res = await api.post<AnalyzeNoteResponse>(`/api/ai/analyze-note/${noteId}`);

			// Add any new suggested tags
			if (res.suggested_tags && res.suggested_tags.length > 0) {
				const newTags = res.suggested_tags.filter((t) => !tags.includes(t));
				if (newTags.length > 0) {
					tags = [...tags, ...newTags];
				}
			}
		} catch (e) {
			console.error('AI analysis failed', e);
			toast.error('AI analysis failed');
		} finally {
			analyzing = false;
		}
	}

	function handleExport() {
		if (!note) return;

		// Build YAML frontmatter
		const fm = [
			'---',
			`title: "${title.replace(/"/g, '\\"')}"`,
			`tags: [${tags.map((t) => `"${t}"`).join(', ')}]`,
			`created: ${note.created_at}`,
			`updated: ${note.updated_at}`,
			'---',
			''
		].join('\n');

		// Gather content from all blocks
		const content = blocks
			.map((b) => {
				if (b.type === 'md') return b.content;
				if (b.type === 'chat' && b.messages?.length) {
					return b.messages
						.map((m) => `**${m.role === 'user' ? 'You' : 'Assistant'}:**\n${m.content}`)
						.join('\n\n');
				}
				return '';
			})
			.filter(Boolean)
			.join('\n\n');

		const markdown = fm + content;
		const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = slugify(title) + '.md';
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function slugify(text: string): string {
		return text
			.toLowerCase()
			.replace(/[^\w\s-]/g, '')
			.replace(/\s+/g, '-')
			.replace(/-+/g, '-')
			.trim() || 'note';
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'f') {
			e.preventDefault();
			notesSearch.requestFocus();
			return;
		} else if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		} else if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
			e.preventDefault();
			if (findOpen) {
				findBar?.focus();
			} else {
				findOpen = true;
				requestAnimationFrame(() => findBar?.focus());
			}
		} else if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
			e.preventDefault();
			preview = !preview;
		} else if ((e.metaKey || e.ctrlKey) && e.key === 'm') {
			e.preventDefault();
			showMeta = !showMeta;
		} else if ((e.metaKey || e.ctrlKey) && e.key === 'd') {
			e.preventDefault();
			fullscreen.toggle();
		} else if (e.key === 'Escape' && findOpen) {
			e.preventDefault();
			findOpen = false;
		} else if (e.key === 'Escape' && fullscreen.active) {
			fullscreen.exit();
		}
	}


	function handleContentDblClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (preview) {
			// Preview: dblclick anywhere switches to edit (except links)
			if (target.closest('a')) return;
			preview = false;
		} else {
			// Edit: only toggle on whitespace outside blocks
			if (target.closest('[data-note-block], button, a, input, textarea')) return;
			preview = true;
		}
	}

	let hasAnyLinks = $derived(
		links && (
			links.outgoing_notes.length > 0 ||
			links.outgoing_tasks.length > 0 ||
			links.outgoing_events.length > 0 ||
			links.incoming_notes.length > 0 ||
			links.incoming_tasks.length > 0
		)
	);

	let hasTasks = $derived(
		links && (links.outgoing_tasks.length > 0 || links.incoming_tasks.length > 0)
	);

	let hasEvents = $derived(
		links && links.outgoing_events.length > 0
	);

	let hasNotes = $derived(
		links && (links.outgoing_notes.length > 0 || links.incoming_notes.length > 0)
	);

	async function unlinkTask(taskId: string) {
		if (!noteId) return;
		try {
			// Get the task to find its current note_ids
			const task = await api.get<TaskResponse>(`/api/tasks/${taskId}`);
			// Remove this note from the task's note_ids
			const updatedNoteIds = (task.note_ids || []).filter((id) => id !== noteId);
			await api.put(`/api/tasks/${taskId}`, { note_ids: updatedNoteIds });
			// Refresh links
			links = await api.get<LinksResponse>(`/api/notes/${noteId}/links`);
		} catch (e) {
			console.error('Failed to unlink task', e);
			toast.error('Failed to unlink task');
		}
	}

	async function loadAvailableTasks() {
		loadingTasks = true;
		try {
			const res = await api.get<TaskList>(`/api/tasks?limit=50`);
			availableTasks = res.tasks.map((t) => ({ id: t.id, title: t.title }));
		} catch {
			availableTasks = [];
		} finally {
			loadingTasks = false;
		}
	}

	function openTaskSelector() {
		showTaskSelector = true;
		taskSearchQuery = '';
		loadAvailableTasks();
	}

	async function linkTask(taskId: string) {
		if (!noteId) return;
		try {
			// Get the task to find its current note_ids
			const task = await api.get<TaskResponse>(`/api/tasks/${taskId}`);
			// Add this note to the task's note_ids if not already there
			const currentNoteIds = task.note_ids || [];
			if (!currentNoteIds.includes(noteId)) {
				await api.put(`/api/tasks/${taskId}`, { note_ids: [...currentNoteIds, noteId] });
			}
			// Refresh links
			links = await api.get<LinksResponse>(`/api/notes/${noteId}/links`);
			showTaskSelector = false;
		} catch (e) {
			console.error('Failed to link task', e);
			toast.error('Failed to link task');
		}
	}

	// Get IDs of already linked tasks
	let linkedTaskIds = $derived(
		links ? [...links.outgoing_tasks.map(t => t.id), ...links.incoming_tasks.map(t => t.id)] : []
	);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if loading && !isNew}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if note || isNew}
	<div class="flex h-full">
	<div class="flex-1 flex flex-col min-w-0">
		<!-- Top bar — matches left pane header height -->
		<div class="flex items-center gap-1 md:gap-2 px-4 py-3 border-b border-base-300 shrink-0">
			<a href="{base}/notes" class="btn btn-ghost btn-sm btn-square md:hidden">
				<ArrowLeft size={18} />
			</a>
			<input
				type="text"
				bind:value={title}
				placeholder="Untitled"
				class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 truncate"
			/>
			<!-- Save status -->
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
			<!-- Preview toggle -->
			<button
				class="btn btn-ghost btn-sm btn-square"
				onclick={() => (preview = !preview)}
				title={preview ? 'Edit (Ctrl+E)' : 'Preview (Ctrl+E)'}
			>
				{#if preview}
					<Pencil size={16} />
				{:else}
					<Eye size={16} />
				{/if}
			</button>
			<!-- Fullscreen toggle -->
			<button
				class="btn btn-ghost btn-sm btn-square flex"
				onclick={() => fullscreen.toggle()}
				title={fullscreen.active ? 'Exit fullscreen (Ctrl+D)' : 'Fullscreen (Ctrl+D)'}
			>
				{#if fullscreen.active}
					<Minimize size={16} />
				{:else}
					<Maximize size={16} />
				{/if}
			</button>
			<!-- Desktop-only buttons -->
			<button
				class="btn btn-ghost btn-sm btn-square hidden md:flex"
				onclick={handleAnalyze}
				disabled={analyzing}
				title="Analyze with AI"
			>
				{#if analyzing}
					<span class="loading loading-spinner loading-xs"></span>
				{:else}
					<Sparkles size={16} />
				{/if}
			</button>
			<div class="hidden md:block">
				<ProjectSelect bind:value={projectId} />
			</div>
			<button
				class="btn btn-ghost btn-sm btn-square hidden md:flex"
				class:btn-active={showMeta}
				onclick={() => (showMeta = !showMeta)}
				title="Note info (Ctrl+M)"
			>
				<Info size={16} />
			</button>
			<button class="btn btn-ghost btn-sm btn-square hidden md:flex" onclick={handleExport} title="Download as markdown">
				<Download size={16} />
			</button>
			<button class="btn btn-ghost btn-sm btn-square text-error hidden md:flex" onclick={handleDelete}>
				<Trash2 size={16} />
			</button>
			<!-- Mobile overflow menu -->
			<div class="dropdown dropdown-end md:hidden">
				<button tabindex="0" class="btn btn-ghost btn-sm btn-square">
					<EllipsisVertical size={16} />
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-48 p-1 border border-base-300 mt-1">
					<li>
						<button onclick={handleAnalyze} disabled={analyzing}>
							<Sparkles size={14} />
							Analyze with AI
						</button>
					</li>
					<li>
						<button onclick={() => (showMeta = !showMeta)}>
							<Info size={14} />
							{showMeta ? 'Hide info' : 'Show info'}
						</button>
					</li>
					<li>
						<button onclick={handleExport}>
							<Download size={14} />
							Export markdown
						</button>
					</li>
					<li>
						<button class="text-error" onclick={handleDelete}>
							<Trash2 size={14} />
							Delete note
						</button>
					</li>
				</ul>
			</div>
		</div>

		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<!-- Scrollable content -->
		<div class="flex-1 min-h-0 relative">
		{#if findOpen}
			<FindBar
				bind:this={findBar}
				{blocks}
				{preview}
				containerEl={editorContentEl!}
				onclose={() => (findOpen = false)}
			/>
		{/if}
		<div class="h-full overflow-y-auto p-4 pb-20 md:p-6" ondblclick={handleContentDblClick} bind:this={editorContentEl}>
		<!-- Metadata section -->
		{#if showMeta}
			<div class="mb-4 md:mb-6 rounded-lg border border-base-content/10 bg-base-200/30 px-3 py-2 flex flex-col">
				<div class="pb-3">
					<span class="text-xs font-medium text-base-content/50 mb-2 block">Tags</span>
					<TagInput bind:tags />
				</div>
				<!-- Links -->
				<div class="border-t border-base-content/5 -mx-3 px-3 pt-1">
					<div class="flex items-center justify-between mb-2">
						<span class="text-xs font-medium text-base-content/50">Links</span>
						<div class="flex items-center gap-1">
							{#if createTaskProjectId}
								<button class="btn btn-ghost btn-xs gap-1" onclick={() => (createTaskOpen = true)}>
									<Plus size={14} />
									Create task
								</button>
							{/if}
							<button class="btn btn-ghost btn-xs gap-1" onclick={openTaskSelector}>
								<Link size={14} />
								Link task
							</button>
						</div>
					</div>

					<!-- Task selector dropdown -->
					{#if showTaskSelector}
						<div class="mb-3 p-2 border border-base-300 rounded-lg bg-base-200">
							<input
								type="text"
								class="input input-bordered input-xs w-full mb-2"
								placeholder="Search tasks..."
								bind:value={taskSearchQuery}
							/>
							{#if loadingTasks}
								<div class="flex justify-center py-2">
									<span class="loading loading-spinner loading-xs"></span>
								</div>
							{:else}
								{@const filteredTasks = availableTasks.filter((t) =>
									!linkedTaskIds.includes(t.id) &&
									(!taskSearchQuery || t.title.toLowerCase().includes(taskSearchQuery.toLowerCase()))
								)}
								{#if filteredTasks.length > 0}
									<div class="max-h-32 overflow-y-auto flex flex-col gap-0.5">
										{#each filteredTasks as task}
											<button
												class="text-left text-xs px-2 py-1 rounded hover:bg-base-300 truncate"
												onclick={() => linkTask(task.id)}
											>
												{task.title}
											</button>
										{/each}
									</div>
								{:else}
									<p class="text-xs text-base-content/50 text-center py-2">No tasks found</p>
								{/if}
							{/if}
							<button class="btn btn-ghost btn-xs w-full mt-1" onclick={() => (showTaskSelector = false)}>
								Cancel
							</button>
						</div>
					{/if}

					{#if hasAnyLinks && links}
						<!-- Tasks -->
						{#if hasTasks}
							<div class="mb-3">
								<span class="text-xs text-base-content/40 uppercase tracking-wide block mb-1">Tasks</span>
								{#each links.outgoing_tasks as task}
									<div class="flex items-center gap-1 group">
										<a href="{base}/tasks/{task.project_id}?task={task.id}" class="inline-flex items-center gap-1.5 text-xs">
											<span>{task.title}</span>
											<span class="badge badge-xs {task.status === 'done' ? 'badge-success' : 'badge-ghost'}">{task.status === 'done' ? 'done' : 'in progress'}</span>
										</a>
										<button
											class="opacity-0 group-hover:opacity-100 hover:text-error transition-all cursor-pointer shrink-0"
											onclick={() => unlinkTask(task.id)}
											title="Unlink task"
										>
											<X size={12} />
										</button>
									</div>
								{/each}
								{#each links.incoming_tasks as task}
									<div class="flex items-center gap-1 group">
										<a href="{base}/tasks/{task.project_id}?task={task.id}" class="inline-flex items-center gap-1.5 text-xs">
											<ArrowUpLeft size={10} class="shrink-0 text-base-content/40" />
											<span>{task.title}</span>
											<span class="badge badge-xs {task.status === 'done' ? 'badge-success' : 'badge-ghost'}">{task.status === 'done' ? 'done' : 'in progress'}</span>
										</a>
										<button
											class="opacity-0 group-hover:opacity-100 hover:text-error transition-all cursor-pointer shrink-0"
											onclick={() => unlinkTask(task.id)}
											title="Unlink task"
										>
											<X size={12} />
										</button>
									</div>
								{/each}
							</div>
						{/if}

						<!-- Events -->
						{#if hasEvents}
							<div class="mb-3 leading-tight">
								<span class="text-xs text-base-content/40 uppercase tracking-wide block">Events</span>
								{#each links.outgoing_events as ev}
									<a href="{base}/calendar" class="inline-flex items-center gap-1.5 text-xs">
										<CalendarDays size={12} class="shrink-0 text-base-content/50" />
										<span>{ev.title}</span>
										<span class="text-base-content/40">{new Date(ev.start_time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
									</a><br>
								{/each}
							</div>
						{/if}

						<!-- Notes -->
						{#if hasNotes}
							<div class="mb-3 leading-tight">
								<span class="text-xs text-base-content/40 uppercase tracking-wide block">Notes</span>
								{#each links.outgoing_notes as n}
									<a href="{base}/notes/{n.id}" class="link link-primary text-xs">{n.title}</a><br>
								{/each}
								{#each links.incoming_notes as n}
									<a href="{base}/notes/{n.id}" class="inline-flex items-center gap-1 text-xs link link-primary">
										<ArrowUpLeft size={10} class="shrink-0 text-base-content/40" />
										{n.title}
									</a><br>
								{/each}
							</div>
						{/if}
					{:else}
						<p class="text-xs text-base-content/40 pb-3">No links yet</p>
					{/if}
				</div>

				{#if note}
					<div class="flex gap-6 text-xs text-base-content/40 border-t border-base-content/5 -mx-3 px-3 pt-2">
						<span>Created {new Date(note.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
						<span>Updated {new Date(note.updated_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Block Editor -->
		<NoteEditor
			{blocks}
			{noteId}
			{preview}
			onchange={(b) => (blocks = b)}
		/>
		</div>
		</div>
	</div>
	{#if createTaskOpen && createTaskProjectId}
		<TaskCreatePanel
			projectId={createTaskProjectId}
			projects={createTaskProjects}
			initialNoteId={noteId}
			onclose={() => (createTaskOpen = false)}
			oncreated={async () => {
				links = await api.get<LinksResponse>(`/api/notes/${noteId}/links`);
			}}
		/>
	{/if}
	</div>
{/if}
