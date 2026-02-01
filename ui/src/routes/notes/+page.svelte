<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { NoteList, NoteListItem, TagListResponse } from '$lib/types';
	import NoteCard from '$lib/components/notes/NoteCard.svelte';
	import { Plus, Search, ArrowUpDown } from 'lucide-svelte';

	const PAGE_SIZE = 30;

	let notes = $state<NoteListItem[]>([]);
	let total = $state(0);
	let allTags = $state<string[]>([]);
	let search = $state('');
	let selectedTag = $state('');
	let sortBy = $state<'newest' | 'oldest' | 'title_asc' | 'title_desc'>('newest');
	let loading = $state(true);
	let loadingMore = $state(false);
	let offset = $state(0);

	async function load(append = false) {
		if (append) {
			loadingMore = true;
		} else {
			loading = true;
			offset = 0;
		}
		try {
			const params = new URLSearchParams();
			if (selectedTag) params.set('tag', selectedTag);
			params.set('limit', String(PAGE_SIZE));
			params.set('offset', String(append ? offset : 0));
			const qs = params.toString();
			const res = await api.get<NoteList>(`/api/notes${qs ? '?' + qs : ''}`);
			if (append) {
				notes = [...notes, ...res.notes];
			} else {
				notes = res.notes;
			}
			total = res.total;
			offset = notes.length;
		} catch {
			toasts.error('Failed to load notes');
		} finally {
			loading = false;
			loadingMore = false;
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
		// Re-load when tag changes
		selectedTag;
		load();
	});

	// Client-side search filter (backend notes API doesn't have search param)
	let searchLower = $derived(search.trim().toLowerCase());

	let filteredNotes = $derived.by(() => {
		let result = notes;
		if (searchLower) {
			result = result.filter(
				(n) =>
					n.title.toLowerCase().includes(searchLower) ||
					n.preview.toLowerCase().includes(searchLower) ||
					n.tags.some((t) => t.toLowerCase().includes(searchLower))
			);
		}
		return sortNotes(result, sortBy);
	});

	function sortNotes(list: NoteListItem[], sort: typeof sortBy): NoteListItem[] {
		const sorted = [...list];
		switch (sort) {
			case 'newest':
				return sorted.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
			case 'oldest':
				return sorted.sort((a, b) => a.updated_at.localeCompare(b.updated_at));
			case 'title_asc':
				return sorted.sort((a, b) => a.title.localeCompare(b.title));
			case 'title_desc':
				return sorted.sort((a, b) => b.title.localeCompare(a.title));
		}
	}

	let hasMore = $derived(notes.length < total);

	let debounceTimer: ReturnType<typeof setTimeout>;
	function handleSearch(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			search = val;
		}, 200);
	}
</script>

<!-- Search + Actions bar -->
<div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
	<div class="relative flex-1 w-full sm:max-w-sm">
		<Search size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" />
		<input
			type="text"
			class="input input-bordered w-full pl-9 input-sm"
			placeholder="Filter notes..."
			value={search}
			oninput={handleSearch}
		/>
	</div>
	<div class="flex items-center gap-2">
		<select
			class="select select-bordered select-sm"
			bind:value={sortBy}
		>
			<option value="newest">Newest first</option>
			<option value="oldest">Oldest first</option>
			<option value="title_asc">Title A-Z</option>
			<option value="title_desc">Title Z-A</option>
		</select>
		<a href="/notes/new" class="btn btn-primary btn-sm">
			<Plus size={16} />
			New Note
		</a>
	</div>
</div>

<!-- Tag filter chips -->
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

<!-- Notes grid -->
{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if filteredNotes.length > 0}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filteredNotes as note (note.id)}
			<NoteCard {note} />
		{/each}
	</div>

	<!-- Load more -->
	{#if hasMore && !searchLower}
		<div class="flex justify-center mt-6">
			<button
				class="btn btn-ghost btn-sm"
				onclick={() => load(true)}
				disabled={loadingMore}
			>
				{#if loadingMore}
					<span class="loading loading-spinner loading-xs"></span>
				{/if}
				Load more ({notes.length} of {total})
			</button>
		</div>
	{/if}
{:else if searchLower}
	<div class="text-center py-20">
		<p class="text-base-content/40">No notes matching "{search}"</p>
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
