<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import { confirmModal } from '$lib/stores/confirm.svelte';
	import type { NoteCreate, NoteList, NoteListItem, NoteResponse, TagListResponse, TagWithCount, ProjectList, ProjectResponse } from '$lib/types';
	import NoteListItemComponent from '$lib/components/notes/NoteListItem.svelte';
	import { Plus, Search, X, ArrowDownNarrowWide, ArrowUpNarrowWide, ArrowDownAZ, ArrowDownZA, ChevronDown, BookOpen, Upload, FolderKanban, Tag } from 'lucide-svelte';
	import { fullscreen } from '$lib/stores/fullscreen.svelte';

	let { children } = $props();

	const PAGE_SIZE = 30;

	let notes = $state<NoteListItem[]>([]);
	let total = $state(0);
	let tagsWithCount = $state<TagWithCount[]>([]);
	let projects = $state<ProjectResponse[]>([]);
	let search = $state('');
	let selectedTag = $state('');
	let selectedProject = $state('');
	let tagSearch = $state('');
	let sortBy = $state<'newest' | 'oldest' | 'title_asc' | 'title_desc'>('newest');
	let loading = $state(true);
	let loadingMore = $state(false);
	let offset = $state(0);

	let selectedNoteId = $derived(page.params.id ?? null);
	let isNewNote = $derived(page.params.id === 'new');

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
			if (selectedProject) params.set('project_id', selectedProject);
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
			toast.error('Failed to load notes');
		} finally {
			loading = false;
			loadingMore = false;
		}
	}

	async function loadTags() {
		try {
			const res = await api.get<TagListResponse>('/api/tags');
			tagsWithCount = res.tags;
		} catch {
			// ignore
		}
	}

	async function loadProjects() {
		try {
			const res = await api.get<ProjectList>('/api/projects');
			projects = res.projects;
		} catch {
			// ignore
		}
	}

	$effect(() => {
		// Re-fetch when tag/search/project filter changes or child routes signal a refresh
		selectedTag;
		selectedProject;
		activeSearch;
		notesList.refreshKey;
		load();
		loadTags();
		loadProjects();
	});

	// In-place patch: update a single note in the list without a full re-fetch
	$effect(() => {
		const patched = notesList.patchedNote;
		if (!patched) return;
		// untrack so reading/writing `notes` doesn't become a dependency (would cause infinite loop)
		untrack(() => {
			const idx = notes.findIndex((n) => n.id === patched.id);
			if (idx !== -1) {
				notes[idx] = patched;
				notes = [...notes];
			}
			loadTags();
		});
	});

	let filteredTags = $derived(
		tagSearch
			? tagsWithCount.filter((t) => t.name.toLowerCase().includes(tagSearch.toLowerCase()))
			: tagsWithCount
	);

	let selectedProjectData = $derived(projects.find((p) => p.id === selectedProject));
	let selectedTagData = $derived(tagsWithCount.find((t) => t.name === selectedTag));

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

	// --- Import functionality ---
	let fileInput = $state<HTMLInputElement>();
	let importing = $state(false);

	function triggerImport() {
		fileInput?.click();
	}

	async function handleFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		importing = true;
		try {
			const text = await file.text();
			const { title, content, tags } = parseMarkdown(text, file.name);

			const data: NoteCreate = { title, content, tags };
			const note = await api.post<NoteResponse>('/api/notes', data);
			notesList.refresh();
			goto(`${base}/notes/${note.id}`);
		} catch (e) {
			console.error('Failed to import note', e);
			toast.error('Failed to import note');
		} finally {
			importing = false;
			input.value = '';
		}
	}

	function parseMarkdown(text: string, filename: string): { title: string; content: string; tags: string[] } {
		let title = filename.replace(/\.(md|markdown|txt)$/i, '');
		let content = text;
		let tags: string[] = [];

		const fmMatch = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
		if (fmMatch) {
			const frontmatter = fmMatch[1];
			content = fmMatch[2];

			const titleMatch = frontmatter.match(/^title:\s*["']?(.+?)["']?\s*$/m);
			if (titleMatch) {
				title = titleMatch[1];
			}

			const tagsMatch = frontmatter.match(/^tags:\s*\[(.+?)\]\s*$/m);
			if (tagsMatch) {
				tags = tagsMatch[1].split(',').map((t) => t.trim().replace(/^["']|["']$/g, ''));
			} else {
				const tagListMatch = frontmatter.match(/^tags:\s*\n((?:\s*-\s*.+\n?)+)/m);
				if (tagListMatch) {
					tags = tagListMatch[1]
						.split('\n')
						.map((line) => line.replace(/^\s*-\s*/, '').trim())
						.filter(Boolean);
				}
			}
		}

		return { title, content: content.trim(), tags };
	}

	// --- Journal creation ---
	interface JournalData {
		date: string;
		notes_created: { id: string; title: string; updated_at: string }[];
		notes_updated: { id: string; title: string; updated_at: string }[];
		tasks_created: { id: string; title: string; status: string; priority: string; due_date: string | null; project_id: string }[];
		tasks_completed: { id: string; title: string; status: string; priority: string; due_date: string | null; project_id: string }[];
		events: { id: string; title: string; start_time: string; end_time: string | null; all_day: boolean }[];
	}

	let creatingJournal = $state(false);

	async function createJournal() {
		creatingJournal = true;
		try {
			const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
			const data = await api.get<JournalData>(`/api/dashboard/journal-data?tz=${encodeURIComponent(tz)}`);
			const content = generateJournalTemplate(data);
			const formattedDate = formatJournalDate(data.date);

			const noteData: NoteCreate = {
				title: `${data.date}: Daily Journal`,
				content,
				tags: ['journal', 'daily']
			};
			const note = await api.post<NoteResponse>('/api/notes', noteData);
			notesList.refresh();
			goto(`${base}/notes/${note.id}`);
		} catch (e) {
			console.error('Failed to create journal', e);
			toast.error('Failed to create journal');
		} finally {
			creatingJournal = false;
		}
	}

	function formatJournalDate(dateStr: string): string {
		const date = new Date(dateStr + 'T00:00:00');
		return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
	}

	function formatEventTime(startTime: string, endTime: string | null, allDay: boolean): string {
		if (allDay) return 'All day';
		const start = new Date(startTime);
		const startStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
		if (!endTime) return startStr;
		const end = new Date(endTime);
		const endStr = end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
		return `${startStr} - ${endStr}`;
	}

	function generateJournalTemplate(data: JournalData): string {
		const lines: string[] = [];
		const formattedDate = formatJournalDate(data.date);

		lines.push(`# ${data.date}: Daily Journal`);
		lines.push('');
		lines.push('## Today\'s Activity');
		lines.push('');

		// Events
		if (data.events.length > 0) {
			lines.push('**Events:**');
			for (const event of data.events) {
				const time = formatEventTime(event.start_time, event.end_time, event.all_day);
				lines.push(`- ${event.title} (${time})`);
			}
			lines.push('');
		}

		// Tasks Completed
		if (data.tasks_completed.length > 0) {
			lines.push('**Tasks Completed:**');
			for (const task of data.tasks_completed) {
				lines.push(`- [[task:${task.id}|${task.title}]]`);
			}
			lines.push('');
		}

		// Tasks Added
		if (data.tasks_created.length > 0) {
			lines.push('**Tasks Added:**');
			for (const task of data.tasks_created) {
				lines.push(`- [[task:${task.id}|${task.title}]]`);
			}
			lines.push('');
		}

		// Notes Updated
		if (data.notes_updated.length > 0) {
			lines.push('**Notes Updated:**');
			for (const note of data.notes_updated) {
				lines.push(`- [[${note.title}]]`);
			}
			lines.push('');
		}

		// Notes Created
		if (data.notes_created.length > 0) {
			lines.push('**Notes Created:**');
			for (const note of data.notes_created) {
				lines.push(`- [[${note.title}]]`);
			}
			lines.push('');
		}

		// Check if there was any activity
		const hasActivity = data.events.length > 0 || data.tasks_completed.length > 0 ||
			data.tasks_created.length > 0 || data.notes_updated.length > 0 || data.notes_created.length > 0;

		if (!hasActivity) {
			lines.push('*No recorded activity for today.*');
			lines.push('');
		}

		lines.push('---');
		lines.push('');
		lines.push('## Reflections');
		lines.push('');
		lines.push('');

		return lines.join('\n');
	}

	// --- Delete from list ---
	async function handleDeleteNote(noteId: string) {
		const confirmed = await confirmModal.confirm({
			title: 'Delete Note',
			message: 'Are you sure you want to delete this note?',
			confirmText: 'Delete',
			variant: 'danger'
		});
		if (!confirmed) return;
		try {
			await api.delete(`/api/notes/${noteId}`);
			notesList.refresh();
			if (selectedNoteId === noteId) {
				goto(`${base}/notes`);
			}
		} catch (e) {
			console.error('Failed to delete note', e);
			toast.error('Failed to delete note');
		}
	}
</script>

<div class="absolute inset-0 flex overflow-hidden">
	<!-- LEFT PANE: Note list -->
	<div
		class="w-full md:w-72 lg:w-80 border-r border-base-300 flex-col bg-base-100
			{fullscreen.active ? 'hidden' : selectedNoteId || isNewNote ? 'hidden md:flex' : 'flex'}"
	>
		<!-- Header: search + new -->
		<div class="px-4 py-3 border-b border-base-300 shrink-0">
			<div class="flex items-center gap-2 h-8">
				<button
					class="btn btn-ghost btn-sm flex-1 min-w-0 justify-start transition-[width] duration-200 !outline-none !shadow-none
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
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<span class="hover:bg-base-content/10 rounded-full p-0.5 shrink-0 cursor-pointer" onmousedown={clearSearch}>
								<X size={12} />
							</span>
						{/if}
					{:else}
						Search
					{/if}
				</button>
				<div class="join shrink-0">
					<a href="{base}/notes/new" class="btn btn-primary btn-sm btn-square join-item" title="New note">
						<Plus size={16} />
					</a>
					<div class="dropdown dropdown-end">
						<button tabindex="0" class="btn btn-primary btn-sm join-item px-1 min-w-0 w-6">
							<ChevronDown size={12} />
						</button>
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-44 p-1 border border-base-300 mt-1">
							<li>
								<button onclick={createJournal} disabled={creatingJournal}>
									{#if creatingJournal}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<BookOpen size={14} />
									{/if}
									Daily journal
								</button>
							</li>
							<li>
								<button onclick={triggerImport} disabled={importing}>
									{#if importing}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<Upload size={14} />
									{/if}
									Import markdown
								</button>
							</li>
						</ul>
					</div>
				</div>
				<input
					type="file"
					accept=".md,.markdown,.txt"
					class="hidden"
					bind:this={fileInput}
					onchange={handleFile}
				/>
			</div>
		</div>

		<!-- Filter row: Project + Tag + Sort dropdowns -->
		<div class="flex items-center justify-between px-4 py-2 border-b border-base-300 min-w-0">
			<!-- Project filter dropdown -->
			<div class="dropdown dropdown-start min-w-0">
				<button tabindex="0" class="btn btn-ghost btn-xs gap-1 min-w-0 {selectedProject ? 'btn-active' : ''}">
					{#if selectedProjectData}
						<span class="w-2 h-2 rounded-full shrink-0" style:background-color={selectedProjectData.color}></span>
						<span class="truncate max-w-12">{selectedProjectData.name}</span>
					{:else}
						<FolderKanban size={12} class="shrink-0" />
						<span>Project</span>
					{/if}
					<ChevronDown size={10} class="shrink-0 opacity-50" />
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-48 p-1 border border-base-300 mt-1 max-h-60 overflow-y-auto flex-nowrap">
					<li>
						<button class={selectedProject === '' ? 'active' : ''} onclick={() => { selectedProject = ''; (document.activeElement as HTMLElement)?.blur(); }}>
							All projects
						</button>
					</li>
					{#each projects as project}
						<li>
							<button
								class={selectedProject === project.id ? 'active' : ''}
								onclick={() => { selectedProject = selectedProject === project.id ? '' : project.id; (document.activeElement as HTMLElement)?.blur(); }}
							>
								<span class="w-2 h-2 rounded-full shrink-0" style:background-color={project.color}></span>
								<span class="truncate">{project.name}</span>
							</button>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Tag filter dropdown -->
			<div class="dropdown dropdown-start min-w-0">
				<button tabindex="0" class="btn btn-ghost btn-xs gap-1 min-w-0 {selectedTag ? 'btn-active' : ''}">
					{#if selectedTagData}
						<Tag size={12} class="shrink-0" />
						<span class="truncate max-w-12">{selectedTagData.name}</span>
					{:else}
						<Tag size={12} class="shrink-0" />
						<span>Tag</span>
					{/if}
					<ChevronDown size={10} class="shrink-0 opacity-50" />
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div tabindex="0" class="dropdown-content bg-base-100 rounded-box shadow-lg z-10 w-52 border border-base-300 mt-1 overflow-x-hidden">
					<div class="p-2 border-b border-base-300">
						<input
							type="text"
							placeholder="Search tags..."
							class="input input-xs input-bordered w-full"
							bind:value={tagSearch}
							onclick={(e) => e.stopPropagation()}
						/>
					</div>
					<ul class="menu menu-sm p-1 max-h-48 overflow-y-auto overflow-x-hidden flex-nowrap w-full">
						<li>
							<button class="w-full {selectedTag === '' ? 'active' : ''}" onclick={() => { selectedTag = ''; tagSearch = ''; }}>
								All tags
							</button>
						</li>
						{#each filteredTags as tag}
							<li>
								<button
									class="w-full justify-between {selectedTag === tag.name ? 'active' : ''}"
									onclick={() => { selectedTag = selectedTag === tag.name ? '' : tag.name; tagSearch = ''; }}
								>
									<span class="truncate">{tag.name}</span>
									<span class="badge badge-xs badge-ghost">{tag.count}</span>
								</button>
							</li>
						{/each}
						{#if filteredTags.length === 0 && tagSearch}
							<li class="text-xs text-base-content/50 px-3 py-2">No tags match "{tagSearch}"</li>
						{/if}
					</ul>
				</div>
			</div>

			<!-- Sort dropdown -->
			<div class="dropdown dropdown-end min-w-0">
				<button tabindex="0" class="btn btn-ghost btn-xs gap-1 min-w-0">
					{#if sortBy === 'newest'}
						<ArrowDownNarrowWide size={12} class="shrink-0" />
						<span>Newest</span>
					{:else if sortBy === 'oldest'}
						<ArrowUpNarrowWide size={12} class="shrink-0" />
						<span>Oldest</span>
					{:else if sortBy === 'title_asc'}
						<ArrowDownAZ size={12} class="shrink-0" />
						<span>A-Z</span>
					{:else}
						<ArrowDownZA size={12} class="shrink-0" />
						<span>Z-A</span>
					{/if}
					<ChevronDown size={10} class="shrink-0 opacity-50" />
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<ul tabindex="0" class="dropdown-content menu grid-cols-1 bg-base-100 rounded-box shadow-lg z-10 w-36 p-1 border border-base-300 mt-1 overflow-x-hidden">
					<li>
						<button class={sortBy === 'newest' ? 'active' : ''} onclick={() => (sortBy = 'newest')}>
							<ArrowDownNarrowWide size={12} />Newest
						</button>
					</li>
					<li>
						<button class={sortBy === 'oldest' ? 'active' : ''} onclick={() => (sortBy = 'oldest')}>
							<ArrowUpNarrowWide size={12} />Oldest
						</button>
					</li>
					<li>
						<button class={sortBy === 'title_asc' ? 'active' : ''} onclick={() => (sortBy = 'title_asc')}>
							<ArrowDownAZ size={12} />Title A-Z
						</button>
					</li>
					<li>
						<button class={sortBy === 'title_desc' ? 'active' : ''} onclick={() => (sortBy = 'title_desc')}>
							<ArrowDownZA size={12} />Title Z-A
						</button>
					</li>
				</ul>
			</div>
		</div>

		<!-- Scrollable note list -->
		<div class="flex-1 overflow-y-auto overscroll-x-contain">
			{#if loading}
				<div class="flex items-center justify-center py-10">
					<span class="loading loading-spinner loading-md"></span>
				</div>
			{:else if displayNotes.length > 0}
				{#each displayNotes as note (note.id)}
					<NoteListItemComponent {note} selected={selectedNoteId === note.id} ondelete={handleDeleteNote} />
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
