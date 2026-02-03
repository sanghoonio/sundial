<script lang="ts">
	import { page } from '$app/state';
	import { User, KeyRound, Bot, Calendar, Palette, Database } from 'lucide-svelte';

	let { children } = $props();

	const categories: { path: string; label: string; icon: typeof User }[] = [
		{ path: '/settings/account', label: 'Account', icon: User },
		{ path: '/settings/tokens', label: 'Sessions & API Keys', icon: KeyRound },
		{ path: '/settings/ai', label: 'AI Features', icon: Bot },
		{ path: '/settings/calendar', label: 'Calendar', icon: Calendar },
		{ path: '/settings/appearance', label: 'Appearance', icon: Palette },
		{ path: '/settings/data', label: 'Data', icon: Database }
	];

	let activePath = $derived(page.url.pathname);
	let hasSelection = $derived(activePath !== '/settings');
</script>

<div class="absolute inset-0 flex overflow-hidden">
	<!-- LEFT PANE: Category list -->
	<div
		class="w-56 border-r border-base-300 flex-col bg-base-100
			{hasSelection ? 'hidden md:flex' : 'flex'}"
	>
		<div class="px-4 py-3 border-b border-base-300 shrink-0">
			<div class="flex items-center gap-2 h-8">
				<h1 class="font-semibold">Settings</h1>
			</div>
		</div>
		<nav class="flex-1 overflow-y-auto pb-2">
			{#each categories as cat}
				<a
					href={cat.path}
					class="flex items-center gap-3 px-4 py-2.5 text-sm border-l-2 transition-colors
						{activePath === cat.path
							? 'bg-base-200 font-medium border-l-primary'
							: 'border-l-transparent hover:bg-base-200/50'}"
				>
					<cat.icon size={16} class="shrink-0" />
					{cat.label}
				</a>
			{/each}
		</nav>
	</div>

	<!-- RIGHT PANE: Section content -->
	<div
		class="flex-1 overflow-hidden flex flex-col
			{!hasSelection ? 'hidden md:flex' : 'flex'}"
	>
		{@render children()}
	</div>
</div>
