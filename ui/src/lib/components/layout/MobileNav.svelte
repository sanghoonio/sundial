<script lang="ts">
	import { page } from '$app/state';
	import { LayoutDashboard, StickyNote, CheckSquare, Calendar, Search } from 'lucide-svelte';

	const links = [
		{ href: '/', label: 'Home', icon: LayoutDashboard },
		{ href: '/notes', label: 'Notes', icon: StickyNote },
		{ href: '/tasks', label: 'Tasks', icon: CheckSquare },
		{ href: '/calendar', label: 'Calendar', icon: Calendar },
		{ href: '/search', label: 'Search', icon: Search }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
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
