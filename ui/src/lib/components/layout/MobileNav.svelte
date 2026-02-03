<script lang="ts">
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { LayoutDashboard, StickyNote, CheckSquare, Calendar, Search } from 'lucide-svelte';

	const links = [
		{ href: `${base}/`, label: 'Home', icon: LayoutDashboard },
		{ href: `${base}/notes`, label: 'Notes', icon: StickyNote },
		{ href: `${base}/tasks`, label: 'Tasks', icon: CheckSquare },
		{ href: `${base}/calendar`, label: 'Calendar', icon: Calendar },
		{ href: `${base}/search`, label: 'Search', icon: Search }
	];

	function isActive(href: string): boolean {
		if (href === `${base}/`) return page.url.pathname === `${base}/` || page.url.pathname === base;
		return page.url.pathname.startsWith(href);
	}
</script>

<nav class="btm-nav md:hidden z-50">
	{#each links as link}
		<a href={link.href} class={isActive(link.href) ? 'active' : ''}>
			<link.icon size={20} />
			<span class="btm-nav-label text-xs">{link.label}</span>
		</a>
	{/each}
</nav>
