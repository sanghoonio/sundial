import type { Mermaid } from 'mermaid';

let mermaidInstance: Mermaid | null = null;
let initPromise: Promise<Mermaid> | null = null;

/**
 * Lazily load and initialize mermaid with DaisyUI-compatible theming.
 */
export async function getMermaid(): Promise<Mermaid> {
	if (mermaidInstance) return mermaidInstance;
	if (initPromise) return initPromise;

	initPromise = (async () => {
		const { default: mermaid } = await import('mermaid');

		// Detect current theme from DaisyUI
		const isDark =
			document.documentElement.getAttribute('data-theme') === 'dark' ||
			(window.matchMedia('(prefers-color-scheme: dark)').matches &&
				!document.documentElement.hasAttribute('data-theme'));

		mermaid.initialize({
			startOnLoad: false,
			theme: isDark ? 'dark' : 'default',
			securityLevel: 'strict',
			fontFamily: 'inherit'
		});

		mermaidInstance = mermaid;
		return mermaid;
	})();

	return initPromise;
}

/**
 * Find all mermaid code blocks in a container and replace with rendered SVG diagrams.
 */
export async function renderMermaidInContainer(container: HTMLElement): Promise<void> {
	const codeBlocks = container.querySelectorAll('pre code.language-mermaid');
	if (codeBlocks.length === 0) return;

	const mermaid = await getMermaid();

	for (const codeBlock of codeBlocks) {
		const pre = codeBlock.parentElement;
		if (!pre) continue;

		const code = codeBlock.textContent?.trim() || '';
		if (!code) continue;

		// Generate unique ID for this diagram
		const id = `mermaid-${crypto.randomUUID().slice(0, 8)}`;

		try {
			const { svg } = await mermaid.render(id, code);

			// Create wrapper div and insert SVG
			const wrapper = document.createElement('div');
			wrapper.className = 'mermaid-diagram';
			wrapper.innerHTML = svg;

			// Apply width parameter if specified (e.g., ```mermaid width=400)
			const width = pre.dataset.width;
			if (width) {
				wrapper.style.maxWidth = width.includes('px') ? width : `${width}px`;
				wrapper.style.marginInline = 'auto';
			}

			pre.replaceWith(wrapper);
		} catch (err) {
			// Show error with original code
			const errorDiv = document.createElement('div');
			errorDiv.className = 'mermaid-error';

			const errorMsg = document.createElement('p');
			errorMsg.className = 'text-error text-sm font-medium mb-2';
			errorMsg.textContent = `Mermaid error: ${err instanceof Error ? err.message : 'Invalid syntax'}`;

			const codeEl = document.createElement('pre');
			codeEl.className = 'text-xs opacity-70 overflow-x-auto';
			codeEl.textContent = code;

			errorDiv.appendChild(errorMsg);
			errorDiv.appendChild(codeEl);
			pre.replaceWith(errorDiv);
		}
	}
}
