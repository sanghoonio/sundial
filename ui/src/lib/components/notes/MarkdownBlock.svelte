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
	let userMinHeight = $state<number | null>(null);
	let lastAutoHeight: number | null = null;

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
		const floor = userMinHeight ?? MIN_H;
		const h = Math.max(textareaEl.scrollHeight, floor);
		textareaEl.style.height = h + 'px';
		lastAutoHeight = h;
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
	<div class="prose prose-sm max-w-none min-h-8 py-1">
		{#if content}
			{@html renderedHtml}
		{:else}
			<p class="text-base-content/30 italic">Empty block</p>
		{/if}
	</div>
{:else}
	<div class="w-full overflow-hidden rounded-lg border border-base-content/20 {focused ? 'shadow-[0_0_8px_rgba(0,0,0,0.06)]' : ''}">
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
{/if}
