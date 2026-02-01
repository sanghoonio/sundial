<script lang="ts">
	import {
		Search, X, AlertCircle, ArrowDownNarrowWide, ArrowUpNarrowWide,
		CalendarClock
	} from 'lucide-svelte';

	interface Props {
		search: string;
		priorityFilter: string;
		dueDateFilter: string;
		sortBy: string;
		sortDir: string;
		filteredCount: number;
		totalCount: number;
	}

	let {
		search = $bindable(''),
		priorityFilter = $bindable('all'),
		dueDateFilter = $bindable('all'),
		sortBy = $bindable('position'),
		sortDir = $bindable('asc'),
		filteredCount,
		totalCount
	}: Props = $props();

	let searchOpen = $state(false);
	let searchInput = $state<HTMLInputElement | null>(null);

	export function focusSearch() {
		searchOpen = true;
		requestAnimationFrame(() => searchInput?.focus());
	}

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
		searchOpen = false;
	}

	const priorityLabels: Record<string, string> = {
		all: 'All priorities',
		urgent: 'Urgent',
		high: 'High',
		medium: 'Medium',
		low: 'Low'
	};

	const dueDateLabels: Record<string, string> = {
		all: 'Any due date',
		overdue: 'Overdue',
		today: 'Today',
		week: 'This week',
		none: 'No date'
	};

	const sortLabels: Record<string, string> = {
		position: 'Default order',
		due_date: 'Due date',
		priority: 'Priority',
		created_at: 'Date created'
	};

	let hasPriorityFilter = $derived(priorityFilter !== 'all');
	let hasDateFilter = $derived(dueDateFilter !== 'all');
</script>

<div class="flex items-center gap-2">
	<!-- Priority dropdown -->
	<div class="dropdown">
		<button
			tabindex="0"
			class="btn btn-sm {hasPriorityFilter ? 'btn-primary' : 'btn-ghost'}"
			title="Priority filter"
		>
			<AlertCircle size={14} />
			<span class="hidden sm:inline text-xs">{priorityLabels[priorityFilter]}</span>
		</button>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-36 p-1 border border-base-300 mt-1">
			{#each Object.entries(priorityLabels) as [value, label]}
				<li><button class={priorityFilter === value ? 'active' : ''} onclick={() => (priorityFilter = value)}>{label}</button></li>
			{/each}
		</ul>
	</div>

	<!-- Due date dropdown -->
	<div class="dropdown">
		<button
			tabindex="0"
			class="btn btn-sm {hasDateFilter ? 'btn-primary' : 'btn-ghost'}"
			title="Due date filter"
		>
			<CalendarClock size={14} />
			<span class="hidden sm:inline text-xs">{dueDateLabels[dueDateFilter]}</span>
		</button>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-36 p-1 border border-base-300 mt-1">
			{#each Object.entries(dueDateLabels) as [value, label]}
				<li><button class={dueDateFilter === value ? 'active' : ''} onclick={() => (dueDateFilter = value)}>{label}</button></li>
			{/each}
		</ul>
	</div>

	<!-- Sort dropdown -->
	<div class="dropdown">
		<button tabindex="0" class="btn btn-ghost btn-sm" title="Sort">
			{#if sortDir === 'asc'}
				<ArrowDownNarrowWide size={14} />
			{:else}
				<ArrowUpNarrowWide size={14} />
			{/if}
			<span class="text-xs">{sortLabels[sortBy]}</span>
		</button>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-40 p-1 border border-base-300 mt-1">
			{#each Object.entries(sortLabels) as [value, label]}
				<li><button class={sortBy === value ? 'active' : ''} onclick={() => (sortBy = value)}>{label}</button></li>
			{/each}
			<div class="divider my-0"></div>
			<li><button class={sortDir === 'asc' ? 'active' : ''} onclick={() => (sortDir = 'asc')}><ArrowDownNarrowWide size={14} />Ascending</button></li>
			<li><button class={sortDir === 'desc' ? 'active' : ''} onclick={() => (sortDir = 'desc')}><ArrowUpNarrowWide size={14} />Descending</button></li>
		</ul>
	</div>

	<!-- Count badge -->
	{#if filteredCount !== totalCount}
		<span class="badge badge-sm badge-primary">{filteredCount}/{totalCount}</span>
	{/if}

	<!-- Search: button that smoothly expands into an input -->
	<button
		class="btn btn-ghost btn-sm shrink-0 transition-[width] duration-200 !outline-none !shadow-none
			{searchOpen ? 'w-64 bg-base-200' : 'w-auto'}"
		onclick={() => { if (!searchOpen) openSearch(); }}
	>
		<Search size={14} class="shrink-0" />
		{#if searchOpen}
			<!-- svelte-ignore a11y_autofocus -->
			<input
				type="text"
				placeholder="Filter tasks..."
				class="bg-transparent outline-none flex-1 min-w-0 text-sm font-normal"
				bind:value={search}
				bind:this={searchInput}
				onblur={closeSearch}
				onclick={(e) => e.stopPropagation()}
				onkeydown={(e) => { if (e.key === 'Escape') { search = ''; searchOpen = false; } }}
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
</div>
