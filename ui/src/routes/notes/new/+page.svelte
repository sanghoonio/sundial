<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { NoteCreate, NoteResponse, NoteBlock } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { ArrowLeft, Eye, Pencil, Save, Check, Info } from 'lucide-svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';

	let title = $state('');
	let blocks = $state<NoteBlock[]>([{ id: newBlockId(), type: 'md', content: '' }]);
	let tags = $state<string[]>([]);
	let projectId = $state<string | null>(page.url.searchParams.get('project'));
	let preview = $state(false);
	let showMeta = $state(false);

	let creating = $state(false);
	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let showSavedText = $state(false);
	let savedTextTimer: ReturnType<typeof setTimeout>;

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
			const note = await api.post<NoteResponse>('/api/notes', data);
			notesList.refresh();
			saveStatus = 'saved';
			showSavedText = true;
			clearTimeout(savedTextTimer);
			// Navigate to the edit page which handles autosave going forward
			goto(`/notes/${note.id}`);
		} catch (e) {
			console.error('Failed to create note', e);
			toast.error('Failed to create note');
			saveStatus = 'error';
			creating = false;
		}
	}

	// Auto-create: debounced 1s after title + content exist
	let autoCreateTimer: ReturnType<typeof setTimeout>;

	$effect(() => {
		// Track reactive deps
		title;
		blocks;

		if (creating) return;
		clearTimeout(autoCreateTimer);

		if (hasContent()) {
			autoCreateTimer = setTimeout(() => handleCreate(), 1000);
		}

		return () => clearTimeout(autoCreateTimer);
	});

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleCreate();
		}
	}

	function handleContentDblClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (preview) {
			if (target.closest('a')) return;
			preview = false;
		} else {
			if (target.closest('[data-note-block], button, a, input, textarea')) return;
			preview = true;
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex flex-col h-full">
	<!-- Top bar — matches left pane header height -->
	<div class="flex items-center gap-2 px-4 py-3 border-b border-base-300 shrink-0">
		<a href="/notes" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ArrowLeft size={18} />
		</a>
		<!-- svelte-ignore a11y_autofocus -->
		<input
			type="text"
			bind:value={title}
			placeholder="Untitled"
			autofocus
			class="flex-1 min-w-0 font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-0.5 truncate"
		/>
		<button
			class="btn btn-ghost btn-sm"
			onclick={() => handleCreate()}
			disabled={creating || !hasContent()}
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
	</div>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- Scrollable content -->
	<div class="flex-1 overflow-y-auto p-4 md:p-6" ondblclick={handleContentDblClick}>
		<!-- Metadata section -->
		{#if showMeta}
			<div class="mb-4 md:mb-6 rounded-lg border border-base-content/10 bg-base-200/30 p-3 flex flex-col sm:flex-row gap-3">
				<div class="flex-1">
					<span class="text-xs font-medium text-base-content/50 mb-1 block">Tags</span>
					<TagInput bind:tags />
				</div>
				<div class="sm:w-48">
					<span class="text-xs font-medium text-base-content/50 mb-1 block">Project</span>
					<ProjectSelect bind:value={projectId} />
				</div>
			</div>
		{/if}

		<!-- Block Editor -->
		<NoteEditor
			{blocks}
			{preview}
			onchange={(b) => (blocks = b)}
		/>
	</div>
</div>
