<script lang="ts">
	import { api } from '$lib/services/api';
	import type { TagListResponse } from '$lib/types';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { Plus } from 'lucide-svelte';

	interface Props {
		tags: string[];
		onchange?: (tags: string[]) => void;
	}

	let { tags = $bindable([]), onchange }: Props = $props();

	let input = $state('');
	let adding = $state(false);
	let allTags = $state<string[]>([]);
	let inputEl = $state<HTMLInputElement>();

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
	}

	function removeTag(tag: string) {
		tags = tags.filter((t) => t !== tag);
		onchange?.(tags);
	}

	function startAdding() {
		adding = true;
		queueMicrotask(() => inputEl?.focus());
	}

	function stopAdding() {
		if (input.trim()) addTag(input);
		adding = false;
		input = '';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			if (input.trim()) {
				addTag(input);
				// Keep input open for adding more
				queueMicrotask(() => inputEl?.focus());
			} else {
				stopAdding();
			}
		} else if (e.key === 'Escape') {
			adding = false;
			input = '';
		}
	}
</script>

<div class="flex flex-wrap items-center gap-1">
	{#each tags as tag}
		<Badge variant="primary" removable onremove={() => removeTag(tag)} class="badge-sm">{tag}</Badge>
	{/each}
	{#if adding}
		<span class="badge badge-sm badge-ghost relative">
			<input
				bind:this={inputEl}
				type="text"
				class="w-20 bg-transparent outline-none text-xs"
				placeholder="tag name"
				bind:value={input}
				onkeydown={handleKeydown}
				onblur={() => setTimeout(stopAdding, 150)}
			/>
			{#if filtered.length > 0}
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
		</span>
	{:else}
		<button
			class="badge badge-sm badge-dash cursor-pointer hover:badge-outline"
			onclick={startAdding}
			title="Add tag"
		>
			<Plus size={12} />
		</button>
	{/if}
</div>
