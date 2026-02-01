<script lang="ts">
	import type { NoteListItem } from '$lib/types';
	import { markdownPreview } from '$lib/utils/markdown';

	interface Props {
		note: NoteListItem;
		selected?: boolean;
	}

	let { note, selected = false }: Props = $props();

	function formatDate(iso: string): string {
		const d = new Date(iso);
		const now = new Date();
		const isToday =
			d.getFullYear() === now.getFullYear() &&
			d.getMonth() === now.getMonth() &&
			d.getDate() === now.getDate();
		if (isToday) {
			return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
		}
		return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	let previewText = $derived(
		note.preview ? markdownPreview(note.preview, 80) : ''
	);
</script>

<a
	href="/notes/{note.id}"
	class="block px-4 md:px-6 py-2.5 border-l-2 transition-colors
		{selected
			? 'bg-primary/10 border-l-primary'
			: 'border-l-transparent hover:bg-base-200'}"
>
	<div class="flex items-baseline gap-2 min-w-0">
		<span class="text-sm font-medium truncate flex-1">{note.title || 'Untitled'}</span>
		<span class="text-xs text-base-content/40 shrink-0">{formatDate(note.updated_at)}</span>
	</div>
	{#if previewText}
		<p class="text-xs text-base-content/50 truncate mt-2.5 mb-2">{previewText}</p>
	{/if}
	{#if note.tags.length > 0}
		<div class="flex gap-1 mt-4 mb-2">
			{#each note.tags.slice(0, 2) as tag}
				<span class="badge badge-xs badge-ghost">{tag}</span>
			{/each}
			{#if note.tags.length > 2}
				<span class="text-xs text-base-content/30">+{note.tags.length - 2}</span>
			{/if}
		</div>
	{/if}
</a>
