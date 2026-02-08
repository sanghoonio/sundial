<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { SearchResult, SearchResultItem, TaskSearchResultItem } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import { Search, StickyNote, CheckSquare } from 'lucide-svelte';

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
		} catch (e) {
			console.error('Search failed', e);
			toast.error('Search failed');
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

	let hasResults = $derived(
		results && (results.results.length > 0 || results.tasks.length > 0)
	);
</script>

<div class="absolute inset-0 flex flex-col overflow-hidden">
	<!-- Search bar -->
	<div class="flex items-center justify-center px-4 py-6 shrink-0">
		<form onsubmit={handleSubmit} class="w-full max-w-2xl">
			<div class="relative">
				<Search size={18} class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40 z-10 pointer-events-none" />
				<!-- svelte-ignore a11y_autofocus -->
				<input
					type="text"
					class="input input-bordered w-full pl-10"
					placeholder="Search notes, tasks..."
					value={query}
					oninput={handleInput}
					autofocus
				/>
			</div>
		</form>
	</div>

	<!-- Scrollable results -->
	<div class="flex-1 overflow-y-auto p-4">
		<div class="max-w-2xl mx-auto">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<span class="loading loading-spinner loading-lg"></span>
				</div>
			{:else if hasResults}
				<p class="text-sm text-base-content/50 mb-4">
					{results!.total} result{results!.total === 1 ? '' : 's'} for "{results!.query}"
				</p>

				{#if results!.results.length > 0}
					<h3 class="text-xs font-semibold text-base-content/50 uppercase tracking-wide mb-2">Notes</h3>
					<div class="flex flex-col gap-3 mb-6">
						{#each results!.results as item (item.id)}
							<a href="{base}/notes/{item.id}" class="block">
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
										</div>
									</div>
								</Card>
							</a>
						{/each}
					</div>
				{/if}

				{#if results!.tasks.length > 0}
					<h3 class="text-xs font-semibold text-base-content/50 uppercase tracking-wide mb-2">Tasks</h3>
					<div class="flex flex-col gap-3">
						{#each results!.tasks as task (task.id)}
							<a href="{base}/tasks/{task.project_id}" class="block">
								<Card hoverable compact>
									<div class="flex items-start gap-3">
										<div class="text-base-content/40 mt-0.5">
											<CheckSquare size={18} />
										</div>
										<div class="flex-1 min-w-0">
											<h3 class="font-medium">{task.title}</h3>
											{#if task.description}
												<p class="text-sm text-base-content/60 mt-1 line-clamp-2">{task.description}</p>
											{/if}
											<span class="badge badge-xs {task.status === 'done' ? 'badge-success' : 'badge-ghost'} mt-1">{task.status === 'done' ? 'done' : 'in progress'}</span>
										</div>
									</div>
								</Card>
							</a>
						{/each}
					</div>
				{/if}
			{:else if hasSearched}
				<div class="text-center py-10">
					<p class="text-sm text-base-content/40">No results found for "{query}"</p>
				</div>
			{:else}
				<div class="text-center py-10">
					<p class="text-sm text-base-content/40">Type to search across all your notes and tasks</p>
				</div>
			{/if}
		</div>
	</div>
</div>
