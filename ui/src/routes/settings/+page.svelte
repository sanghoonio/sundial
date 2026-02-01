<script lang="ts">
	import { api } from '$lib/services/api';
	import { toasts } from '$lib/stores/toasts.svelte';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { Bot, Calendar, Palette, Save } from 'lucide-svelte';

	let settings = $state<SettingsResponse | null>(null);
	let loading = $state(true);
	let saving = $state(false);

	// Editable fields
	let aiEnabled = $state(false);
	let aiAutoTag = $state(true);
	let aiAutoExtractTasks = $state(true);
	let calendarSource = $state('google');
	let calendarSyncEnabled = $state(false);
	let theme = $state('light');

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			settings = res;
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			calendarSource = res.calendar_source;
			calendarSyncEnabled = res.calendar_sync_enabled;
			theme = res.theme;
		} catch {
			toasts.error('Failed to load settings');
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
				ai_auto_extract_tasks: aiAutoExtractTasks,
				calendar_source: calendarSource,
				calendar_sync_enabled: calendarSyncEnabled,
				theme
			};
			settings = await api.put<SettingsResponse>('/api/settings', update);
			toasts.success('Settings saved');

			// Apply theme change
			document.documentElement.setAttribute('data-theme', theme);
		} catch {
			toasts.error('Failed to save settings');
		} finally {
			saving = false;
		}
	}

	async function handleCalendarSync() {
		try {
			toasts.info('Syncing calendar...');
			await api.post('/api/calendar/sync');
			toasts.success('Calendar synced');
		} catch {
			toasts.error('Calendar sync failed');
		}
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else}
	<div class="max-w-2xl mx-auto flex flex-col gap-6">
		<!-- AI Settings -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Bot size={18} />
				AI Features
			</h2>
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
							<p class="text-xs text-base-content/60">Automatically detect actionable items in notes</p>
						</div>
						<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoExtractTasks} />
					</label>
				{/if}
			</div>
		</Card>

		<!-- Calendar Settings -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Calendar size={18} />
				Calendar
			</h2>
			<div class="flex flex-col gap-3">
				<div>
					<!-- svelte-ignore a11y_label_has_associated_control -->
					<label class="label"><span class="label-text text-sm font-medium">Calendar source</span></label>
					<select class="select select-bordered select-sm w-full max-w-xs" bind:value={calendarSource}>
						<option value="google">Google Calendar</option>
						<option value="outlook">Outlook</option>
						<option value="none">None</option>
					</select>
				</div>

				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-sm">Calendar sync</p>
						<p class="text-xs text-base-content/60">Periodically sync events from your calendar</p>
					</div>
					<input type="checkbox" class="toggle toggle-primary" bind:checked={calendarSyncEnabled} />
				</label>

				{#if calendarSyncEnabled}
					<button class="btn btn-ghost btn-sm w-fit" onclick={handleCalendarSync}>
						Sync now
					</button>
				{/if}
			</div>
		</Card>

		<!-- Appearance -->
		<Card>
			<h2 class="font-semibold flex items-center gap-2 mb-4">
				<Palette size={18} />
				Appearance
			</h2>
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="label"><span class="label-text text-sm font-medium">Theme</span></label>
				<select class="select select-bordered select-sm w-full max-w-xs" bind:value={theme}>
					<option value="light">Light</option>
					<option value="dark">Dark</option>
				</select>
			</div>
		</Card>

		<!-- Save -->
		<div class="flex items-center gap-2">
			<Button variant="primary" loading={saving} onclick={handleSave}>
				<Save size={16} />
				Save Settings
			</Button>
		</div>
	</div>
{/if}
