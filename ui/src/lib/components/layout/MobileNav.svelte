<script lang="ts">
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { LayoutDashboard, StickyNote, CheckSquare, Calendar, Ellipsis, FolderKanban, Search, Settings } from 'lucide-svelte';

	const mainLinks = [
		{ href: `${base}/`, label: 'Home', icon: LayoutDashboard },
		{ href: `${base}/notes`, label: 'Notes', icon: StickyNote },
		{ href: `${base}/tasks`, label: 'Tasks', icon: CheckSquare },
		{ href: `${base}/calendar`, label: 'Calendar', icon: Calendar }
	];

	const moreLinks = [
		{ href: `${base}/projects`, label: 'Projects', icon: FolderKanban },
		{ href: `${base}/search`, label: 'Search', icon: Search },
		{ href: `${base}/settings`, label: 'Settings', icon: Settings }
	];

	let moreOpen = $state(false);

	function isActive(href: string): boolean {
		if (href === `${base}/`) return page.url.pathname === `${base}/` || page.url.pathname === base;
		return page.url.pathname.startsWith(href);
	}

	let isMoreActive = $derived(moreLinks.some((link) => isActive(link.href)));

	function toggleMore() {
		moreOpen = !moreOpen;
	}

	function closeMore() {
		moreOpen = false;
	}
</script>

<!-- Invisible backdrop to capture taps -->
{#if moreOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-40 md:hidden"
		onclick={closeMore}
		onkeydown={(e) => { if (e.key === 'Escape') closeMore(); }}
	></div>

	<!-- Bottom sheet -->
	<div class="fixed left-0 right-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] rounded-t-2xl bg-base-100 shadow-[0_-4px_12px_rgba(0,0,0,0.1)] z-50 md:hidden">
		<div class="flex flex-col py-2">
			{#each moreLinks as link}
				<a
					href={link.href}
					class="flex items-center gap-3 px-5 py-3 text-sm transition-colors
						{isActive(link.href) ? 'text-primary font-bold bg-primary/5' : 'text-base-content hover:bg-base-200'}"
					onclick={closeMore}
				>
					{#if isActive(link.href)}
						<link.icon size={20} strokeWidth={2.5} fill="currentColor" />
					{:else}
						<link.icon size={20} />
					{/if}
					{link.label}
				</a>
			{/each}
		</div>
	</div>
{/if}

<!-- Dock nav -->
<nav class="dock md:hidden border-t border-base-300 shadow-[0_-2px_8px_rgba(0,0,0,0.06)]">
	{#each mainLinks as link}
		<a href={link.href} class={isActive(link.href) ? 'dock-active' : ''}>
			{#if isActive(link.href)}
				<link.icon size={20} strokeWidth={2.5} fill="currentColor" />
			{:else}
				<link.icon size={20} />
			{/if}
			<span class="dock-label {isActive(link.href) ? 'font-bold' : ''}">{link.label}</span>
		</a>
	{/each}
	<button class={isMoreActive ? 'dock-active' : ''} onclick={toggleMore}>
		{#if isMoreActive}
			<Ellipsis size={20} strokeWidth={2.5} />
		{:else}
			<Ellipsis size={20} />
		{/if}
		<span class="dock-label {isMoreActive ? 'font-bold' : ''}">More</span>
	</button>
</nav>
