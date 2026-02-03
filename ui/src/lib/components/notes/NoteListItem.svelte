<script lang="ts">
	import type { NoteListItem } from '$lib/types';
	import { markdownPreview } from '$lib/utils/markdown';
	import { Trash2 } from 'lucide-svelte';

	interface Props {
		note: NoteListItem;
		selected?: boolean;
		ondelete?: (noteId: string) => void;
	}

	let { note, selected = false, ondelete }: Props = $props();

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

	// Swipe-to-delete state
	let swipeRevealed = $state(false);
	let swipeOffset = $state(0); // Real-time offset during swipe
	let isSettling = $state(false); // True when animating to final position
	let hideTimeout: ReturnType<typeof setTimeout>;
	let settleTimeout: ReturnType<typeof setTimeout>;
	let containerEl: HTMLDivElement;

	const MAX_OFFSET = 64;

	// Use non-passive listener to allow preventDefault
	$effect(() => {
		if (!containerEl) return;
		containerEl.addEventListener('wheel', handleWheel, { passive: false });
		return () => containerEl.removeEventListener('wheel', handleWheel);
	});

	function handleWheel(e: WheelEvent) {
		// Only respond to primarily horizontal scroll (two-finger swipe)
		if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) {
			return;
		}

		// Prevent browser rubber-band scrolling
		e.preventDefault();
		isSettling = false;

		// Update offset in real-time (negative = swiped left = reveal trash)
		swipeOffset = Math.max(-MAX_OFFSET, Math.min(0, swipeOffset - e.deltaX));

		// Settle after gesture ends
		clearTimeout(settleTimeout);
		settleTimeout = setTimeout(() => {
			isSettling = true;
			// Snap to revealed or hidden based on position
			if (swipeOffset < -MAX_OFFSET / 2) {
				swipeRevealed = true;
				swipeOffset = -MAX_OFFSET;
				resetHideTimer();
			} else {
				swipeRevealed = false;
				swipeOffset = 0;
				clearTimeout(hideTimeout);
			}
		}, 100);
	}

	function resetHideTimer() {
		clearTimeout(hideTimeout);
		hideTimeout = setTimeout(() => {
			isSettling = true;
			swipeRevealed = false;
			swipeOffset = 0;
		}, 10000);
	}

	function handleDelete(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		swipeRevealed = false;
		swipeOffset = 0;
		clearTimeout(hideTimeout);
		ondelete?.(note.id);
	}
</script>

<div class="overflow-hidden" bind:this={containerEl} style="overscroll-behavior-x: contain; touch-action: pan-y;">
	<!-- Sliding wrapper containing content + trash -->
	<div
		class="flex {isSettling ? 'transition-transform duration-150' : ''}"
		style:transform="translateX({swipeOffset}px)"
	>
		<!-- Content -->
		<a
			href="/notes/{note.id}"
			class="block flex-1 min-w-full px-4 py-2.5 border-l-2
				{selected
					? 'bg-primary/10 border-l-primary'
					: 'bg-base-100 border-l-transparent hover:bg-base-200'}"
		>
		<div class="flex items-baseline gap-2 min-w-0">
			<span class="text-sm font-medium truncate flex-1">{note.title || 'Untitled'}</span>
			<span class="text-xs text-base-content/40 shrink-0">{formatDate(note.updated_at)}</span>
		</div>
		{#if previewText}
			<p class="text-xs text-base-content/50 truncate mt-1.5 mb-0.5">{previewText}</p>
		{/if}
		{#if note.tags.length > 0 || note.linked_tasks.length > 0}
			<div class="flex gap-1 mt-2 mb-0.5 items-center">
				{#if note.linked_tasks.length > 0}
					<span class="badge badge-xs badge-outline gap-0.5">{note.linked_tasks.length} task{note.linked_tasks.length > 1 ? 's' : ''}</span>
				{/if}
				{#each note.tags.slice(0, 2) as tag}
					<span class="badge badge-xs badge-ghost">{tag}</span>
				{/each}
				{#if note.tags.length > 2}
					<span class="text-xs text-base-content/30">+{note.tags.length - 2}</span>
				{/if}
			</div>
		{/if}
		</a>

		<!-- Trash button -->
		<button
			class="w-16 shrink-0 bg-error flex items-center justify-center hover:bg-error/90"
			onclick={handleDelete}
			title="Delete note"
		>
			<Trash2 size={18} class="text-white" />
		</button>
	</div>
</div>
