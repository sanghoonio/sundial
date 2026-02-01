<script lang="ts">
	import { renderMarkdown } from '$lib/utils/markdown';
	import MarkdownToolbar from './MarkdownToolbar.svelte';

	interface Props {
		content: string;
		preview: boolean;
		focused: boolean;
		onfocus: () => void;
		onupdate: (content: string) => void;
	}

	let { content, preview, focused, onfocus, onupdate }: Props = $props();

	let textareaEl = $state<HTMLTextAreaElement>();

	let renderedHtml = $derived(renderMarkdown(content));

	function handleInput() {
		if (textareaEl) {
			onupdate(textareaEl.value);
			autoResize();
		}
	}

	const MIN_H = 120; // ~5 lines at text-sm

	function autoResize() {
		if (!textareaEl) return;
		textareaEl.style.height = '0';
		textareaEl.style.height = Math.max(textareaEl.scrollHeight, MIN_H) + 'px';
	}

	function handleKeydown(e: KeyboardEvent) {
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

	$effect(() => {
		// Auto-resize on mount and when content changes
		if (textareaEl) {
			content; // track reactivity
			// Use a microtask to ensure DOM is updated
			queueMicrotask(autoResize);
		}
	});
</script>

{#if preview}
	<div class="prose prose-sm max-w-none min-h-8 py-1">
		{#if content}
			{@html renderedHtml}
		{:else}
			<p class="text-base-content/30 italic">Empty block</p>
		{/if}
	</div>
{:else}
	<div class="w-full">
		{#if focused}
			<div class="border border-base-300 rounded-t-lg px-2 py-1 bg-base-200/50">
				<MarkdownToolbar textarea={textareaEl} />
			</div>
		{/if}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div onclick={onfocus}>
			<textarea
				bind:this={textareaEl}
				class="textarea textarea-bordered w-full font-mono text-sm {focused
					? 'border-primary/50 rounded-t-none border-t-0'
					: ''}"
				placeholder="Write markdown..."
				value={content}
				onfocus={onfocus}
				oninput={handleInput}
				onkeydown={handleKeydown}
			></textarea>
		</div>
	</div>
{/if}
