<script lang="ts">
	import type { NoteBlock } from '$lib/types';
	import { Search, ChevronUp, ChevronDown, X } from 'lucide-svelte';
	import { notesSearch } from '$lib/stores/notesSearch.svelte';

	interface Props {
		blocks: NoteBlock[];
		preview: boolean;
		containerEl: HTMLElement;
		onclose: () => void;
	}

	let { blocks, preview, containerEl, onclose }: Props = $props();

	let query = $state('');
	let currentIndex = $state(0);
	let inputEl = $state<HTMLInputElement | null>(null);

	interface Match {
		blockIndex: number;
		start: number;
		end: number;
	}

	let matches = $derived.by(() => {
		if (!query) return [] as Match[];
		const q = query.toLowerCase();
		const result: Match[] = [];
		for (let i = 0; i < blocks.length; i++) {
			const block = blocks[i];
			if (block.type !== 'md') continue;
			const text = (block.content ?? '').toLowerCase();
			let pos = 0;
			while (pos < text.length) {
				const idx = text.indexOf(q, pos);
				if (idx === -1) break;
				result.push({ blockIndex: i, start: idx, end: idx + q.length });
				pos = idx + q.length;
			}
		}
		return result;
	});

	// Clamp currentIndex when matches change
	$effect(() => {
		if (matches.length === 0) {
			currentIndex = 0;
		} else if (currentIndex >= matches.length) {
			currentIndex = 0;
		}
	});

	// Sync query to store so MarkdownBlock can render highlights
	$effect(() => {
		notesSearch.findQuery = query;
		return () => {
			notesSearch.findQuery = '';
			notesSearch.currentMatch = null;
		};
	});

	// Keep currentMatch in sync — covers typing in find bar + clamping
	$effect(() => {
		notesSearch.currentMatch = matches.length > 0 ? matches[currentIndex] ?? null : null;
	});

	let highlightedBlockIndex = $state<number | null>(null);
	let highlightTimer: ReturnType<typeof setTimeout>;

	function goToMatch(index: number) {
		const match = matches[index];
		if (!match || !containerEl) return;

		if (preview) {
			const sel = window.getSelection();
			sel?.removeAllRanges();
			(window as any).find(query, false, false, true);
		} else {
			const blockEls = containerEl.querySelectorAll('[data-note-block]');
			const blockEl = blockEls[match.blockIndex] as HTMLElement | undefined;
			if (!blockEl) return;

			// Calculate the match's Y position within the scrollable container
			const textarea = blockEl.querySelector('textarea') as HTMLTextAreaElement | null;
			if (textarea) {
				const textBefore = textarea.value.substring(0, match.start);
				const linesBefore = textBefore.split('\n').length - 1;
				const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 20;
				const matchY = linesBefore * lineHeight;

				// Walk offsetParent chain to get true offset relative to containerEl
				let offsetY = matchY;
				let el: HTMLElement | null = textarea;
				while (el && el !== containerEl) {
					offsetY += el.offsetTop;
					el = el.offsetParent as HTMLElement | null;
				}

				containerEl.scrollTo({
					top: offsetY - containerEl.clientHeight / 2,
					behavior: 'smooth'
				});
			} else {
				// Fallback for blocks without a textarea
				blockEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
			}

			// Flash highlight on the block
			clearTimeout(highlightTimer);
			highlightedBlockIndex = match.blockIndex;
			highlightTimer = setTimeout(() => { highlightedBlockIndex = null; }, 1500);
		}
	}

	// Apply/remove highlight class on the matched block element
	$effect(() => {
		if (!containerEl) return;
		const blockEls = containerEl.querySelectorAll('[data-note-block]');
		// Clear all highlights
		blockEls.forEach((el) => el.classList.remove('find-highlight'));
		// Apply to current
		if (highlightedBlockIndex !== null && blockEls[highlightedBlockIndex]) {
			blockEls[highlightedBlockIndex].classList.add('find-highlight');
		}
	});

	function next() {
		if (matches.length === 0) return;
		currentIndex = (currentIndex + 1) % matches.length;
		goToMatch(currentIndex);
	}

	function prev() {
		if (matches.length === 0) return;
		currentIndex = (currentIndex - 1 + matches.length) % matches.length;
		goToMatch(currentIndex);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && e.shiftKey) {
			e.preventDefault();
			prev();
		} else if (e.key === 'Enter') {
			e.preventDefault();
			next();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			onclose();
		}
	}

	export function focus() {
		inputEl?.focus();
		inputEl?.select();
	}
</script>

<style>
	:global(.find-highlight) {
		background-color: oklch(var(--wa) / 0.15);
		border-radius: 0.375rem;
		transition: background-color 0.3s ease;
	}
</style>

<div class="absolute top-2 right-4 z-20 flex items-center gap-1 bg-base-100 border border-base-300 rounded-lg shadow-lg px-2 py-1.5">
	<Search size={14} class="text-base-content/50 shrink-0" />
	<input
		type="text"
		bind:value={query}
		bind:this={inputEl}
		onkeydown={handleKeydown}
		placeholder="Find in note..."
		class="bg-transparent outline-none text-sm w-48"
	/>
	{#if query}
		<span class="text-xs text-base-content/50 shrink-0 tabular-nums">
			{#if matches.length > 0}
				{currentIndex + 1} of {matches.length}
			{:else}
				0 results
			{/if}
		</span>
	{/if}
	<button class="btn btn-ghost btn-xs btn-square" onclick={prev} disabled={matches.length === 0} title="Previous (Shift+Enter)">
		<ChevronUp size={14} />
	</button>
	<button class="btn btn-ghost btn-xs btn-square" onclick={next} disabled={matches.length === 0} title="Next (Enter)">
		<ChevronDown size={14} />
	</button>
	<button class="btn btn-ghost btn-xs btn-square" onclick={onclose} title="Close (Escape)">
		<X size={14} />
	</button>
</div>
