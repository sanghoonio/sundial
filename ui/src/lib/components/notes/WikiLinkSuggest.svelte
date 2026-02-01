<script lang="ts">
	import { api } from '$lib/services/api';
	import type { NoteList } from '$lib/types';

	interface Props {
		query: string;
		top: number;
		left: number;
		onselect: (title: string) => void;
		onclose: () => void;
	}

	let { query, top, left, onselect, onclose }: Props = $props();

	let results = $state<{ id: string; title: string }[]>([]);
	let selectedIndex = $state(0);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let wrapperEl = $state<HTMLDivElement>();

	// Fetch matching notes on query change
	$effect(() => {
		const q = query.trim();
		if (debounceTimer) clearTimeout(debounceTimer);
		const delay = q ? 200 : 0; // Show recent notes immediately for empty query
		debounceTimer = setTimeout(async () => {
			try {
				const params = q
					? `search=${encodeURIComponent(q)}&limit=8`
					: 'limit=8';
				const data = await api.get<NoteList>(`/api/notes?${params}`);
				results = data.notes.map((n) => ({ id: n.id, title: n.title }));
				selectedIndex = 0;
			} catch {
				results = [];
			}
		}, delay);
	});

	// Close on click outside
	function handleWindowClick(e: MouseEvent) {
		if (wrapperEl && !wrapperEl.contains(e.target as Node)) {
			onclose();
		}
	}

	export function handleKey(e: KeyboardEvent): boolean {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (results.length > 0) {
				selectedIndex = (selectedIndex + 1) % results.length;
			}
			return true;
		}
		if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (results.length > 0) {
				selectedIndex = (selectedIndex - 1 + results.length) % results.length;
			}
			return true;
		}
		if (e.key === 'Enter') {
			e.preventDefault();
			if (results.length > 0) {
				onselect(results[selectedIndex].title);
			}
			return true;
		}
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose();
			return true;
		}
		return false;
	}
</script>

<svelte:window onclick={handleWindowClick} />

{#if results.length > 0}
	<div
		bind:this={wrapperEl}
		class="absolute z-50 bg-base-100 border border-base-content/20 rounded-lg shadow-lg overflow-hidden max-h-60 w-max max-w-64"
		style="top: {top}px; left: {left}px;"
	>
		<ul class="menu menu-sm p-1 w-full">
			{#each results as item, i}
				<li>
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
					<button
						class="text-left truncate {i === selectedIndex ? 'active' : ''}"
						onmousedown={(e) => { e.preventDefault(); onselect(item.title); }}
						onmouseenter={() => (selectedIndex = i)}
					>
						{item.title}
					</button>
				</li>
			{/each}
		</ul>
	</div>
{/if}
