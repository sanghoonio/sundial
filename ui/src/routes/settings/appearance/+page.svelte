<script lang="ts">
	import { api } from '$lib/services/api';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Save } from 'lucide-svelte';

	let loading = $state(true);
	let saving = $state(false);
	let theme = $state('light');

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			theme = res.theme;
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
		saving = true;
		try {
			const update: SettingsUpdate = { theme };
			const res = await api.put<SettingsResponse>('/api/settings', update);
			theme = res.theme;
			document.documentElement.setAttribute('data-theme', theme);
		} catch (e) {
			console.error('Failed to save appearance settings', e);
		} finally {
			saving = false;
		}
	}
</script>

<!-- Header bar -->
<div class="px-4 py-3 border-b border-base-300 shrink-0">
	<div class="flex items-center gap-2 h-8">
		<a href="/settings" class="btn btn-ghost btn-sm btn-square md:hidden">
			<ChevronLeft size={18} />
		</a>
		<h2 class="font-semibold">Appearance</h2>
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
			</select>
		</div>

		<div class="pt-2">
			<Button variant="primary" size="sm" loading={saving} onclick={handleSave}>
				<Save size={14} />
				Save
			</Button>
		</div>
	</div>
{/if}
</div>
</div>
