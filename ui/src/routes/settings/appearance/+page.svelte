<script lang="ts">
	import { base } from '$app/paths';
	import { api } from '$lib/services/api';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import { ChevronLeft, Save, Check } from 'lucide-svelte';

	let loading = $state(true);
	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = $state('idle');
	let showSavedText = $state(false);
	let theme = $state('light');
	let sidebarDefaultCollapsed = $state(false);
	let editorToolbarStyle = $state('float');

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			theme = res.theme;
			sidebarDefaultCollapsed = res.sidebar_default_collapsed;
			editorToolbarStyle = res.editor_toolbar_style;
		} catch (e) {
			console.error('Failed to load settings', e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		loadSettings();
	});

	async function handleSave() {
		saveStatus = 'saving';
		try {
			const update: SettingsUpdate = { theme, sidebar_default_collapsed: sidebarDefaultCollapsed, editor_toolbar_style: editorToolbarStyle };
			const res = await api.put<SettingsResponse>('/api/settings', update);
			theme = res.theme;
			sidebarDefaultCollapsed = res.sidebar_default_collapsed;
			editorToolbarStyle = res.editor_toolbar_style;
			localStorage.setItem('sundial_sidebar_collapsed', String(sidebarDefaultCollapsed));
			localStorage.setItem('sundial_editor_toolbar_style', editorToolbarStyle);
			localStorage.setItem('sundial_theme', theme);
			const resolved = theme === 'system'
				? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
				: theme;
			document.documentElement.setAttribute('data-theme', resolved);
			saveStatus = 'saved';
			showSavedText = true;
			setTimeout(() => { showSavedText = false; }, 2000);
			setTimeout(() => { if (saveStatus === 'saved') saveStatus = 'idle'; }, 2500);
		} catch (e) {
			console.error('Failed to save appearance settings', e);
			saveStatus = 'error';
			setTimeout(() => { if (saveStatus === 'error') saveStatus = 'idle'; }, 2500);
		}
	}
	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 's') {
			e.preventDefault();
			handleSave();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="{base}/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold flex-1">Appearance</h2>
		<button
			class="btn btn-ghost btn-sm"
			onclick={handleSave}
			disabled={saveStatus === 'saving'}
			title="Save"
		>
			{#if saveStatus === 'saving'}
				<span class="loading loading-spinner loading-xs"></span>
			{:else if saveStatus === 'saved'}
				<Check size={16} class="text-success" />
				{#if showSavedText}
					<span class="text-xs text-success">Saved!</span>
				{/if}
			{:else if saveStatus === 'error'}
				<Save size={16} class="text-error" />
			{:else}
				<Save size={16} />
			{/if}
		</button>
	</div>
</div>

<!-- Scrollable content -->
<div class="flex-1 overflow-y-auto p-4 md:p-6">
<div class="max-w-3xl">
{#if loading}
	<div class="flex items-center justify-center py-10">
		<span class="loading loading-spinner loading-md"></span>
	</div>
{:else}
	<div class="flex flex-col gap-4">
		<div>
			<p class="text-sm font-medium mb-1">Theme</p>
			<select class="select select-bordered select-sm w-full max-w-xs" bind:value={theme}>
				<option value="light">Light</option>
				<option value="dark">Dark</option>
				<option value="system">System</option>
			</select>
		</div>
		<div>
			<p class="text-sm font-medium mb-1">Default Sidebar</p>
			<select class="select select-bordered select-sm w-full max-w-xs" bind:value={sidebarDefaultCollapsed}>
				<option value={false}>Expanded</option>
				<option value={true}>Collapsed</option>
			</select>
		</div>
		<div>
			<p class="text-sm font-medium mb-1">Note Editor Toolbar</p>
			<p class="text-xs text-base-content/60 mb-1">How the formatting toolbar appears when editing a text block</p>
			<select class="select select-bordered select-sm w-full max-w-xs" bind:value={editorToolbarStyle}>
				<option value="float">Float</option>
				<option value="slide">Slide</option>
			</select>
		</div>
	</div>
{/if}
</div>
</div>
