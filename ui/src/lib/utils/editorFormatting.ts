/**
 * Shared formatting utilities for the markdown editor.
 * Used by both MarkdownToolbar (click) and MarkdownBlock (keyboard shortcuts).
 */

interface EditorContext {
	textarea: HTMLTextAreaElement;
	onchange?: () => void;
}

function looksLikeUrl(text: string): boolean {
	try {
		const url = new URL(text.trim());
		return url.protocol === 'http:' || url.protocol === 'https:';
	} catch {
		return false;
	}
}

/**
 * Replace a range in the textarea using execCommand so the edit
 * is pushed onto the browser's native undo/redo stack.
 */
function replaceRange(textarea: HTMLTextAreaElement, start: number, end: number, text: string) {
	textarea.focus();
	textarea.setSelectionRange(start, end);
	document.execCommand('insertText', false, text);
}

function notify(ctx: EditorContext) {
	ctx.onchange?.();
}

/**
 * Wrap the selection with before/after markers. Toggles off if already wrapped.
 */
export function wrap(ctx: EditorContext, before: string, after: string) {
	const { textarea } = ctx;
	const start = textarea.selectionStart;
	const end = textarea.selectionEnd;
	const value = textarea.value;
	const selected = value.slice(start, end);

	// Case 1: Selection includes the markers (user selected "**bold**")
	if (selected.startsWith(before) && selected.endsWith(after) && selected.length >= before.length + after.length) {
		const inner = selected.slice(before.length, selected.length - after.length);
		replaceRange(textarea, start, end, inner);
		textarea.selectionStart = start;
		textarea.selectionEnd = start + inner.length;
		notify(ctx);
		return;
	}

	// Case 2: Markers surround the selection (cursor/selection inside "**|text|**")
	const bLen = before.length;
	const aLen = after.length;
	if (
		start >= bLen &&
		end + aLen <= value.length &&
		value.slice(start - bLen, start) === before &&
		value.slice(end, end + aLen) === after
	) {
		const inner = value.slice(start, end);
		replaceRange(textarea, start - bLen, end + aLen, inner);
		textarea.selectionStart = start - bLen;
		textarea.selectionEnd = start - bLen + inner.length;
		notify(ctx);
		return;
	}

	// Default: wrap
	// Smart link/image: if after contains ](url) and selection looks like a URL,
	// put the selection in the URL slot instead of the text slot
	if (selected && after === '](url)' && looksLikeUrl(selected)) {
		const label = 'text';
		const trimmed = selected.trim();
		const trailing = selected.slice(selected.indexOf(trimmed) + trimmed.length);
		const replacement = before + label + '](' + trimmed + ')' + trailing;
		replaceRange(textarea, start, end, replacement);
		// Select the placeholder label so user can type a caption
		textarea.selectionStart = start + before.length;
		textarea.selectionEnd = start + before.length + label.length;
		notify(ctx);
		return;
	}

	const placeholder = selected || 'text';
	const replacement = before + placeholder + after;
	replaceRange(textarea, start, end, replacement);
	if (!selected) {
		textarea.selectionStart = start + before.length;
		textarea.selectionEnd = start + before.length + placeholder.length;
	}
	notify(ctx);
}

/**
 * Insert or toggle a prefix at the start of each selected line.
 * For numbered lists, continues from the preceding numbered line.
 */
export function insertAtLineStart(ctx: EditorContext, prefix: string) {
	const { textarea } = ctx;
	const value = textarea.value;
	const selStart = textarea.selectionStart;
	const selEnd = textarea.selectionEnd;

	// Find the range of lines covered by the selection
	const blockStart = value.lastIndexOf('\n', selStart - 1) + 1;
	let blockEnd = value.indexOf('\n', selEnd);
	if (blockEnd === -1) blockEnd = value.length;

	const block = value.slice(blockStart, blockEnd);
	const lines = block.split('\n');

	const isNumbered = prefix === '1. ';
	const numberedRegex = /^\d+\.\s/;

	// Check if ALL lines already have the prefix (for toggle)
	const allHavePrefix = lines.every((line) =>
		isNumbered ? numberedRegex.test(line) : line.startsWith(prefix)
	);

	let newLines: string[];
	if (allHavePrefix) {
		// Remove prefix from all lines
		newLines = lines.map((line) =>
			isNumbered ? line.replace(numberedRegex, '') : line.slice(prefix.length)
		);
	} else {
		// Determine starting number for numbered lists
		let startNum = 1;
		if (isNumbered) {
			// Look at the line preceding the selection block
			const textBefore = value.slice(0, blockStart);
			const prevLineStart = textBefore.lastIndexOf('\n', textBefore.length - 2) + 1;
			const prevLine = textBefore.slice(prevLineStart).replace(/\n$/, '');
			const prevMatch = prevLine.match(/^(\d+)\.\s/);
			if (prevMatch) {
				startNum = parseInt(prevMatch[1]) + 1;
			}
		}

		// Add prefix to lines that lack it
		newLines = lines.map((line, i) => {
			if (isNumbered) {
				if (numberedRegex.test(line)) return line;
				return `${startNum + i}. ${line}`;
			}
			if (line.startsWith(prefix)) return line;
			return prefix + line;
		});
	}

	const replacement = newLines.join('\n');
	replaceRange(textarea, blockStart, blockEnd, replacement);
	textarea.selectionStart = blockStart;
	textarea.selectionEnd = blockStart + replacement.length;
	notify(ctx);
}

/**
 * Insert raw text at the cursor position.
 */
export function insertText(ctx: EditorContext, text: string) {
	const { textarea } = ctx;
	replaceRange(textarea, textarea.selectionStart, textarea.selectionEnd, text);
	notify(ctx);
}
