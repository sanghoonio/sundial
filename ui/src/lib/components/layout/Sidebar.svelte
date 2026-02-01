<script lang="ts">
	import { page } from '$app/state';
	import { LayoutDashboard, StickyNote, CheckSquare, Calendar, FolderKanban, Search, Settings, ChevronLeft, ChevronRight, BookOpen } from 'lucide-svelte';

	let collapsed = $state(false);

	const links = [
		{ href: '/', label: 'Dashboard', icon: LayoutDashboard },
		{ href: '/notes', label: 'Notes', icon: StickyNote },
		{ href: '/tasks', label: 'Tasks', icon: CheckSquare },
		{ href: '/calendar', label: 'Calendar', icon: Calendar },
		{ href: '/projects', label: 'Projects', icon: FolderKanban },
		{ href: '/search', label: 'Search', icon: Search }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href);
	}
</script>

<aside
	class="hidden md:flex flex-col bg-base-200 border-r border-base-300 h-screen transition-all {collapsed ? 'w-16' : 'w-56'}"
>
	<div class="flex items-center h-16 px-4 border-b border-base-300 {collapsed ? 'justify-center' : 'justify-between'}">
		{#if !collapsed}
			<span class="text-lg font-bold">Sundial</span>
		{/if}
		<button class="btn btn-ghost btn-sm btn-square" onclick={() => (collapsed = !collapsed)}>
			{#if collapsed}
				<ChevronRight size={18} />
			{:else}
				<ChevronLeft size={18} />
			{/if}
		</button>
	</div>

	<nav class="flex-1 flex flex-col gap-1 py-2 px-2">
		{#each links as link}
			<a
				href={link.href}
				class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
					{isActive(link.href) ? 'bg-primary text-primary-content' : 'hover:bg-base-300'}
					{collapsed ? 'justify-center' : ''}"
				title={collapsed ? link.label : undefined}
			>
				<link.icon size={20} />
				{#if !collapsed}
					<span>{link.label}</span>
				{/if}
			</a>
		{/each}
	</nav>

	<div class="py-2 px-2 border-t border-base-300 flex flex-col gap-1">
		<a
			href="/settings"
			class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
				{isActive('/settings') ? 'bg-primary text-primary-content' : 'hover:bg-base-300'}
				{collapsed ? 'justify-center' : ''}"
			title={collapsed ? 'Settings' : undefined}
		>
			<Settings size={20} />
			{#if !collapsed}
				<span>Settings</span>
			{/if}
		</a>
		<a
			href="/api/docs"
			target="_blank"
			rel="noopener noreferrer"
			class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300
				{collapsed ? 'justify-center' : ''}"
			title={collapsed ? 'API Docs' : undefined}
		>
			<BookOpen size={20} />
			{#if !collapsed}
				<span>API Docs</span>
			{/if}
		</a>
	</div>
</aside>
