<script lang="ts">
	import type { NoteListItem, DashboardNote } from '$lib/types';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		note: NoteListItem | DashboardNote;
		compact?: boolean;
	}

	let { note, compact = false }: Props = $props();

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	let hasTags = $derived('tags' in note && (note as NoteListItem).tags?.length > 0);
	let hasPreview = $derived('preview' in note && !!(note as NoteListItem).preview);
</script>

<a
	href="/notes/{note.id}"
	class="card bg-base-100 border border-base-300 hover:shadow-md transition-shadow"
>
	<div class="card-body {compact ? 'p-3' : 'p-4'}">
		<h3 class="card-title text-base">{note.title}</h3>
		{#if hasPreview && !compact}
			<p class="text-sm text-base-content/60 line-clamp-2">{(note as NoteListItem).preview}</p>
		{/if}
		<div class="flex items-center gap-2 mt-1 flex-wrap">
			{#if hasTags}
				{#each (note as NoteListItem).tags.slice(0, 3) as tag}
					<Badge variant="ghost">{tag}</Badge>
				{/each}
			{/if}
			<span class="text-xs text-base-content/40 ml-auto">
				{formatDate('updated_at' in note ? note.updated_at : '')}
			</span>
		</div>
	</div>
</a>
