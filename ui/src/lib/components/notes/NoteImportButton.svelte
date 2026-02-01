<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/services/api';
	import type { NoteCreate, NoteResponse } from '$lib/types';
	import { notesList } from '$lib/stores/noteslist.svelte';
	import { Upload } from 'lucide-svelte';

	let fileInput = $state<HTMLInputElement>();
	let importing = $state(false);

	function trigger() {
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
			goto(`/notes/${note.id}`);
		} catch (e) {
			console.error('Failed to import note', e);
		} finally {
			importing = false;
			// Reset so same file can be re-imported
			input.value = '';
		}
	}

	function parseMarkdown(text: string, filename: string): { title: string; content: string; tags: string[] } {
		let title = filename.replace(/\.(md|markdown|txt)$/i, '');
		let content = text;
		let tags: string[] = [];

		// Try to extract YAML frontmatter
		const fmMatch = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
		if (fmMatch) {
			const frontmatter = fmMatch[1];
			content = fmMatch[2];

			// Extract title from frontmatter
			const titleMatch = frontmatter.match(/^title:\s*["']?(.+?)["']?\s*$/m);
			if (titleMatch) {
				title = titleMatch[1];
			}

			// Extract tags from frontmatter (supports both array and comma-separated)
			const tagsMatch = frontmatter.match(/^tags:\s*\[(.+?)\]\s*$/m);
			if (tagsMatch) {
				tags = tagsMatch[1].split(',').map((t) => t.trim().replace(/^["']|["']$/g, ''));
			} else {
				// YAML list format
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
</script>

<input
	type="file"
	accept=".md,.markdown,.txt"
	class="hidden"
	bind:this={fileInput}
	onchange={handleFile}
/>

<button
	class="btn btn-ghost btn-sm btn-square"
	title="Import note"
	onclick={trigger}
	disabled={importing}
>
	{#if importing}
		<span class="loading loading-spinner loading-xs"></span>
	{:else}
		<Upload size={16} />
	{/if}
</button>
