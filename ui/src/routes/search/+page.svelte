<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { SearchResult, SearchResultItem } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import { Search, FileText, StickyNote } from 'lucide-svelte';

	let query = $state('');
	let results = $state<SearchResult | null>(null);
	let loading = $state(false);
	let hasSearched = $state(false);

	// Initialize from URL query param
	$effect(() => {
		const q = page.url.searchParams.get('q');
		if (q && q !== query) {
			query = q;
		}
	});

	let debounceTimer: ReturnType<typeof setTimeout>;

	function handleInput(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		query = val;
		clearTimeout(debounceTimer);
		if (!val.trim()) {
			results = null;
			hasSearched = false;
			return;
		}
		debounceTimer = setTimeout(() => {
			doSearch(val.trim());
		}, 300);
	}

	async function doSearch(q: string) {
		loading = true;
		hasSearched = true;
		try {
			const params = new URLSearchParams({ q, limit: '50' });
			results = await api.get<SearchResult>(`/api/search?${params}`);
		} catch {
			toasts.error('Search failed');
		} finally {
			loading = false;
		}
	}

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (query.trim()) {
			clearTimeout(debounceTimer);
			doSearch(query.trim());
		}
	}

	function getResultHref(item: SearchResultItem): string {
		// filepath determines what type of result this is
		if (item.filepath.startsWith('notes/')) {
			return `/notes/${item.id}`;
		}
		return `/notes/${item.id}`;
	}
</script>

<div class="max-w-2xl mx-auto">
	<form onsubmit={handleSubmit} class="mb-6">
		<div class="relative">
			<Search size={18} class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40" />
			<!-- svelte-ignore a11y_autofocus -->
			<input
				type="text"
				class="input input-bordered w-full pl-10 text-lg"
				placeholder="Search notes, tasks..."
				value={query}
				oninput={handleInput}
				autofocus
			/>
		</div>
	</form>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<span class="loading loading-spinner loading-lg"></span>
		</div>
	{:else if results && results.results.length > 0}
		<p class="text-sm text-base-content/50 mb-4">
			{results.total} result{results.total === 1 ? '' : 's'} for "{results.query}"
		</p>
		<div class="flex flex-col gap-3">
			{#each results.results as item (item.id)}
				<a href={getResultHref(item)} class="block">
					<Card hoverable compact>
						<div class="flex items-start gap-3">
							<div class="text-base-content/40 mt-0.5">
								<StickyNote size={18} />
							</div>
							<div class="flex-1 min-w-0">
								<h3 class="font-medium">{item.title}</h3>
								{#if item.snippet}
									<p class="text-sm text-base-content/60 mt-1 line-clamp-2">{item.snippet}</p>
								{/if}
								<p class="text-xs text-base-content/40 mt-1">{item.filepath}</p>
							</div>
						</div>
					</Card>
				</a>
			{/each}
		</div>
	{:else if hasSearched}
		<div class="text-center py-12">
			<p class="text-base-content/40">No results found for "{query}"</p>
		</div>
	{:else}
		<div class="text-center py-12">
			<p class="text-base-content/40">Type to search across all your notes and tasks</p>
		</div>
	{/if}
</div>
