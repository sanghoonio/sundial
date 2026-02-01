<script lang="ts">
	import type { NoteBlock, ChatMessage } from '$lib/types';
	import { newBlockId, gatherContext } from '$lib/utils/blocks';
	import MarkdownBlock from './MarkdownBlock.svelte';
	import ChatBlock from './ChatBlock.svelte';
	import BlockControls from './BlockControls.svelte';
	import AddBlockDivider from './AddBlockDivider.svelte';
	import { FileText, MessageSquare } from 'lucide-svelte';

	interface Props {
		blocks: NoteBlock[];
		noteId?: string;
		preview: boolean;
		onchange: (blocks: NoteBlock[]) => void;
	}

	let { blocks, noteId = '', preview, onchange }: Props = $props();

	let focusedBlockId = $state<string | null>(null);

	function updateBlock(index: number, updated: Partial<NoteBlock>) {
		const newBlocks = [...blocks];
		newBlocks[index] = { ...newBlocks[index], ...updated } as NoteBlock;
		onchange(newBlocks);
	}

	function moveBlock(index: number, direction: -1 | 1) {
		const target = index + direction;
		if (target < 0 || target >= blocks.length) return;
		const newBlocks = [...blocks];
		[newBlocks[index], newBlocks[target]] = [newBlocks[target], newBlocks[index]];
		onchange(newBlocks);
	}

	function deleteBlock(index: number) {
		if (blocks.length <= 1) return; // Keep at least one block
		const newBlocks = blocks.filter((_, i) => i !== index);
		onchange(newBlocks);
		focusedBlockId = null;
	}

	function insertBlock(afterIndex: number, type: 'md' | 'chat') {
		const newBlock: NoteBlock =
			type === 'md'
				? { id: newBlockId(), type: 'md', content: '' }
				: { id: newBlockId(), type: 'chat', messages: [] };
		const newBlocks = [...blocks];
		newBlocks.splice(afterIndex + 1, 0, newBlock);
		onchange(newBlocks);
		focusedBlockId = newBlock.id;
	}

	function addBlockAtEnd(type: 'md' | 'chat') {
		insertBlock(blocks.length - 1, type);
	}

	function handleChatMessagesChange(index: number, messages: ChatMessage[]) {
		updateBlock(index, { messages });
	}
</script>

<div class="space-y-0">
	{#each blocks as block, i (block.id)}
		<!-- Divider between blocks (not before first) -->
		{#if i > 0}
			<AddBlockDivider
				onaddmd={() => insertBlock(i - 1, 'md')}
				onaddchat={() => insertBlock(i - 1, 'chat')}
			/>
		{/if}

		<!-- Block wrapper with hover gutter -->
		<div class="group/block flex gap-2 relative" data-note-block>
			<!-- Gutter controls -->
			{#if !preview}
				<div class="w-6 pt-1 flex-shrink-0">
					<BlockControls
						index={i}
						total={blocks.length}
						onmoveup={() => moveBlock(i, -1)}
						onmovedown={() => moveBlock(i, 1)}
						ondelete={() => deleteBlock(i)}
					/>
				</div>
			{/if}

			<!-- Block content -->
			<div class="flex-1 min-w-0">
				{#if block.type === 'md'}
					<MarkdownBlock
						content={block.content}
						{preview}
						focused={focusedBlockId === block.id}
						onfocus={() => (focusedBlockId = block.id)}
						onupdate={(c) => updateBlock(i, { content: c })}
					/>
				{:else if block.type === 'chat'}
					<ChatBlock
						noteId={noteId}
						messages={block.messages ?? []}
						precedingContext={gatherContext(blocks, i)}
						onmessageschange={(msgs) => handleChatMessagesChange(i, msgs)}
						onremove={() => deleteBlock(i)}
					/>
				{/if}
			</div>
		</div>
	{/each}

	<!-- Add block buttons at bottom -->
	{#if !preview}
		<div class="flex items-center gap-2 pt-3 pl-8">
			<button class="btn btn-ghost btn-sm gap-1" onclick={() => addBlockAtEnd('md')}>
				<FileText size={14} />
				Add text
			</button>
			<button class="btn btn-ghost btn-sm gap-1" onclick={() => addBlockAtEnd('chat')}>
				<MessageSquare size={14} />
				Add chat
			</button>
		</div>
	{/if}
</div>
