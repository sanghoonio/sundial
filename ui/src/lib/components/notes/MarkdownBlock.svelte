<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { NoteList } from '$lib/types';
	import { renderMarkdown } from '$lib/utils/markdown';
	import { renderMermaidInContainer } from '$lib/utils/mermaid';
	import { notesSearch } from '$lib/stores/notesSearch.svelte';
	import MarkdownToolbar from './MarkdownToolbar.svelte';
	import WikiLinkSuggest from './WikiLinkSuggest.svelte';

	interface Props {
		content: string;
		preview: boolean;
		focused: boolean;
		blockIndex: number;
		onfocus: () => void;
		onupdate: (content: string) => void;
	}

	let { content, preview, focused, blockIndex, onfocus, onupdate }: Props = $props();

	let textareaEl = $state<HTMLTextAreaElement>();
	let userMinHeight = $state<number | null>(null);
	let lastAutoHeight: number | null = null;
	let editorWrapperEl = $state<HTMLDivElement>();
	let previewEl = $state<HTMLDivElement>();

	let renderedHtml = $derived(preview ? renderMarkdown(content) : '');

	// Find-in-note highlight backdrop
	let backdropEl = $state<HTMLDivElement>();

	function escapeHtml(text: string): string {
		return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	let highlightedHtml = $derived.by(() => {
		const q = notesSearch.findQuery;
		if (!q || preview) return '';
		const cur = notesSearch.currentMatch;
		const text = content;
		const lowerText = text.toLowerCase();
		const lowerQ = q.toLowerCase();
		let result = '';
		let pos = 0;
		let found = false;
		while (pos < text.length) {
			const idx = lowerText.indexOf(lowerQ, pos);
			if (idx === -1) {
				result += escapeHtml(text.slice(pos));
				break;
			}
			found = true;
			const isCurrent = cur && cur.blockIndex === blockIndex && cur.start === idx;
			result += escapeHtml(text.slice(pos, idx));
			result += `<mark${isCurrent ? ' class="current"' : ''}>${escapeHtml(text.slice(idx, idx + q.length))}</mark>`;
			pos = idx + q.length;
		}
		// Trailing newline so the backdrop height matches textarea (textareas always have an implicit trailing line)
		return found ? result + '\n' : '';
	});

	let findActive = $derived(!!notesSearch.findQuery && !preview);

	// Which ordinal within this block is the current match?
	let currentMatchOrdinal = $derived.by(() => {
		const cur = notesSearch.currentMatch;
		const q = notesSearch.findQuery;
		if (!cur || !q || cur.blockIndex !== blockIndex) return -1;
		const lowerText = content.toLowerCase();
		const lowerQ = q.toLowerCase();
		let count = 0;
		let pos = 0;
		while (pos < cur.start) {
			const idx = lowerText.indexOf(lowerQ, pos);
			if (idx === -1 || idx >= cur.start) break;
			count++;
			pos = idx + q.length;
		}
		return count;
	});

	// Preview-mode find highlighting via pure string manipulation (no DOM APIs)
	let previewHtmlWithHighlights = $derived.by(() => {
		if (!preview) return renderedHtml;
		const q = notesSearch.findQuery;
		if (!q || !renderedHtml) return renderedHtml;

		const ordinal = currentMatchOrdinal;
		const lowerQ = q.toLowerCase();
		let result = '';
		let matchCount = 0;
		let i = 0;

		while (i < renderedHtml.length) {
			if (renderedHtml[i] === '<') {
				// Copy entire tag verbatim
				const end = renderedHtml.indexOf('>', i);
				if (end === -1) {
					result += renderedHtml.slice(i);
					break;
				}
				result += renderedHtml.slice(i, end + 1);
				i = end + 1;
			} else {
				// Collect text run until next tag
				const textStart = i;
				while (i < renderedHtml.length && renderedHtml[i] !== '<') i++;
				const text = renderedHtml.slice(textStart, i);

				// Search and highlight within this text run
				const lowerText = text.toLowerCase();
				let pos = 0;
				while (pos < text.length) {
					const idx = lowerText.indexOf(lowerQ, pos);
					if (idx === -1) {
						result += text.slice(pos);
						break;
					}
					result += text.slice(pos, idx);
					const isCurrent = matchCount === ordinal;
					const bg = isCurrent ? 'rgba(234,179,8,.45)' : 'rgba(234,179,8,.2)';
					result += `<mark class="find-match${isCurrent ? ' current' : ''}" style="background:${bg};border-radius:.25rem;color:inherit">${text.slice(idx, idx + q.length)}</mark>`;
					matchCount++;
					pos = idx + q.length;
				}
			}
		}

		return result;
	});

	// Sync backdrop text-rendering styles with textarea so word-wrap matches
	$effect(() => {
		if (!textareaEl || !backdropEl || !findActive) return;
		const s = getComputedStyle(textareaEl);
		const b = backdropEl.style;
		b.padding = s.padding;
		b.fontSize = s.fontSize;
		b.fontFamily = s.fontFamily;
		b.lineHeight = s.lineHeight;
		b.letterSpacing = s.letterSpacing;
		b.wordSpacing = s.wordSpacing;
		b.overflowWrap = s.overflowWrap;
		b.wordBreak = s.wordBreak;
		b.tabSize = s.tabSize;
	});

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

	function getScrollParent(el: HTMLElement): HTMLElement | null {
		let p = el.parentElement;
		while (p) {
			if (p.scrollHeight > p.clientHeight) {
				const { overflowY } = getComputedStyle(p);
				if (overflowY === 'auto' || overflowY === 'scroll') return p;
			}
			p = p.parentElement;
		}
		return null;
	}

	function autoResize() {
		if (!textareaEl) return;
		// Save scroll position — collapsing height to 0 causes the browser to clamp scrollTop
		const scrollParent = getScrollParent(textareaEl);
		const savedScrollTop = scrollParent?.scrollTop ?? 0;
		textareaEl.style.height = '0';
		const floor = userMinHeight ?? MIN_H;
		const h = Math.max(textareaEl.scrollHeight, floor);
		textareaEl.style.height = h + 'px';
		lastAutoHeight = h;
		if (scrollParent) scrollParent.scrollTop = savedScrollTop;
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

		// Tab/Shift+Tab: indent/unindent (supports multi-line selection)
		if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && textareaEl) {
			e.preventDefault();
			const { selectionStart, selectionEnd, value } = textareaEl;

			// Find the start of the first selected line and end of the last
			const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1;
			const lineEnd = value.indexOf('\n', selectionEnd);
			const blockEnd = lineEnd === -1 ? value.length : lineEnd;

			const selectedBlock = value.slice(lineStart, blockEnd);
			const lines = selectedBlock.split('\n');

			let newBlock: string;
			let newSelectionStart: number;
			let newSelectionEnd: number;

			if (e.shiftKey) {
				// Unindent: remove leading tab from each line
				newBlock = lines.map(line => line.startsWith('\t') ? line.slice(1) : line).join('\n');
				const removedBefore = selectedBlock.slice(0, selectionStart - lineStart).split('\n')
					.reduce((count, line) => count + (line.startsWith('\t') ? 1 : 0), 0);
				const totalRemoved = lines.filter(line => line.startsWith('\t')).length;
				newSelectionStart = Math.max(lineStart, selectionStart - removedBefore);
				newSelectionEnd = selectionEnd - totalRemoved + (selectionEnd === selectionStart ? removedBefore - totalRemoved : 0);
			} else {
				// Indent: add tab to start of each line
				newBlock = lines.map(line => '\t' + line).join('\n');
				newSelectionStart = selectionStart + 1;
				newSelectionEnd = selectionEnd + lines.length;
			}

			textareaEl.setRangeText(newBlock, lineStart, blockEnd, 'select');
			textareaEl.setSelectionRange(newSelectionStart, newSelectionEnd);
			textareaEl.dispatchEvent(new Event('input', { bubbles: true }));
			return;
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
		const link = target.closest('a.wiki-link') as HTMLAnchorElement | null;
		if (!link) return;
		e.preventDefault();

		// Handle task links
		if (link.classList.contains('wiki-link-task')) {
			const id = link.dataset.id;
			if (id) goto(`${base}/tasks?task=${id}`);
			return;
		}

		// Handle event links
		if (link.classList.contains('wiki-link-event')) {
			const id = link.dataset.id;
			if (id) goto(`${base}/calendar?event=${id}`);
			return;
		}

		// Handle note links
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
		// Auto-resize on mount, when content changes, and when toggling back from preview
		if (textareaEl) {
			content; // track reactivity
			preview; // re-run when switching back to edit so hidden textarea gets resized
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

	// Render mermaid diagrams after preview HTML is injected
	$effect(() => {
		// Track renderedHtml to re-run when content changes
		if (previewEl && preview && renderedHtml) {
			// Use tick to ensure DOM is updated with the new HTML
			queueMicrotask(() => renderMermaidInContainer(previewEl!));
		}
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div bind:this={previewEl} class="prose prose-sm max-w-none min-h-8 py-1" class:hidden={!preview} onclick={handlePreviewClick}>
	{#if content}
		{@html previewHtmlWithHighlights}
	{:else}
		<p class="text-base-content/30 italic">Empty block</p>
	{/if}
</div>
<div bind:this={editorWrapperEl} class="relative w-full" class:hidden={preview}>
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
		<div onclick={onfocus} class="relative">
			<div
				bind:this={backdropEl}
				class="absolute inset-0 pointer-events-none overflow-hidden whitespace-pre-wrap break-words text-transparent [&_mark]:text-transparent [&_mark]:bg-warning/20 [&_mark]:rounded [&_mark]:py-[2px] [&_mark]:pl-[3.5px] [&_mark]:pr-[1.5px] [&_mark]:-ml-[3.5px] [&_mark]:-mr-[1.5px] [&_mark.current]:bg-warning/50"
				class:hidden={!findActive}
				aria-hidden="true"
			>{@html highlightedHtml}</div>
			<textarea
				bind:this={textareaEl}
				class="textarea w-full font-mono text-sm border-none focus:outline-none focus:shadow-none rounded-none"
				class:!bg-transparent={findActive}
				class:relative={findActive}
				class:!overflow-hidden={findActive}
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
