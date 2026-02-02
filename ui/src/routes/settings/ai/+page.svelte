<script lang="ts">
	import { api } from '$lib/services/api';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Save } from 'lucide-svelte';

	let loading = $state(true);
	let saving = $state(false);
	let aiEnabled = $state(false);
	let aiAutoTag = $state(true);
	let aiAutoExtractTasks = $state(true);

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
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
			const update: SettingsUpdate = {
				ai_enabled: aiEnabled,
				ai_auto_tag: aiAutoTag,
				ai_auto_extract_tasks: aiAutoExtractTasks
			};
			const res = await api.put<SettingsResponse>('/api/settings', update);
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
		} catch (e) {
			console.error('Failed to save AI settings', e);
		} finally {
			saving = false;
		}
	}
</script>

<a href="/settings" class="btn btn-ghost btn-sm gap-1 mb-4 md:hidden">
	<ChevronLeft size={16} />
	Settings
</a>

<h2 class="font-semibold text-lg mb-4">AI Features</h2>

{#if loading}
	<div class="flex items-center justify-center py-10">
		<span class="loading loading-spinner loading-md"></span>
	</div>
{:else}
	<div class="flex flex-col gap-3">
		<label class="flex items-center justify-between cursor-pointer">
			<div>
				<p class="font-medium text-sm">Enable AI</p>
				<p class="text-xs text-base-content/60">Use Claude for auto-tagging and task extraction</p>
			</div>
			<input type="checkbox" class="toggle toggle-primary" bind:checked={aiEnabled} />
		</label>

		{#if aiEnabled}
			<label class="flex items-center justify-between cursor-pointer pl-4">
				<div>
					<p class="font-medium text-sm">Auto-tag notes</p>
					<p class="text-xs text-base-content/60">Automatically suggest tags for new notes</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoTag} />
			</label>

			<label class="flex items-center justify-between cursor-pointer pl-4">
				<div>
					<p class="font-medium text-sm">Extract tasks</p>
					<p class="text-xs text-base-content/60">
						Automatically detect actionable items in notes
					</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoExtractTasks} />
			</label>
		{/if}

		<div class="pt-2">
			<Button variant="primary" size="sm" loading={saving} onclick={handleSave}>
				<Save size={14} />
				Save
			</Button>
		</div>
	</div>
{/if}
