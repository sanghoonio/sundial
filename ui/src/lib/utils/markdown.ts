import { Marked } from 'marked';
import DOMPurify from 'dompurify';

// Custom extension for [[wiki-links]]
const wikiLinkExtension = {
	name: 'wikiLink',
	level: 'inline' as const,
	start(src: string) {
		return src.indexOf('[[');
	},
	tokenizer(src: string) {
		const match = src.match(/^\[\[([^\]]+)\]\]/);
		if (match) {
			return {
				type: 'wikiLink',
				raw: match[0],
				text: match[1].trim()
			};
		}
		return undefined;
	},
	renderer(token: { text: string }) {
		const text = token.text;
		// Support pipe syntax for display text: [[target|display]]
		const pipeIdx = text.indexOf('|');
		const target = pipeIdx >= 0 ? text.slice(0, pipeIdx).trim() : text;
		const display = pipeIdx >= 0 ? text.slice(pipeIdx + 1).trim() : text;

		// If it's task:id or event:id, link accordingly
		// Use # as href since the click handler in MarkdownBlock.svelte handles navigation with base path
		if (target.startsWith('task:')) {
			const id = target.slice(5);
			return `<a href="#" class="wiki-link wiki-link-task" data-type="task" data-id="${escapeAttr(id)}">${escapeHtml(display)}</a>`;
		}
		if (target.startsWith('event:')) {
			const id = target.slice(6);
			return `<a href="#" class="wiki-link wiki-link-event" data-type="event" data-id="${escapeAttr(id)}">${escapeHtml(display)}</a>`;
		}
		// Default: link to note by title
		return `<a href="#" class="wiki-link wiki-link-note" data-title="${escapeAttr(target)}">${escapeHtml(display)}</a>`;
	}
};

function escapeHtml(str: string): string {
	return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str: string): string {
	return str.replace(/"/g, '&quot;').replace(/&/g, '&amp;');
}

const marked = new Marked();
marked.use({ extensions: [wikiLinkExtension] });

/**
 * Render markdown content to sanitized HTML.
 */
export function renderMarkdown(content: string): string {
	if (!content) return '';
	const raw = marked.parse(content) as string;
	return DOMPurify.sanitize(raw, {
		ADD_ATTR: ['data-title', 'data-type', 'data-id'],
		ADD_TAGS: []
	});
}

/**
 * Extract a plain-text preview from markdown content.
 */
export function markdownPreview(content: string, maxLength = 200): string {
	if (!content) return '';
	// Strip markdown syntax for a clean preview
	const text = content
		.replace(/#{1,6}\s+/g, '') // headings
		.replace(/\*\*(.+?)\*\*/g, '$1') // bold
		.replace(/\*(.+?)\*/g, '$1') // italic
		.replace(/`(.+?)`/g, '$1') // inline code
		.replace(/```[\s\S]*?```/g, '') // code blocks
		.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
		.replace(/\[\[([^\]]+)\]\]/g, '$1') // wiki links
		.replace(/!\[.*?\]\(.*?\)/g, '') // images
		.replace(/^\s*[-*+]\s+/gm, '') // list items
		.replace(/^\s*\d+\.\s+/gm, '') // ordered list items
		.replace(/^\s*>\s+/gm, '') // blockquotes
		.replace(/---+/g, '') // horizontal rules
		.replace(/\n{2,}/g, ' ')
		.replace(/\n/g, ' ')
		.trim();
	if (text.length <= maxLength) return text;
	return text.slice(0, maxLength) + '...';
}
