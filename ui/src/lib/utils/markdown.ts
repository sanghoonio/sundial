import { Marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import r from 'highlight.js/lib/languages/r';
import rust from 'highlight.js/lib/languages/rust';
import cpp from 'highlight.js/lib/languages/cpp';

// Register syntax highlighting languages
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('ts', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('py', python);
hljs.registerLanguage('r', r);
hljs.registerLanguage('rust', rust);
hljs.registerLanguage('cpp', cpp);
hljs.registerLanguage('c++', cpp);

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

/**
 * Parse code block info string parameters (e.g., "mermaid width=400" -> { width: "400" })
 */
function parseCodeParams(paramString: string): Record<string, string> {
	const params: Record<string, string> = {};
	const regex = /(\w+)=(\S+)/g;
	let match;
	while ((match = regex.exec(paramString)) !== null) {
		params[match[1]] = match[2];
	}
	return params;
}

const marked = new Marked();
marked.use({ extensions: [wikiLinkExtension] });

// Custom renderer for code blocks with syntax highlighting
marked.use({
	renderer: {
		code({ text, lang }) {
			// Parse "mermaid width=400" into { language: "mermaid", params: { width: "400" } }
			const [language, ...paramParts] = (lang || '').split(/\s+/);
			const params = parseCodeParams(paramParts.join(' '));

			// Build data attributes for post-processing (e.g., mermaid width)
			const dataAttrs = Object.entries(params)
				.map(([k, v]) => `data-${k}="${escapeAttr(v)}"`)
				.join(' ');

			// Apply syntax highlighting if language is supported (skip mermaid - it's post-processed)
			let highlighted = escapeHtml(text);
			if (language && language !== 'mermaid' && hljs.getLanguage(language)) {
				highlighted = hljs.highlight(text, { language }).value;
			}

			const dataAttrStr = dataAttrs ? ` ${dataAttrs}` : '';
			return `<pre${dataAttrStr}><code class="language-${language || ''}">${highlighted}</code></pre>`;
		}
	}
});

/**
 * Render markdown content to sanitized HTML.
 */
export function renderMarkdown(content: string): string {
	if (!content) return '';
	const raw = marked.parse(content) as string;
	return DOMPurify.sanitize(raw, {
		ADD_ATTR: ['data-title', 'data-type', 'data-id', 'data-width'],
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
		.replace(/```mermaid[\s\S]*?```/g, '[diagram]') // mermaid diagrams
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
