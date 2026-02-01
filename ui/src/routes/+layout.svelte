<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { ws } from '$lib/stores/websocket.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Header from '$lib/components/layout/Header.svelte';
	import MobileNav from '$lib/components/layout/MobileNav.svelte';
	import Toast from '$lib/components/ui/Toast.svelte';
	import '../app.css';

	let { children } = $props();

	const publicPaths = ['/login', '/setup'];
	let isPublicPage = $derived(publicPaths.includes(page.url.pathname));

	// Initialize auth once on mount
	let initialized = false;
	$effect(() => {
		if (!initialized) {
			initialized = true;
			auth.init();
		}
	});

	// Auth guard - redirect to login if not authenticated on protected pages
	$effect(() => {
		if (!auth.ready) return;
		if (!auth.isAuthenticated && !isPublicPage) {
			goto('/login');
		}
	});

	// WebSocket lifecycle - tied to auth state only, not navigation
	$effect(() => {
		if (auth.isAuthenticated) {
			ws.start();
			return () => ws.stop();
		}
	});

	let pageTitle = $derived.by(() => {
		const path = page.url.pathname;
		if (path === '/') return 'Dashboard';
		if (path === '/notes/new') return 'New Note';
		if (path.startsWith('/notes/')) return 'Note';
		if (path === '/notes') return 'Notes';
		if (path === '/tasks') return 'Tasks';
		if (path === '/calendar') return 'Calendar';
		if (path.startsWith('/projects/')) return 'Project';
		if (path === '/projects') return 'Projects';
		if (path === '/search') return 'Search';
		if (path === '/settings') return 'Settings';
		return '';
	});
</script>

{#if auth.loading}
	<div class="min-h-screen flex items-center justify-center">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if isPublicPage}
	{@render children()}
{:else if auth.isAuthenticated}
	<div class="flex h-screen overflow-hidden">
		<Sidebar />
		<div class="flex-1 flex flex-col min-w-0">
			<Header title={pageTitle} />
			<main class="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
				{@render children()}
			</main>
		</div>
	</div>
	<MobileNav />
{/if}

<Toast />
