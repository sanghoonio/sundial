<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteCreate, NoteResponse, NoteBlock } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { ArrowLeft, Eye, Pencil, Info } from 'lucide-svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';

	let title = $state('');
	let blocks = $state<NoteBlock[]>([{ id: newBlockId(), type: 'md', content: '' }]);
	let tags = $state<string[]>([]);
	let projectId = $state<string | null>(null);
	let saving = $state(false);
	let preview = $state(false);
	let showMeta = $state(false);

	async function handleSave() {
		if (!title.trim()) {
			toasts.warning('Title is required');
			return;
		}
		saving = true;
		try {
			const data: NoteCreate = {
				title: title.trim(),
				blocks,
				tags,
				project_id: projectId
			};
			const note = await api.post<NoteResponse>('/api/notes', data);
			notesList.refresh();
			toasts.success('Note created');
			goto(`/notes/${note.id}`);
		} catch {
			toasts.error('Failed to create note');
		} finally {
			saving = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="p-4 md:p-6">
	<!-- Top bar -->
	<div class="flex items-center gap-2 mb-4">
		<a href="/notes" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ArrowLeft size={18} />
		</a>
		<!-- svelte-ignore a11y_autofocus -->
		<input
			type="text"
			bind:value={title}
			placeholder="Untitled"
			autofocus
			class="flex-1 min-w-0 text-lg font-semibold bg-transparent border-none outline-none focus:bg-base-200 rounded px-2 py-1 truncate"
		/>
		<button class="btn btn-primary btn-sm" onclick={handleSave} disabled={saving}>
			{#if saving}
				<span class="loading loading-spinner loading-xs"></span>
			{/if}
			Create
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

	<!-- Metadata section -->
	{#if showMeta}
		<div class="mb-4 rounded-lg border border-base-content/10 bg-base-200/30 p-3 flex flex-col sm:flex-row gap-3">
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
