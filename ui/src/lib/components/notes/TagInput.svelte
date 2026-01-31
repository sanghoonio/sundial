<script lang="ts">
	import { api } from '$lib/services/api';
	import type { TagListResponse } from '$lib/types';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		tags: string[];
		onchange?: (tags: string[]) => void;
	}

	let { tags = $bindable([]), onchange }: Props = $props();

	let input = $state('');
	let suggestions = $state<string[]>([]);
	let allTags = $state<string[]>([]);
	let showSuggestions = $state(false);

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

	let filtered = $derived(
		input.trim()
			? allTags.filter(
					(t) => t.toLowerCase().includes(input.toLowerCase()) && !tags.includes(t)
				)
			: []
	);

	function addTag(tag: string) {
		const trimmed = tag.trim().toLowerCase();
		if (trimmed && !tags.includes(trimmed)) {
			tags = [...tags, trimmed];
			onchange?.(tags);
		}
		input = '';
		showSuggestions = false;
	}

	function removeTag(tag: string) {
		tags = tags.filter((t) => t !== tag);
		onchange?.(tags);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			if (input.trim()) addTag(input);
		} else if (e.key === 'Backspace' && !input && tags.length > 0) {
			removeTag(tags[tags.length - 1]);
		}
	}
</script>

<div class="flex flex-wrap items-center gap-1 p-2 border border-base-300 rounded-lg bg-base-100 min-h-10">
	{#each tags as tag}
		<Badge variant="primary" removable onremove={() => removeTag(tag)}>{tag}</Badge>
	{/each}
	<div class="relative flex-1 min-w-24">
		<input
			type="text"
			class="w-full bg-transparent outline-none text-sm px-1 py-0.5"
			placeholder={tags.length === 0 ? 'Add tags...' : ''}
			bind:value={input}
			onkeydown={handleKeydown}
			onfocus={() => (showSuggestions = true)}
			onblur={() => setTimeout(() => (showSuggestions = false), 150)}
		/>
		{#if showSuggestions && filtered.length > 0}
			<ul class="absolute left-0 top-full mt-1 bg-base-100 border border-base-300 rounded-lg shadow-lg z-10 w-48 max-h-40 overflow-auto">
				{#each filtered.slice(0, 8) as suggestion}
					<li>
						<button
							class="w-full text-left px-3 py-1.5 text-sm hover:bg-base-200 cursor-pointer"
							onmousedown={() => addTag(suggestion)}
						>
							{suggestion}
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
