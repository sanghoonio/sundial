<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteCreate, NoteResponse } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import TagInput from '$lib/components/notes/TagInput.svelte';

	let title = $state('');
	let content = $state('');
	let tags = $state<string[]>([]);
	let saving = $state(false);

	async function handleSave() {
		if (!title.trim()) {
			toasts.warning('Title is required');
			return;
		}
		saving = true;
		try {
			const note = await api.post<NoteResponse>('/api/notes', {
				title: title.trim(),
				content,
				tags
			} satisfies NoteCreate);
			toasts.success('Note created');
			goto(`/notes/${note.id}`);
		} catch {
			toasts.error('Failed to create note');
		} finally {
			saving = false;
		}
	}
</script>

<div class="max-w-3xl mx-auto">
	<div class="mb-4">
		<Input
			placeholder="Note title"
			bind:value={title}
			class="text-xl font-semibold"
			autofocus
		/>
	</div>

	<div class="mb-4">
		<TagInput bind:tags />
	</div>

	<div class="mb-4">
		<textarea
			class="textarea textarea-bordered w-full font-mono text-sm"
			rows="20"
			placeholder="Write your note in markdown..."
			bind:value={content}
		></textarea>
	</div>

	<div class="flex items-center gap-2">
		<Button variant="primary" loading={saving} onclick={handleSave}>
			Save Note
		</Button>
		<a href="/notes" class="btn btn-ghost">Cancel</a>
	</div>
</div>
