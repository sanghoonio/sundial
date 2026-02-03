<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import type { NoteResponse, NoteUpdate, BacklinksResponse, NoteBlock, EventResponse, ProjectList, ProjectResponse } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import TaskCreatePanel from '$lib/components/tasks/TaskCreatePanel.svelte';
	import { ArrowLeft, Trash2, Eye, Pencil, Sparkles, Save, Check, Info, Download, Plus, CalendarDays } from 'lucide-svelte';

	let note = $state<NoteResponse | null>(null);
	let backlinks = $state<BacklinksResponse | null>(null);
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
	let linkedEventDetails = $state<EventResponse[]>([]);

	let noteId = $derived(page.params.id);
	let loaded = $state(false);

	async function load() {
		loading = true;
		loaded = false;
		try {
			const [n, bl] = await Promise.all([
				api.get<NoteResponse>(`/api/notes/${noteId}`),
				api.get<BacklinksResponse>(`/api/notes/${noteId}/backlinks`)
			]);
			note = n;
			backlinks = bl;
			title = n.title;
			tags = [...n.tags];
			projectId = n.project_id;

			// Fetch linked event details
			if (n.linked_events.length > 0) {
				const events = await Promise.all(
					n.linked_events.map((eid) =>
						api.get<EventResponse>(`/api/calendar/events/${eid}`).catch(() => null)
					)
				);
				linkedEventDetails = events.filter((e): e is EventResponse => e !== null);
			} else {
				linkedEventDetails = [];
			}

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
			goto('/notes');
		} finally {
			loading = false;
			// Snapshot the loaded state so auto-save only fires on real changes
			lastSavedSnapshot = currentSnapshot();
			loaded = true;
		}
	}

	$effect(() => {
		noteId;
		load();
	});

	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;

	async function handleSave() {
		if (!title.trim()) return;
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
			notesList.refresh();
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
		if (!loaded || !note) return;
		const snap = currentSnapshot();
		if (snap === lastSavedSnapshot) return;

		saveStatus = 'idle';
		showSavedText = false;
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(() => handleSave(), 500);
		return () => clearTimeout(autoSaveTimer);
	});

	async function handleDelete() {
		if (!confirm('Delete this note?')) return;
		try {
			await api.delete(`/api/notes/${noteId}`);
			notesList.refresh();
			goto('/notes');
		} catch (e) {
			console.error('Failed to delete note', e);
		}
	}

	async function handleAnalyze() {
		analyzing = true;
		try {
			const res = await api.post<{ result: Record<string, unknown> }>(
				`/api/ai/analyze-note/${noteId}`
			);
			const result = res.result;

			if (Array.isArray(result.suggested_tags) && result.suggested_tags.length > 0) {
				const newTags = result.suggested_tags.filter((t: string) => !tags.includes(t));
				if (newTags.length > 0) {
					tags = [...tags, ...newTags];
				}
			}
		} catch (e) {
			console.error('AI analysis failed', e);
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
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
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

	let hasBacklinks = $derived(
		backlinks && backlinks.notes.length > 0
	);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if note}
	<div class="flex h-full">
	<div class="flex-1 flex flex-col min-w-0">
		<!-- Top bar — matches left pane header height -->
		<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
			<a href="/notes" class="btn btn-ghost btn-sm btn-square md:hidden">
				<ArrowLeft size={18} />
			</a>
			<input
				type="text"
				bind:value={title}
				placeholder="Untitled"
				class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 truncate"
			/>
			<button
				class="btn btn-ghost btn-sm"
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
			<button
				class="btn btn-ghost btn-sm"
				class:btn-active={showMeta}
				onclick={() => (showMeta = !showMeta)}
				title="Note info"
			>
				<Info size={16} />
			</button>
			<button
				class="btn btn-ghost btn-sm gap-1.5"
				onclick={() => (preview = !preview)}
				title={preview ? 'Edit' : 'Preview'}
			>
				{#if preview}
					<Pencil size={16} />
					Edit
				{:else}
					<Eye size={16} />
					Preview
				{/if}
			</button>
			<button class="btn btn-ghost btn-sm" onclick={handleExport} title="Download as markdown">
				<Download size={16} />
			</button>
			<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
				<Trash2 size={16} />
			</button>
		</div>

		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<!-- Scrollable content -->
		<div class="flex-1 overflow-y-auto p-4 md:p-6" ondblclick={handleContentDblClick}>
		<!-- Metadata section -->
		{#if showMeta}
			<div class="mb-4 md:mb-6 rounded-lg border border-base-content/10 bg-base-200/30 p-3 flex flex-col gap-3">
				<div class="flex flex-col sm:flex-row gap-3">
					<div class="flex-1">
						<span class="text-xs font-medium text-base-content/50 mb-1 block">Tags</span>
						<TagInput bind:tags />
					</div>
					<div class="sm:w-48">
						<span class="text-xs font-medium text-base-content/50 mb-1 block">Project</span>
						<ProjectSelect bind:value={projectId} />
					</div>
				</div>
				{#if note}
					<div class="flex gap-6 text-xs text-base-content/40">
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

		<!-- Linked items -->
		<div class="mt-8 border-t border-base-300 pt-4">
			<div class="flex items-center justify-between mb-2">
				<h3 class="font-semibold text-sm text-base-content/60">Linked Items</h3>
				{#if createTaskProjectId}
					<button class="btn btn-ghost btn-xs gap-1" onclick={() => (createTaskOpen = true)}>
						<Plus size={14} />
						Create task
					</button>
				{/if}
			</div>
			{#if backlinks && backlinks.tasks.length > 0}
				<div class="mb-2">
					{#each backlinks.tasks as task}
						<a href="/tasks?task={task.id}" class="flex items-center gap-2 text-sm py-1 hover:bg-base-200 rounded px-1 -mx-1">
							<span class="badge badge-xs {task.status === 'done' ? 'badge-success' : task.status === 'in_progress' ? 'badge-info' : 'badge-ghost'}">{task.status.replace('_', ' ')}</span>
							<span class="truncate">{task.title}</span>
						</a>
					{/each}
				</div>
			{:else if note.linked_tasks.length > 0}
				<p class="text-sm text-base-content/60">{note.linked_tasks.length} linked task(s)</p>
			{/if}
			{#if linkedEventDetails.length > 0}
				<div class="mb-2">
					{#each linkedEventDetails as ev}
						<a href="/calendar" class="flex items-center gap-2 text-sm py-1 hover:bg-base-200 rounded px-1 -mx-1">
							<CalendarDays size={14} class="shrink-0 text-base-content/50" />
							<span class="truncate">{ev.title}</span>
							<span class="text-xs text-base-content/40 shrink-0">
								{new Date(ev.start_time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
							</span>
						</a>
					{/each}
				</div>
			{:else if note.linked_events.length > 0}
				<p class="text-sm text-base-content/60">{note.linked_events.length} linked event(s)</p>
			{/if}
			{#if !backlinks?.tasks.length && !note.linked_tasks.length && !linkedEventDetails.length && !note.linked_events.length}
				<p class="text-sm text-base-content/40">No linked items yet</p>
			{/if}
		</div>

		<!-- Backlinks (note-to-note only) -->
		{#if hasBacklinks}
			<div class="mt-6 border-t border-base-300 pt-4">
				<h3 class="font-semibold mb-2 text-sm text-base-content/60">Backlinks</h3>
				<div class="mb-2">
					{#each backlinks!.notes as bl}
						<a href="/notes/{bl.id}" class="link link-primary text-sm block py-0.5">
							{bl.title}
						</a>
					{/each}
				</div>
			</div>
		{/if}
		</div>
	</div>
	{#if createTaskOpen && createTaskProjectId}
		<TaskCreatePanel
			projectId={createTaskProjectId}
			projects={createTaskProjects}
			sourceNoteId={noteId}
			onclose={() => (createTaskOpen = false)}
			oncreated={async () => {
				backlinks = await api.get<BacklinksResponse>(`/api/notes/${noteId}/backlinks`);
			}}
		/>
	{/if}
	</div>
{/if}
