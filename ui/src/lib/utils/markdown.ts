import { Marked } from 'marked';
import markedKatex from 'marked-katex-extension';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import r from 'highlight.js/lib/languages/r';
import rust from 'highlight.js/lib/languages/rust';
import cpp from 'highlight.js/lib/languages/cpp';
import css from 'highlight.js/lib/languages/css';
import xml from 'highlight.js/lib/languages/xml';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import sql from 'highlight.js/lib/languages/sql';
import yaml from 'highlight.js/lib/languages/yaml';
import go from 'highlight.js/lib/languages/go';
import java from 'highlight.js/lib/languages/java';
import markdown from 'highlight.js/lib/languages/markdown';

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
hljs.registerLanguage('css', css);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);
hljs.registerLanguage('go', go);
hljs.registerLanguage('java', java);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('md', markdown);

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
marked.use(markedKatex({ throwOnError: false }));

// Custom renderer for task list checkboxes (remove disabled) and code blocks
marked.use({
	renderer: {
		listitem(token) {
			// Must use this.parser.parse() to render nested lists/inline content
			const body = this.parser.parse(token.tokens);
			if (token.task) {
				const c = token.checked ? ' checked' : '';
				// Strip the default disabled checkbox that parse() emits (may be inside <p> for loose lists)
				const stripped = body.replace(/<input[^>]*type="checkbox"[^>]*>\s*/i, '');
				return `<li class="task-list-item"><input type="checkbox" class="checkbox checkbox-xs"${c}> ${stripped}</li>\n`;
			}
			return `<li>${body}</li>\n`;
		},
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
	// marked doesn't recognize `- [ ]` as a task without trailing text — add zero-width space
	const preprocessed = content.replace(/^(\s*- \[[ xX]\])(\s*)$/gm, '$1 \u200B');
	const raw = marked.parse(preprocessed) as string;
	return DOMPurify.sanitize(raw, {
		ADD_ATTR: [
			'data-title', 'data-type', 'data-id', 'data-width',
			'checked', 'type',
			// KaTeX needs inline styles, aria attrs, and SVG attrs
			'style', 'aria-hidden', 'xmlns', 'encoding',
			'd', 'viewBox', 'preserveAspectRatio', 'width', 'height',
			'x1', 'x2', 'y1', 'y2', 'stroke', 'fill', 'stroke-width', 'fill-rule', 'clip-rule'
		],
		ADD_TAGS: [
			// Task list checkboxes
			'input',
			// MathML elements
			'math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'mfrac', 'msup', 'msub',
			'msubsup', 'msqrt', 'mroot', 'mtable', 'mtr', 'mtd', 'mtext', 'mspace',
			'annotation', 'munder', 'mover', 'munderover', 'mpadded', 'mphantom',
			// SVG elements for stretchy delimiters
			'svg', 'line', 'path', 'rect', 'g'
		]
	});
}

/**
 * Extract a plain-text preview from markdown content.
 */
export function markdownPreview(content: string, maxLength = 200): string {
	if (!content) return '';
	// Strip markdown syntax for a clean preview
	const text = content
		.replace(/\$\$[\s\S]*?\$\$/g, '[math]') // display math
		.replace(/\$([^$\n]+?)\$/g, '$1') // inline math — keep inner text
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
