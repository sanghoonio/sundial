<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { NoteList } from '$lib/types';
	import { renderMarkdown } from '$lib/utils/markdown';
	import MarkdownToolbar from './MarkdownToolbar.svelte';
	import WikiLinkSuggest from './WikiLinkSuggest.svelte';

	interface Props {
		content: string;
		preview: boolean;
		focused: boolean;
		onfocus: () => void;
		onupdate: (content: string) => void;
	}

	let { content, preview, focused, onfocus, onupdate }: Props = $props();

	let textareaEl = $state<HTMLTextAreaElement>();
	let userMinHeight = $state<number | null>(null);
	let lastAutoHeight: number | null = null;
	let editorWrapperEl = $state<HTMLDivElement>();

	let renderedHtml = $derived(renderMarkdown(content));

	// Wiki-link autocomplete state
	let suggestActive = $state(false);
	let suggestQuery = $state('');
	let suggestPosition = $state({ top: 0, left: 0 });
	let suggestComponent = $state<{ handleKey: (e: KeyboardEvent) => boolean }>();

	function handleInput() {
		if (textareaEl) {
			onupdate(textareaEl.value);
			autoResize();
			checkForWikiLink();
		}
	}

	const MIN_H = 144; // ~6 lines at text-sm

	function autoResize() {
		if (!textareaEl) return;
		textareaEl.style.height = '0';
		const floor = userMinHeight ?? MIN_H;
		const h = Math.max(textareaEl.scrollHeight, floor);
		textareaEl.style.height = h + 'px';
		lastAutoHeight = h;
	}

	function checkForWikiLink() {
		if (!textareaEl) return;
		const { selectionStart, value } = textareaEl;
		// Scan backwards from cursor for [[ without ]]
		const before = value.slice(0, selectionStart);
		const openIdx = before.lastIndexOf('[[');
		if (openIdx === -1) {
			suggestActive = false;
			return;
		}
		// Check no ]] between [[ and cursor
		const between = before.slice(openIdx + 2);
		if (between.includes(']]')) {
			suggestActive = false;
			return;
		}
		// Don't trigger on newlines in the query
		if (between.includes('\n')) {
			suggestActive = false;
			return;
		}
		suggestQuery = between;
		suggestActive = true;
		suggestPosition = measureCursorPosition(openIdx);
	}

	function measureCursorPosition(bracketIdx: number): { top: number; left: number } {
		if (!textareaEl || !editorWrapperEl) return { top: 0, left: 0 };

		// Create a mirror element to measure cursor position
		const mirror = document.createElement('div');
		const style = getComputedStyle(textareaEl);
		mirror.style.position = 'fixed';
		mirror.style.top = '-9999px';
		mirror.style.left = '0';
		mirror.style.visibility = 'hidden';
		mirror.style.whiteSpace = 'pre-wrap';
		mirror.style.overflowWrap = 'break-word';
		mirror.style.width = style.width;
		mirror.style.font = style.font;
		mirror.style.fontSize = style.fontSize;
		mirror.style.fontFamily = style.fontFamily;
		mirror.style.lineHeight = style.lineHeight;
		mirror.style.padding = style.padding;
		mirror.style.border = style.border;
		mirror.style.boxSizing = style.boxSizing;
		mirror.style.letterSpacing = style.letterSpacing;

		const text = textareaEl.value.substring(0, bracketIdx);
		mirror.textContent = text;

		// Add a span at cursor position to measure offset within the mirror
		const marker = document.createElement('span');
		marker.textContent = '\u200b';
		mirror.appendChild(marker);

		document.body.appendChild(mirror);

		// Measure marker position relative to mirror (= position within textarea text)
		const mirrorRect = mirror.getBoundingClientRect();
		const markerRect = marker.getBoundingClientRect();
		const relTop = markerRect.top - mirrorRect.top;
		const relLeft = markerRect.left - mirrorRect.left;

		document.body.removeChild(mirror);

		// Translate to wrapper coordinates: textarea offset within wrapper + relative text position
		const textareaRect = textareaEl.getBoundingClientRect();
		const wrapperRect = editorWrapperEl.getBoundingClientRect();
		const lineHeight = parseInt(style.lineHeight) || 20;

		return {
			top: (textareaRect.top - wrapperRect.top) + relTop + lineHeight + 4,
			left: (textareaRect.left - wrapperRect.left) + relLeft
		};
	}

	function handleKeydown(e: KeyboardEvent) {
		// Forward to WikiLinkSuggest when active
		if (suggestActive && suggestComponent) {
			const handled = suggestComponent.handleKey(e);
			if (handled) return;
		}

		if (e.key !== 'Enter' || e.shiftKey || !textareaEl) return;

		const { selectionStart, value } = textareaEl;
		const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1;
		const line = value.slice(lineStart, selectionStart);

		// Match leading whitespace + list prefix
		const match = line.match(/^(\s*)([-*]|\d+\.|>) /);
		if (!match) return;

		const [fullPrefix, indent, bullet] = match;

		// If the line is just the prefix (empty list item), remove it and break out
		if (line.trimEnd() === fullPrefix.trimEnd()) {
			e.preventDefault();
			textareaEl.setRangeText('\n', lineStart, selectionStart, 'end');
			textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
			return;
		}

		e.preventDefault();

		// Auto-increment numbered lists
		let newPrefix: string;
		if (/^\d+$/.test(bullet)) {
			newPrefix = `${indent}${parseInt(bullet) + 1}. `;
		} else {
			newPrefix = fullPrefix;
		}

		textareaEl.setRangeText('\n' + newPrefix, selectionStart, selectionStart, 'end');
		textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
	}

	function handleSuggestSelect(title: string) {
		if (!textareaEl) return;
		const { selectionStart, value } = textareaEl;
		const before = value.slice(0, selectionStart);
		const openIdx = before.lastIndexOf('[[');
		if (openIdx === -1) return;

		const replacement = `[[${title}]]`;
		textareaEl.setRangeText(replacement, openIdx, selectionStart, 'end');
		textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
		suggestActive = false;
		textareaEl.focus();
	}

	function handleSuggestClose() {
		suggestActive = false;
	}

	async function handlePreviewClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		const link = target.closest('a.wiki-link-note') as HTMLAnchorElement | null;
		if (!link) return;
		e.preventDefault();

		const title = link.dataset.title;
		if (!title) return;

		try {
			const data = await api.get<NoteList>(
				`/api/notes?search=${encodeURIComponent(title)}&limit=5`
			);
			const exact = data.notes.find(
				(n) => n.title.toLowerCase() === title.toLowerCase()
			);
			if (exact) {
				goto(`${base}/notes/${exact.id}`);
			} else {
				toast.error(`Note "${title}" not found`);
			}
		} catch {
			toast.error('Failed to find linked note');
		}
	}

	$effect(() => {
		// Auto-resize on mount and when content changes
		if (textareaEl) {
			content; // track reactivity
			// Use a microtask to ensure DOM is updated
			queueMicrotask(autoResize);
		}
	});

	// Track user manual resizes (via drag handle) and preserve as minimum height
	$effect(() => {
		if (!textareaEl) return;
		const observer = new ResizeObserver(() => {
			if (!textareaEl || lastAutoHeight === null) return;
			const currentH = textareaEl.offsetHeight;
			if (Math.abs(currentH - lastAutoHeight) > 2) {
				userMinHeight = currentH;
			}
		});
		observer.observe(textareaEl);
		return () => observer.disconnect();
	});
</script>

{#if preview}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="prose prose-sm max-w-none min-h-8 py-1" onclick={handlePreviewClick}>
		{#if content}
			{@html renderedHtml}
		{:else}
			<p class="text-base-content/30 italic">Empty block</p>
		{/if}
	</div>
{:else}
	<div bind:this={editorWrapperEl} class="relative w-full">
		<div
			class="w-full overflow-hidden rounded-lg border border-base-content/20 {focused ? 'shadow-[0_0_8px_rgba(0,0,0,0.06)]' : ''}"
		>
			{#if focused}
				<div class="px-2 py-1 bg-base-200/50 border-b border-base-content/20">
					<MarkdownToolbar textarea={textareaEl} />
				</div>
			{/if}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div onclick={onfocus}>
				<textarea
					bind:this={textareaEl}
					class="textarea w-full font-mono text-sm border-none focus:outline-none focus:shadow-none rounded-none"
					placeholder="Write markdown..."
					value={content}
					onfocus={onfocus}
					oninput={handleInput}
					onkeydown={handleKeydown}
				></textarea>
			</div>
		</div>

		{#if suggestActive}
			<WikiLinkSuggest
				bind:this={suggestComponent}
				query={suggestQuery}
				top={suggestPosition.top}
				left={suggestPosition.left}
				onselect={handleSuggestSelect}
				onclose={handleSuggestClose}
			/>
		{/if}
	</div>
{/if}
