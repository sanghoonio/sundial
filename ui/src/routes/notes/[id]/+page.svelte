<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteResponse, NoteUpdate, BacklinksResponse, NoteBlock } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import { ArrowLeft, Trash2, Eye, Pencil, Sparkles, Save, Check, Info } from 'lucide-svelte';

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

			// Use blocks from API response, fallback to single md block
			if (n.blocks && n.blocks.length > 0) {
				blocks = n.blocks.map((b) => ({ ...b }));
			} else {
				blocks = [{ id: newBlockId(), type: 'md', content: n.content || '' }];
			}
		} catch {
			toasts.error('Failed to load note');
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
			toasts.success('Note deleted');
			goto('/notes');
		} catch {
			toasts.error('Failed to delete note');
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
					toasts.success(`Added ${newTags.length} suggested tag(s)`);
				}
			}

			if (Array.isArray(result.extracted_tasks) && result.extracted_tasks.length > 0) {
				toasts.info(`AI found ${result.extracted_tasks.length} potential task(s)`);
			}

			if (
				(!result.suggested_tags || (result.suggested_tags as string[]).length === 0) &&
				(!result.extracted_tasks || (result.extracted_tasks as string[]).length === 0)
			) {
				toasts.info('No suggestions from AI analysis');
			}
		} catch {
			toasts.error('AI analysis failed');
		} finally {
			analyzing = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		}
	}

	let hasBacklinks = $derived(
		backlinks && (backlinks.notes.length > 0 || backlinks.tasks.length > 0)
	);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if note}
	<div class="p-4 md:p-6">
		<!-- Top bar -->
		<div class="flex items-center gap-2 mb-4">
			<a href="/notes" class="btn btn-ghost btn-sm btn-square md:hidden">
				<ArrowLeft size={18} />
			</a>
			<input
				type="text"
				bind:value={title}
				placeholder="Untitled"
				class="flex-1 min-w-0 text-lg font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-1 truncate"
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
			<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
				<Trash2 size={16} />
			</button>
		</div>

		<!-- Metadata section -->
		{#if showMeta}
			<div class="mb-4 rounded-lg border border-base-content/10 bg-base-200/30 p-3 flex flex-col gap-3">
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
		{#if note.linked_tasks.length > 0 || note.linked_events.length > 0}
			<div class="mt-8 border-t border-base-300 pt-4">
				<h3 class="font-semibold mb-2 text-sm text-base-content/60">Linked Items</h3>
				{#if note.linked_tasks.length > 0}
					<p class="text-sm text-base-content/60">{note.linked_tasks.length} linked task(s)</p>
				{/if}
				{#if note.linked_events.length > 0}
					<p class="text-sm text-base-content/60">
						{note.linked_events.length} linked event(s)
					</p>
				{/if}
			</div>
		{/if}

		<!-- Backlinks -->
		{#if hasBacklinks}
			<div class="mt-6 border-t border-base-300 pt-4">
				<h3 class="font-semibold mb-2 text-sm text-base-content/60">Backlinks</h3>
				{#if backlinks!.notes.length > 0}
					<div class="mb-2">
						{#each backlinks!.notes as bl}
							<a href="/notes/{bl.id}" class="link link-primary text-sm block py-0.5">
								{bl.title}
							</a>
						{/each}
					</div>
				{/if}
				{#if backlinks!.tasks.length > 0}
					<div>
						{#each backlinks!.tasks as bl}
							<span class="text-sm block py-0.5">
								{bl.title}
								<span class="badge badge-sm badge-ghost ml-1">{bl.status}</span>
							</span>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
