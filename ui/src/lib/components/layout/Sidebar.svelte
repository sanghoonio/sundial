<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import {
		LayoutDashboard,
		StickyNote,
		CheckSquare,
		Calendar,
		FolderKanban,
		Search,
		Settings,
		ChevronLeft,
		ChevronRight,
		BookOpen,
		Sun,
		Moon,
		LogOut
	} from 'lucide-svelte';

	let collapsed = $state(false);
	let darkMode = $state(false);

	// Initialize theme from localStorage / system preference
	$effect(() => {
		const stored = localStorage.getItem('sundial_theme');
		if (stored) {
			darkMode = stored === 'dark';
		} else {
			darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
	});

	function toggleTheme() {
		darkMode = !darkMode;
		const theme = darkMode ? 'dark' : 'light';
		document.documentElement.setAttribute('data-theme', theme);
		localStorage.setItem('sundial_theme', theme);
	}

	function handleLogout() {
		auth.logout();
		goto('/login');
	}

	const links = [
		{ href: '/', label: 'Dashboard', icon: LayoutDashboard },
		{ href: '/notes', label: 'Notes', icon: StickyNote },
		{ href: '/tasks', label: 'Tasks', icon: CheckSquare },
		{ href: '/projects', label: 'Projects', icon: FolderKanban },
		{ href: '/calendar', label: 'Calendar', icon: Calendar },
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
	<!-- Nav links -->
	<nav class="flex-1 flex flex-col gap-1 pt-4 md:pt-6 pb-2 px-2">
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

	<!-- Bottom section -->
	<div class="py-2 px-2 border-t border-base-300 flex flex-col gap-1">
		<!-- Settings -->
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

		<!-- API Docs -->
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

	<!-- User profile + toggles -->
	<div class="py-2 px-2 border-t border-base-300 flex flex-col gap-1">
		{#if collapsed}
			<!-- Toggles above avatar when collapsed -->
			<button
				class="flex items-center justify-center px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300"
				onclick={toggleTheme}
				title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
			>
				{#if darkMode}
					<Sun size={20} />
				{:else}
					<Moon size={20} />
				{/if}
			</button>
			<button
				class="flex items-center justify-center px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300"
				onclick={() => (collapsed = !collapsed)}
				title="Expand sidebar"
			>
				<ChevronRight size={20} />
			</button>
		{/if}

		<!-- Avatar row -->
		<div class="flex items-center gap-2">
			<div class="dropdown {collapsed ? 'dropdown-right w-full' : 'dropdown-top'}">
				<div
					tabindex="0"
					role="button"
					class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300
						{collapsed ? 'justify-center' : ''}"
					title={collapsed ? auth.user?.username ?? 'User' : undefined}
				>
					<div class="avatar placeholder">
						<div class="bg-neutral text-neutral-content rounded-full w-8 h-8 flex items-center justify-center">
							<span class="text-xs">{(auth.user?.username ?? 'U')[0].toUpperCase()}</span>
						</div>
					</div>
					{#if !collapsed}
						<span class="truncate">{auth.user?.username ?? ''}</span>
					{/if}
				</div>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow-lg z-10 w-40 p-2 border border-base-300 {collapsed ? 'ml-1' : 'mb-1'}">
					<li>
						<button onclick={handleLogout}>
							<LogOut size={16} />
							Log out
						</button>
					</li>
				</ul>
			</div>

			{#if !collapsed}
				<div class="flex-1"></div>
				<div class="join">
					<button
						class="join-item btn btn-ghost btn-sm btn-square"
						onclick={toggleTheme}
						title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
					>
						{#if darkMode}
							<Sun size={18} />
						{:else}
							<Moon size={18} />
						{/if}
					</button>
					<button
						class="join-item btn btn-ghost btn-sm btn-square"
						onclick={() => (collapsed = !collapsed)}
						title="Collapse sidebar"
					>
						<ChevronLeft size={18} />
					</button>
				</div>
			{/if}
		</div>
	</div>
</aside>
