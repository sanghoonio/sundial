<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import type { NoteList, NoteListItem, TagListResponse } from '$lib/types';
	import NoteListItemComponent from '$lib/components/notes/NoteListItem.svelte';
	import { Plus, Search, ArrowDownNarrowWide, ArrowUpNarrowWide, ArrowDownAZ, ArrowDownZA } from 'lucide-svelte';

	let { children } = $props();

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

	let selectedNoteId = $derived(page.params.id ?? null);
	let isNewNote = $derived(page.url.pathname === '/notes/new');

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
		// Re-fetch when tag filter changes or child routes signal a refresh
		selectedTag;
		notesList.refreshKey;
		load();
		loadTags();
	});

	// Client-side search filter
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

<div class="absolute inset-0 flex overflow-hidden">
	<!-- LEFT PANE: Note list -->
	<div
		class="w-72 lg:w-80 border-r border-base-300 flex-col bg-base-100
			{selectedNoteId || isNewNote ? 'hidden md:flex' : 'flex'}"
	>
		<!-- Header: search + sort + new -->
		<div class="py-4 md:py-6 px-4 md:px-6 border-b border-base-300">
			<div class="flex items-center gap-2">
				<label class="input input-bordered input-sm w-full flex-1">
					<Search size={14} class="text-base-content/40" />
					<input
						type="text"
						placeholder="Filter notes..."
						value={search}
						oninput={handleSearch}
					/>
				</label>
				<div class="dropdown dropdown-end">
					<button tabindex="0" class="btn btn-ghost btn-sm btn-square" title="Sort">
						{#if sortBy === 'newest'}
							<ArrowDownNarrowWide size={14} />
						{:else if sortBy === 'oldest'}
							<ArrowUpNarrowWide size={14} />
						{:else if sortBy === 'title_asc'}
							<ArrowDownAZ size={14} />
						{:else}
							<ArrowDownZA size={14} />
						{/if}
					</button>
					<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
					<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-44 p-1 border border-base-300 mt-1">
						<li><button class={sortBy === 'newest' ? 'active' : ''} onclick={() => (sortBy = 'newest')}><ArrowDownNarrowWide size={14} />Newest first</button></li>
						<li><button class={sortBy === 'oldest' ? 'active' : ''} onclick={() => (sortBy = 'oldest')}><ArrowUpNarrowWide size={14} />Oldest first</button></li>
						<li><button class={sortBy === 'title_asc' ? 'active' : ''} onclick={() => (sortBy = 'title_asc')}><ArrowDownAZ size={14} />Title A-Z</button></li>
						<li><button class={sortBy === 'title_desc' ? 'active' : ''} onclick={() => (sortBy = 'title_desc')}><ArrowDownZA size={14} />Title Z-A</button></li>
					</ul>
				</div>
				<a href="/notes/new" class="btn btn-primary btn-sm btn-square" title="New note">
					<Plus size={16} />
				</a>
			</div>
		</div>

		<!-- Tag filter chips -->
		{#if allTags.length > 0}
			<div class="flex gap-1 px-4 md:px-6 py-2 overflow-x-auto border-b border-base-300">
				<button
					class="badge badge-xs cursor-pointer shrink-0 {selectedTag === '' ? 'badge-primary' : 'badge-ghost'}"
					onclick={() => (selectedTag = '')}
				>
					All
				</button>
				{#each allTags as tag}
					<button
						class="badge badge-xs cursor-pointer shrink-0 {selectedTag === tag ? 'badge-primary' : 'badge-ghost'}"
						onclick={() => (selectedTag = selectedTag === tag ? '' : tag)}
					>
						{tag}
					</button>
				{/each}
			</div>
		{/if}

		<!-- Scrollable note list -->
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex items-center justify-center py-10">
					<span class="loading loading-spinner loading-md"></span>
				</div>
			{:else if filteredNotes.length > 0}
				{#each filteredNotes as note (note.id)}
					<NoteListItemComponent {note} selected={selectedNoteId === note.id} />
				{/each}

				{#if hasMore && !searchLower}
					<div class="flex justify-center py-3">
						<button
							class="btn btn-ghost btn-xs"
							onclick={() => load(true)}
							disabled={loadingMore}
						>
							{#if loadingMore}
								<span class="loading loading-spinner loading-xs"></span>
							{/if}
							More ({notes.length}/{total})
						</button>
					</div>
				{/if}
			{:else if searchLower}
				<p class="text-center text-sm text-base-content/40 py-10">No matches</p>
			{:else}
				<div class="text-center py-10 px-4">
					<p class="text-sm text-base-content/40 mb-3">No notes yet</p>
					<a href="/notes/new" class="btn btn-primary btn-sm">
						<Plus size={14} />
						Create note
					</a>
				</div>
			{/if}
		</div>
	</div>

	<!-- RIGHT PANE: Content -->
	<div
		class="flex-1 overflow-y-auto
			{!selectedNoteId && !isNewNote ? 'hidden md:flex' : 'flex'}"
	>
		<div class="flex-1">
			{@render children()}
		</div>
	</div>
</div>
