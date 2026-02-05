<script lang="ts">
	import { api } from '$lib/services/api';
	import { renderMarkdown } from '$lib/utils/markdown';
	import type { ChatMessage } from '$lib/types';
	import { Send } from 'lucide-svelte';

	interface Props {
		noteId: string;
		messages: ChatMessage[];
		precedingContext?: string;
		initialPrompt?: string;
		onmessageschange: (messages: ChatMessage[]) => void;
		onpromptchange?: (prompt: string) => void;
		onremove?: () => void;
	}

	let { noteId, messages, precedingContext = '', initialPrompt = '', onmessageschange, onpromptchange, onremove }: Props = $props();

	// svelte-ignore state_referenced_locally
	let promptText = $state(initialPrompt);
	let loading = $state(false);

	function handlePromptInput() {
		autoResize();
		onpromptchange?.(promptText);
	}
	let textareaEl = $state<HTMLTextAreaElement>();

	let userMessage = $derived(messages.find((m) => m.role === 'user'));
	let assistantMessage = $derived(messages.find((m) => m.role === 'assistant'));
	let hasSent = $derived(!!userMessage);

	let responseHtml = $derived(assistantMessage ? renderMarkdown(assistantMessage.content) : '');

	function autoResize() {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = textareaEl.scrollHeight + 'px';
	}

	$effect(() => {
		if (textareaEl) {
			promptText;
			queueMicrotask(autoResize);
		}
	});

	async function sendMessage() {
		const text = promptText.trim();
		if (!text || loading) return;

		const newMessages: ChatMessage[] = [{ role: 'user', content: text }];
		onmessageschange(newMessages);
		loading = true;

		try {
			const res = await api.post<{ response?: string; error?: string }>('/api/ai/chat', {
				message: text,
				note_id: noteId,
				context: precedingContext || undefined
			});
			const reply = res.error || res.response || 'No response received.';
			onmessageschange([...newMessages, { role: 'assistant', content: reply }]);
		} catch {
			onmessageschange([
				...newMessages,
				{ role: 'assistant', content: 'Sorry, I encountered an error.' }
			]);
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

<div>
	<!-- Prompt box -->
	<div class="rounded-lg border border-primary/30 bg-primary/5 px-3 pt-3 {hasSent ? 'pb-3' : 'pb-2'}">
		{#if hasSent}
			<p class="text-sm whitespace-pre-wrap">{userMessage?.content}</p>
		{:else}
			<div class="relative">
				<textarea
					bind:this={textareaEl}
					class="textarea w-full resize-none overflow-hidden bg-transparent text-sm border-none focus:outline-none p-0"
					rows="1"
					placeholder="Ask about this note..."
					bind:value={promptText}
					onkeydown={handleKeydown}
					oninput={handlePromptInput}
					disabled={loading}
				></textarea>
				<div class="flex justify-end pt-2">
					{#if loading}
						<span class="loading loading-spinner loading-sm text-primary"></span>
					{:else}
						<button
							class="btn btn-primary btn-sm btn-square"
							onclick={sendMessage}
							disabled={!promptText.trim()}
						>
							<Send size={14} />
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- Response -->
	{#if assistantMessage}
		<div class="mt-2 pl-3 border-l-2 border-primary/30">
			<div class="prose prose-sm max-w-none">
				{@html responseHtml}
			</div>
		</div>
	{:else if loading}
		<div class="mt-2 pl-3 border-l-2 border-primary/30">
			<span class="loading loading-dots loading-sm text-primary"></span>
		</div>
	{/if}
</div>
