<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteResponse, NoteUpdate, BacklinksResponse } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import TagInput from '$lib/components/notes/TagInput.svelte';
	import { ArrowLeft, Trash2, Eye, Pencil } from 'lucide-svelte';

	let note = $state<NoteResponse | null>(null);
	let backlinks = $state<BacklinksResponse | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let preview = $state(false);

	let title = $state('');
	let content = $state('');
	let tags = $state<string[]>([]);

	let noteId = $derived(page.params.id);

	async function load() {
		loading = true;
		try {
			const [n, bl] = await Promise.all([
				api.get<NoteResponse>(`/api/notes/${noteId}`),
				api.get<BacklinksResponse>(`/api/notes/${noteId}/backlinks`)
			]);
			note = n;
			backlinks = bl;
			title = n.title;
			content = n.content;
			tags = [...n.tags];
		} catch {
			toasts.error('Failed to load note');
			goto('/notes');
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		noteId;
		load();
	});

	async function handleSave() {
		if (!title.trim()) {
			toasts.warning('Title is required');
			return;
		}
		saving = true;
		try {
			const update: NoteUpdate = { title: title.trim(), content, tags };
			note = await api.put<NoteResponse>(`/api/notes/${noteId}`, update);
			toasts.success('Note saved');
		} catch {
			toasts.error('Failed to save note');
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!confirm('Delete this note?')) return;
		try {
			await api.delete(`/api/notes/${noteId}`);
			toasts.success('Note deleted');
			goto('/notes');
		} catch {
			toasts.error('Failed to delete note');
		}
	}

	let hasBacklinks = $derived(
		backlinks && (backlinks.notes.length > 0 || backlinks.tasks.length > 0)
	);
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if note}
	<div class="max-w-3xl mx-auto">
		<div class="flex items-center gap-2 mb-4">
			<a href="/notes" class="btn btn-ghost btn-sm btn-square">
				<ArrowLeft size={18} />
			</a>
			<div class="flex-1"></div>
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
			<button class="btn btn-ghost btn-sm text-error" onclick={handleDelete}>
				<Trash2 size={16} />
			</button>
		</div>

		<div class="mb-4">
			<Input
				placeholder="Note title"
				bind:value={title}
				class="text-xl font-semibold"
			/>
		</div>

		<div class="mb-4">
			<TagInput bind:tags />
		</div>

		{#if preview}
			<div class="prose prose-sm max-w-none bg-base-100 border border-base-300 rounded-lg p-4 min-h-64">
				{@html content
					.replace(/&/g, '&amp;')
					.replace(/</g, '&lt;')
					.replace(/>/g, '&gt;')
					.replace(/\n/g, '<br>')}
			</div>
		{:else}
			<div class="mb-4">
				<textarea
					class="textarea textarea-bordered w-full font-mono text-sm"
					rows="20"
					placeholder="Write your note in markdown..."
					bind:value={content}
				></textarea>
			</div>
		{/if}

		<div class="flex items-center gap-2 mt-4">
			<Button variant="primary" loading={saving} onclick={handleSave}>
				Save
			</Button>
		</div>

		<!-- Linked items -->
		{#if note.linked_tasks.length > 0 || note.linked_events.length > 0}
			<div class="mt-8 border-t border-base-300 pt-4">
				<h3 class="font-semibold mb-2 text-sm text-base-content/60">Linked Items</h3>
				{#if note.linked_tasks.length > 0}
					<p class="text-sm text-base-content/60">{note.linked_tasks.length} linked task(s)</p>
				{/if}
				{#if note.linked_events.length > 0}
					<p class="text-sm text-base-content/60">{note.linked_events.length} linked event(s)</p>
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
