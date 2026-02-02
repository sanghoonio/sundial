<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/services/api';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import type { NoteList, NoteListItem, TagListResponse } from '$lib/types';
	import NoteListItemComponent from '$lib/components/notes/NoteListItem.svelte';
	import NoteImportButton from '$lib/components/notes/NoteImportButton.svelte';
	import { Plus, Search, X, ArrowDownNarrowWide, ArrowUpNarrowWide, ArrowDownAZ, ArrowDownZA } from 'lucide-svelte';

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

	// Debounce search to avoid hammering the API
	let activeSearch = $state('');

	$effect(() => {
		const val = search.trim();
		const timer = setTimeout(() => {
			activeSearch = val;
		}, 300);
		return () => clearTimeout(timer);
	});

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
			if (activeSearch) params.set('search', activeSearch);
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
		} catch (e) {
			console.error('Failed to load notes', e);
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
		// Re-fetch when tag/search filter changes or child routes signal a refresh
		selectedTag;
		activeSearch;
		notesList.refreshKey;
		load();
		loadTags();
	});

	let displayNotes = $derived(sortNotes(notes, sortBy));

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

	let searchOpen = $state(false);
	let searchInput = $state<HTMLInputElement | null>(null);

	function openSearch() {
		searchOpen = true;
		requestAnimationFrame(() => searchInput?.focus());
	}

	function closeSearch() {
		if (!search) {
			searchOpen = false;
		}
	}

	function clearSearch(e: MouseEvent) {
		e.preventDefault();
		search = '';
		activeSearch = '';
		searchOpen = false;
	}
</script>

<div class="absolute inset-0 flex overflow-hidden">
	<!-- LEFT PANE: Note list -->
	<div
		class="w-72 lg:w-80 border-r border-base-300 flex-col bg-base-100
			{selectedNoteId || isNewNote ? 'hidden md:flex' : 'flex'}"
	>
		<!-- Header: search + sort + new -->
		<div class="px-4 py-3 border-b border-base-300">
			<div class="flex items-center gap-2">
				<button
					class="btn btn-ghost btn-sm flex-1 justify-start transition-[width] duration-200 !outline-none !shadow-none
						{searchOpen ? 'bg-base-200' : ''}"
					onclick={() => { if (!searchOpen) openSearch(); }}
				>
					<Search size={14} class="shrink-0" />
					{#if searchOpen}
						<!-- svelte-ignore a11y_autofocus -->
						<input
							type="text"
							placeholder="Search notes..."
							class="bg-transparent outline-none flex-1 min-w-0 text-sm font-normal"
							bind:value={search}
							bind:this={searchInput}
							onblur={closeSearch}
							onclick={(e) => e.stopPropagation()}
							onkeydown={(e) => { if (e.key === 'Escape') { clearSearch(e as unknown as MouseEvent); } }}
						/>
						{#if search}
							<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
							<span class="hover:bg-base-content/10 rounded-full p-0.5 shrink-0 cursor-pointer" onmousedown={clearSearch}>
								<X size={12} />
							</span>
						{/if}
					{:else}
						Search
					{/if}
				</button>
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
				<NoteImportButton />
				<a href="/notes/new" class="btn btn-primary btn-sm btn-square" title="New note">
					<Plus size={16} />
				</a>
			</div>
		</div>

		<!-- Tag filter chips -->
		{#if allTags.length > 0}
			<div class="flex gap-1 px-4 py-2 overflow-x-auto border-b border-base-300">
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
			{:else if displayNotes.length > 0}
				{#each displayNotes as note (note.id)}
					<NoteListItemComponent {note} selected={selectedNoteId === note.id} />
				{/each}

				{#if hasMore && !activeSearch}
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
			{:else if activeSearch}
				<p class="text-center text-sm text-base-content/40 py-10">No matches</p>
			{:else}
				<div class="text-center py-10 px-4">
					<p class="text-sm text-base-content/40">No notes found.</p>
				</div>
			{/if}
		</div>
	</div>

	<!-- RIGHT PANE: Content -->
	<div
		class="flex-1 overflow-hidden flex flex-col
			{!selectedNoteId && !isNewNote ? 'hidden md:flex' : 'flex'}"
	>
		<div class="flex-1 flex flex-col overflow-hidden">
			{@render children()}
		</div>
	</div>
</div>
