<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteList, TagListResponse } from '$lib/types';
	import NoteCard from '$lib/components/notes/NoteCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import { Plus, Search } from 'lucide-svelte';

	let notes = $state<NoteList | null>(null);
	let allTags = $state<string[]>([]);
	let search = $state('');
	let selectedTag = $state('');
	let loading = $state(true);

	async function load() {
		loading = true;
		try {
			const params = new URLSearchParams();
			if (search.trim()) params.set('search', search.trim());
			if (selectedTag) params.set('tag', selectedTag);
			params.set('limit', '50');
			const qs = params.toString();
			notes = await api.get<NoteList>(`/api/notes${qs ? '?' + qs : ''}`);
		} catch {
			toasts.error('Failed to load notes');
		} finally {
			loading = false;
		}
	}

	async function loadTags() {
		try {
			const res = await api.get<TagListResponse>('/api/tags');
			allTags = res.tags.map((t) => t.name);
		} catch {
			// ignore
		}
	}

	$effect(() => {
		loadTags();
	});

	$effect(() => {
		// Re-run when search or selectedTag changes
		search;
		selectedTag;
		load();
	});

	let debounceTimer: ReturnType<typeof setTimeout>;
	function handleSearch(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			search = val;
		}, 300);
	}
</script>

<div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
	<div class="relative flex-1 w-full sm:max-w-sm">
		<Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" />
		<input
			type="text"
			class="input input-bordered w-full pl-9"
			placeholder="Search notes..."
			value={search}
			oninput={handleSearch}
		/>
	</div>
	<a href="/notes/new" class="btn btn-primary btn-sm">
		<Plus size={16} />
		New Note
	</a>
</div>

{#if allTags.length > 0}
	<div class="flex flex-wrap gap-1.5 mb-4">
		<button
			class="badge cursor-pointer {selectedTag === '' ? 'badge-primary' : 'badge-ghost'}"
			onclick={() => (selectedTag = '')}
		>
			All
		</button>
		{#each allTags as tag}
			<button
				class="badge cursor-pointer {selectedTag === tag ? 'badge-primary' : 'badge-ghost'}"
				onclick={() => (selectedTag = selectedTag === tag ? '' : tag)}
			>
				{tag}
			</button>
		{/each}
	</div>
{/if}

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if notes && notes.notes.length > 0}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each notes.notes as note (note.id)}
			<NoteCard {note} />
		{/each}
	</div>
{:else}
	<div class="text-center py-20">
		<p class="text-base-content/40 mb-4">No notes found</p>
		<a href="/notes/new" class="btn btn-primary btn-sm">
			<Plus size={16} />
			Create your first note
		</a>
	</div>
{/if}
