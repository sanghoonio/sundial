<script lang="ts">
	import {
		Bold,
		Italic,
		Code,
		Heading,
		List,
		ListOrdered,
		Link,
		Quote,
		Minus,
		FileText
	} from 'lucide-svelte';

	interface Props {
		textarea: HTMLTextAreaElement | undefined;
		onchange?: () => void;
	}

	let { textarea, onchange }: Props = $props();

	function wrap(before: string, after: string) {
		if (!textarea) return;
		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;
		const selected = textarea.value.slice(start, end);
		const replacement = before + (selected || 'text') + after;
		textarea.setRangeText(replacement, start, end, 'select');
		// Adjust selection to be inside the wrapping
		if (!selected) {
			textarea.selectionStart = start + before.length;
			textarea.selectionEnd = start + before.length + 4; // 'text'.length
		}
		textarea.focus();
		textarea.dispatchEvent(new Event('input', { bubbles: true }));
		onchange?.();
	}

	function insertAtLineStart(prefix: string) {
		if (!textarea) return;
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
			// Add prefix to lines that lack it
			newLines = lines.map((line, i) => {
				if (isNumbered) {
					if (numberedRegex.test(line)) return line;
					return `${i + 1}. ${line}`;
				}
				if (line.startsWith(prefix)) return line;
				return prefix + line;
			});
		}

		const replacement = newLines.join('\n');
		textarea.setRangeText(replacement, blockStart, blockEnd, 'select');
		// Select the entire replaced block
		textarea.selectionStart = blockStart;
		textarea.selectionEnd = blockStart + replacement.length;
		textarea.focus();
		textarea.dispatchEvent(new Event('input', { bubbles: true }));
		onchange?.();
	}

	function insertText(text: string) {
		if (!textarea) return;
		const start = textarea.selectionStart;
		textarea.setRangeText(text, start, textarea.selectionEnd, 'end');
		textarea.focus();
		textarea.dispatchEvent(new Event('input', { bubbles: true }));
		onchange?.();
	}

	function handleBold() { wrap('**', '**'); }
	function handleItalic() { wrap('*', '*'); }
	function handleCode() { wrap('`', '`'); }
	function handleHeading() { insertAtLineStart('## '); }
	function handleUl() { insertAtLineStart('- '); }
	function handleOl() { insertAtLineStart('1. '); }
	function handleQuote() { insertAtLineStart('> '); }
	function handleLink() { wrap('[', '](url)'); }
	function handleWikiLink() { wrap('[[', ']]'); }
	function handleHr() { insertText('\n---\n'); }
</script>

<div class="flex items-center gap-0.5 flex-wrap">
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleBold} title="Bold (Ctrl+B)">
		<Bold size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleItalic} title="Italic (Ctrl+I)">
		<Italic size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleCode} title="Inline code">
		<Code size={14} />
	</button>
	<div class="divider divider-horizontal mx-0.5 h-5"></div>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleHeading} title="Heading">
		<Heading size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleUl} title="Bullet list">
		<List size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleOl} title="Numbered list">
		<ListOrdered size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleQuote} title="Blockquote">
		<Quote size={14} />
	</button>
	<div class="divider divider-horizontal mx-0.5 h-5"></div>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleLink} title="Link">
		<Link size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleWikiLink} title="Wiki link [[...]]">
		<FileText size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleHr} title="Horizontal rule">
		<Minus size={14} />
	</button>
</div>
