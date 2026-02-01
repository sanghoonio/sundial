<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteCreate, NoteResponse, NoteBlock } from '$lib/types';
	import { newBlockId } from '$lib/utils/blocks';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import ProjectSelect from '$lib/components/notes/ProjectSelect.svelte';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
	import { Eye, Pencil } from 'lucide-svelte';

	let title = $state('');
	let blocks = $state<NoteBlock[]>([{ id: newBlockId(), type: 'md', content: '' }]);
	let tags = $state<string[]>([]);
	let projectId = $state<string | null>(null);
	let saving = $state(false);
	let preview = $state(false);

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

<div class="max-w-3xl mx-auto">
	<!-- Top bar -->
	<div class="flex items-center justify-end gap-2 mb-4">
		<button
			class="btn btn-ghost btn-sm"
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

	<!-- Title -->
	<!-- svelte-ignore a11y_autofocus -->
	<div class="mb-4">
		<Input
			placeholder="Note title"
			bind:value={title}
			class="text-xl font-semibold"
			autofocus
		/>
	</div>

	<!-- Tags & Project row -->
	<div class="flex flex-col sm:flex-row gap-3 mb-4">
		<div class="flex-1">
			<TagInput bind:tags />
		</div>
		<div class="sm:w-48">
			<ProjectSelect bind:value={projectId} />
		</div>
	</div>

	<!-- Block Editor -->
	<NoteEditor
		{blocks}
		{preview}
		onchange={(b) => (blocks = b)}
	/>

	<!-- Actions -->
	<div class="flex items-center gap-2 mt-4">
		<Button variant="primary" loading={saving} onclick={handleSave}>Save Note</Button>
		<a href="/notes" class="btn btn-ghost">Cancel</a>
		<span class="text-xs text-base-content/40 ml-2">
			{navigator?.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+S
		</span>
	</div>
</div>
