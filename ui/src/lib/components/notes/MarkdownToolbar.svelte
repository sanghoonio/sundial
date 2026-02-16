<script lang="ts">
	import {
		Bold,
		Italic,
		Strikethrough,
		Code,
		Heading,
		List,
		ListOrdered,
		ListChecks,
		Link,
		Quote,
		Minus,
		FileText,
		Braces,
		ImagePlus
	} from 'lucide-svelte';
	import { wrap, insertAtLineStart, insertText } from '$lib/utils/editorFormatting';

	interface Props {
		textarea: HTMLTextAreaElement | undefined;
		onchange?: () => void;
	}

	let { textarea, onchange }: Props = $props();

	function ctx() {
		return { textarea: textarea!, onchange };
	}

	function handleBold() { if (textarea) wrap(ctx(), '**', '**'); }
	function handleItalic() { if (textarea) wrap(ctx(), '*', '*'); }
	function handleStrikethrough() { if (textarea) wrap(ctx(), '~~', '~~'); }
	function handleCode() { if (textarea) wrap(ctx(), '`', '`'); }
	function handleHeading() { if (textarea) insertAtLineStart(ctx(), '## '); }
	function handleUl() { if (textarea) insertAtLineStart(ctx(), '- '); }
	function handleOl() { if (textarea) insertAtLineStart(ctx(), '1. '); }
	function handleTaskList() { if (textarea) insertAtLineStart(ctx(), '- [ ] '); }
	function handleQuote() { if (textarea) insertAtLineStart(ctx(), '> '); }
	function handleLink() { if (textarea) wrap(ctx(), '[', '](url)'); }
	function handleWikiLink() { if (textarea) wrap(ctx(), '[[', ']]'); }
	function handleImage() { if (textarea) wrap(ctx(), '![', '](url)'); }
	function handleCodeBlock() { if (textarea) insertText(ctx(), '\n```\n\n```\n'); }
	function handleHr() { if (textarea) insertText(ctx(), '\n---\n'); }
</script>

<div class="flex items-center gap-0.5 flex-wrap">
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleBold} title="Bold (Ctrl+B)">
		<Bold size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleItalic} title="Italic (Ctrl+I)">
		<Italic size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleStrikethrough} title="Strikethrough (Ctrl+Shift+S)">
		<Strikethrough size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleCode} title="Inline code (Ctrl+`)">
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
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleTaskList} title="Task list">
		<ListChecks size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleQuote} title="Blockquote">
		<Quote size={14} />
	</button>
	<div class="divider divider-horizontal mx-0.5 h-5"></div>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleLink} title="Link (Ctrl+K)">
		<Link size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleWikiLink} title="Wiki link [[...]]">
		<FileText size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleImage} title="Image">
		<ImagePlus size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleCodeBlock} title="Code block">
		<Braces size={14} />
	</button>
	<button type="button" class="btn btn-ghost btn-xs btn-square" onclick={handleHr} title="Horizontal rule">
		<Minus size={14} />
	</button>
</div>
