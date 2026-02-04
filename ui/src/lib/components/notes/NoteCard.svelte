<script lang="ts">
	import { base } from '$app/paths';
	import type { NoteListItem, DashboardNote } from '$lib/types';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { markdownPreview } from '$lib/utils/markdown';
	import { CheckSquare, Calendar, FolderKanban } from 'lucide-svelte';

	interface Props {
		note: NoteListItem | DashboardNote;
		compact?: boolean;
	}

	let { note, compact = false }: Props = $props();

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
	}

	let isListItem = $derived('tags' in note);
	let listNote = $derived(isListItem ? (note as NoteListItem) : null);
	let hasTags = $derived(listNote && listNote.tags.length > 0);
	let previewText = $derived(
		listNote?.preview ? markdownPreview(listNote.preview, 120) : ''
	);
	let linkedTaskCount = $derived(listNote?.linked_tasks?.length ?? 0);
	let linkedEventCount = $derived(listNote?.linked_events?.length ?? 0);
</script>

{#if compact}
	<a
		href="{base}/notes/{note.id}"
		class="block p-3 rounded-lg bg-base-100 hover:bg-base-100/80 transition-colors"
	>
		<h3 class="text-sm font-medium truncate">{note.title}</h3>
		<span class="text-xs text-base-content/40">{formatDate('updated_at' in note ? note.updated_at : '')}</span>
	</a>
{:else}
	<a
		href="{base}/notes/{note.id}"
		class="card bg-base-100 border border-base-300 hover:shadow-md transition-shadow"
	>
		<div class="card-body p-4">
			<div class="flex items-start gap-2">
				<h3 class="card-title text-base flex-1">{note.title}</h3>
				{#if listNote?.project_id}
					<span title="In project">
						<FolderKanban size={14} class="text-base-content/40" />
					</span>
				{/if}
			</div>
			{#if previewText}
				<p class="text-sm text-base-content/60 line-clamp-2">{previewText}</p>
			{/if}
			<div class="flex items-center gap-2 mt-1 flex-wrap">
				{#if hasTags}
					{#each listNote!.tags.slice(0, 3) as tag}
						<Badge variant="ghost">{tag}</Badge>
					{/each}
					{#if listNote!.tags.length > 3}
						<span class="text-xs text-base-content/40">+{listNote!.tags.length - 3}</span>
					{/if}
				{/if}
				<div class="flex items-center gap-2 ml-auto text-xs text-base-content/40">
					{#if linkedTaskCount > 0}
						<span class="flex items-center gap-0.5" title="{linkedTaskCount} linked tasks">
							<CheckSquare size={11} />
							{linkedTaskCount}
						</span>
					{/if}
					{#if linkedEventCount > 0}
						<span class="flex items-center gap-0.5" title="{linkedEventCount} linked events">
							<Calendar size={11} />
							{linkedEventCount}
						</span>
					{/if}
					<span>{formatDate('updated_at' in note ? note.updated_at : '')}</span>
				</div>
			</div>
		</div>
	</a>
{/if}
