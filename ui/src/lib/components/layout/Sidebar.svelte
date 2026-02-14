<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { auth } from '$lib/stores/auth.svelte';
	import { api } from '$lib/services/api';
	import type { SettingsResponse } from '$lib/types';
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
		Github,
		Sun,
		Moon,
		LogOut,
		Wifi,
		WifiOff
	} from 'lucide-svelte';
	import { ws } from '$lib/stores/websocket.svelte';

	// Initialize from localStorage cache for fast render, then sync with API
	const cachedCollapsed = typeof localStorage !== 'undefined'
		? localStorage.getItem('sundial_sidebar_collapsed') === 'true'
		: false;
	let collapsed = $state(cachedCollapsed);

	$effect(() => {
		api.get<SettingsResponse>('/api/settings').then((res) => {
			collapsed = res.sidebar_default_collapsed;
			localStorage.setItem('sundial_sidebar_collapsed', String(res.sidebar_default_collapsed));
		}).catch(() => {
			// Ignore errors, keep cached/default value
		});
	});
	let darkMode = $state(false);

	function resolveTheme(pref: string): 'light' | 'dark' {
		if (pref === 'system') return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		return pref === 'dark' ? 'dark' : 'light';
	}

	// Initialize theme from localStorage (default to light)
	$effect(() => {
		const stored = localStorage.getItem('sundial_theme') ?? 'light';
		const resolved = resolveTheme(stored);
		darkMode = resolved === 'dark';
		document.documentElement.setAttribute('data-theme', resolved);

		const mq = window.matchMedia('(prefers-color-scheme: dark)');
		const handler = () => {
			const current = localStorage.getItem('sundial_theme') ?? 'light';
			if (current === 'system') {
				const r = resolveTheme('system');
				darkMode = r === 'dark';
				document.documentElement.setAttribute('data-theme', r);
			}
		};
		mq.addEventListener('change', handler);
		return () => mq.removeEventListener('change', handler);
	});

	function toggleTheme() {
		const stored = localStorage.getItem('sundial_theme') ?? 'light';
		let next: string;
		if (stored === 'system') {
			next = darkMode ? 'light' : 'dark';
		} else {
			next = darkMode ? 'light' : 'dark';
		}
		darkMode = next === 'dark';
		document.documentElement.setAttribute('data-theme', next);
		localStorage.setItem('sundial_theme', next);
	}

	function handleLogout() {
		auth.logout();
		goto(`${base}/login`);
	}

	const links = [
		{ href: `${base}/`, label: 'Dashboard', icon: LayoutDashboard },
		{ href: `${base}/notes`, label: 'Notes', icon: StickyNote },
		{ href: `${base}/tasks`, label: 'Tasks', icon: CheckSquare },
		{ href: `${base}/projects`, label: 'Projects', icon: FolderKanban },
		{ href: `${base}/calendar`, label: 'Calendar', icon: Calendar },
		{ href: `${base}/search`, label: 'Search', icon: Search }
	];

	function isActive(href: string): boolean {
		if (href === `${base}/`) return page.url.pathname === `${base}/` || page.url.pathname === base;
		return page.url.pathname.startsWith(href);
	}
</script>

<aside
	class="hidden md:flex flex-col bg-base-200 border-r border-base-300 h-screen transition-all {collapsed ? 'w-16' : 'w-56'}"
>
	<!-- Nav links -->
	<nav class="flex-1 flex flex-col gap-1 pt-2 pb-2 px-2">
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
			href="{base}/settings"
			class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
				{isActive(`${base}/settings`) ? 'bg-primary text-primary-content' : 'hover:bg-base-300'}
				{collapsed ? 'justify-center' : ''}"
			title={collapsed ? 'Settings' : undefined}
		>
			<Settings size={20} />
			{#if !collapsed}
				<span>Settings</span>
			{/if}
		</a>

		<!-- GitHub -->
		<a
			href="https://github.com/sanghoonio/sundial"
			target="_blank"
			rel="noopener noreferrer"
			class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300
				{collapsed ? 'justify-center' : ''}"
			title={collapsed ? 'GitHub' : undefined}
		>
			<Github size={20} />
			{#if !collapsed}
				<span>GitHub</span>
			{/if}
		</a>

		<!-- API Docs -->
		<a
			href="{base}/api/docs"
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

		<!-- Connection status -->
		{#if ws.connectionState === 'connected'}
			<div class="dropdown {collapsed ? 'dropdown-right w-full' : 'dropdown-top'}">
				<button
					class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300 w-full
						{collapsed ? 'justify-center' : ''}"
					title={collapsed ? 'Connected' : undefined}
				>
					<span class="relative inline-flex">
						<Wifi size={20} />
						<span class="absolute -top-0.5 -right-0.5 block h-2 w-2 rounded-full bg-success ring-2 ring-base-200"></span>
					</span>
					{#if !collapsed}
						<span>Connected</span>
					{/if}
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div tabindex="0" class="dropdown-content bg-base-100 rounded-box shadow-lg z-10 w-48 p-3 border border-base-300 {collapsed ? 'ml-1' : 'mb-1'}">
					<div class="flex items-center gap-2 text-sm">
						<span class="block h-2 w-2 rounded-full bg-success"></span>
						<span>Connected</span>
					</div>
					<p class="text-xs text-base-content/50 mt-1">Live updates active</p>
				</div>
			</div>
		{:else if ws.connectionState === 'reconnecting'}
			<div class="dropdown {collapsed ? 'dropdown-right w-full' : 'dropdown-top'}">
				<button
					class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300 w-full
						{collapsed ? 'justify-center' : ''}"
					title={collapsed ? 'Reconnecting...' : undefined}
					onclick={() => ws.reconnect()}
				>
					<span class="relative inline-flex">
						<WifiOff size={20} class="animate-pulse" />
						<span class="absolute -top-0.5 -right-0.5 block h-2 w-2 rounded-full bg-warning ring-2 ring-base-200"></span>
					</span>
					{#if !collapsed}
						<span>Reconnecting...</span>
					{/if}
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div tabindex="0" class="dropdown-content bg-base-100 rounded-box shadow-lg z-10 w-48 p-3 border border-base-300 {collapsed ? 'ml-1' : 'mb-1'}">
					<div class="flex items-center gap-2 text-sm">
						<span class="block h-2 w-2 rounded-full bg-warning"></span>
						<span>Reconnecting...</span>
					</div>
					<p class="text-xs text-base-content/50 mt-1">Click to retry now</p>
				</div>
			</div>
		{:else}
			<div class="dropdown {collapsed ? 'dropdown-right w-full' : 'dropdown-top'}">
				<button
					class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors hover:bg-base-300 w-full
						{collapsed ? 'justify-center' : ''}"
					title={collapsed ? 'Disconnected' : undefined}
					onclick={() => ws.reconnect()}
				>
					<span class="relative inline-flex">
						<WifiOff size={20} />
						<span class="absolute -top-0.5 -right-0.5 block h-2 w-2 rounded-full bg-error ring-2 ring-base-200"></span>
					</span>
					{#if !collapsed}
						<span>Disconnected</span>
					{/if}
				</button>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div tabindex="0" class="dropdown-content bg-base-100 rounded-box shadow-lg z-10 w-48 p-3 border border-base-300 {collapsed ? 'ml-1' : 'mb-1'}">
					<div class="flex items-center gap-2 text-sm">
						<span class="block h-2 w-2 rounded-full bg-error"></span>
						<span>Disconnected</span>
					</div>
					<p class="text-xs text-base-content/50 mt-1">Click to reconnect</p>
				</div>
			</div>
		{/if}
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
