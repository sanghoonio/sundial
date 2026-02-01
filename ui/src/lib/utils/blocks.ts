import type { NoteBlock } from '$lib/types';

/**
 * Collect all markdown content and chat transcripts from blocks 0..beforeIndex-1
 * to send as AI context for a chat block.
 */
export function gatherContext(blocks: NoteBlock[], beforeIndex: number): string {
	const parts: string[] = [];

	for (let i = 0; i < beforeIndex && i < blocks.length; i++) {
		const block = blocks[i];
		if (block.type === 'md' && block.content) {
			parts.push(block.content);
		} else if (block.type === 'chat' && block.messages?.length) {
			const transcript = block.messages
				.map((m) => `${m.role}: ${m.content}`)
				.join('\n');
			parts.push(transcript);
		}
	}

	return parts.join('\n\n');
}

/** Generate a short random ID for new blocks. */
export function newBlockId(): string {
	return Math.random().toString(36).slice(2, 10);
}
