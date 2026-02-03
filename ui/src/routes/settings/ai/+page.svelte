<script lang="ts">
	import { api } from '$lib/services/api';
	import type { SettingsResponse, SettingsUpdate } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { ChevronLeft, Save, CheckCircle, XCircle } from 'lucide-svelte';

	let loading = $state(true);
	let saving = $state(false);
	let aiEnabled = $state(false);
	let aiAutoTag = $state(true);
	let aiAutoExtractTasks = $state(true);
	let aiAutoLinkEvents = $state(true);
	let aiDailySuggestions = $state(true);
	let openrouterApiKey = $state('');
	let openrouterApiKeyOriginal = $state('');
	let openrouterModel = $state('anthropic/claude-sonnet-4');
	let hasApiKey = $state(false);

	async function loadSettings() {
		loading = true;
		try {
			const res = await api.get<SettingsResponse>('/api/settings');
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			aiAutoLinkEvents = res.ai_auto_link_events;
			aiDailySuggestions = res.ai_daily_suggestions;
			openrouterApiKey = res.openrouter_api_key;
			openrouterApiKeyOriginal = res.openrouter_api_key;
			openrouterModel = res.openrouter_model;
			hasApiKey = res.openrouter_api_key.length > 0 && res.openrouter_api_key !== '';
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
				ai_auto_extract_tasks: aiAutoExtractTasks,
				ai_auto_link_events: aiAutoLinkEvents,
				ai_daily_suggestions: aiDailySuggestions,
				openrouter_model: openrouterModel
			};
			// Only send API key if it was changed (not the masked value)
			if (openrouterApiKey !== openrouterApiKeyOriginal) {
				update.openrouter_api_key = openrouterApiKey;
			}
			const res = await api.put<SettingsResponse>('/api/settings', update);
			aiEnabled = res.ai_enabled;
			aiAutoTag = res.ai_auto_tag;
			aiAutoExtractTasks = res.ai_auto_extract_tasks;
			aiAutoLinkEvents = res.ai_auto_link_events;
			aiDailySuggestions = res.ai_daily_suggestions;
			openrouterApiKey = res.openrouter_api_key;
			openrouterApiKeyOriginal = res.openrouter_api_key;
			openrouterModel = res.openrouter_model;
			hasApiKey = res.openrouter_api_key.length > 0 && res.openrouter_api_key !== '';
		} catch (e) {
			console.error('Failed to save AI settings', e);
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
		<h2 class="font-semibold">AI Features</h2>
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
		<label class="flex items-center justify-between cursor-pointer">
			<div>
				<p class="font-medium text-sm">Enable AI</p>
				<p class="text-xs text-base-content/60">Use AI for auto-tagging, task extraction, and chat</p>
			</div>
			<input type="checkbox" class="toggle toggle-primary" bind:checked={aiEnabled} />
		</label>

		{#if aiEnabled}
			<div class="border-t border-base-300 pt-4 mt-4"></div>

			<div class="flex flex-col gap-1">
				<label class="font-medium text-sm" for="api-key">OpenRouter API Key</label>
				<div class="flex items-center gap-2">
					<input
						id="api-key"
						type="password"
						class="input input-bordered input-sm flex-1"
						placeholder="sk-or-..."
						bind:value={openrouterApiKey}
					/>
					{#if hasApiKey}
						<span class="text-success flex items-center gap-1 text-xs">
							<CheckCircle size={14} />
							Configured
						</span>
					{:else}
						<span class="text-warning flex items-center gap-1 text-xs">
							<XCircle size={14} />
							Not set
						</span>
					{/if}
				</div>
				<p class="text-xs text-base-content/50">
					Get an API key from <a href="https://openrouter.ai/keys" target="_blank" class="link">openrouter.ai/keys</a>
				</p>
			</div>

			<div class="flex flex-col gap-1">
				<label class="font-medium text-sm" for="model">Model</label>
				<input
					id="model"
					type="text"
					class="input input-bordered input-sm"
					placeholder="anthropic/claude-sonnet-4"
					bind:value={openrouterModel}
				/>
				<p class="text-xs text-base-content/50">
					OpenRouter model ID. Browse models at <a href="https://openrouter.ai/models" target="_blank" class="link">openrouter.ai/models</a>
				</p>
			</div>

			<div class="border-t border-base-300 pt-4 mt-2">
				<p class="text-xs font-medium text-base-content/50 mb-3">Background Processing</p>
			</div>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Auto-tag notes</p>
					<p class="text-xs text-base-content/60">Automatically suggest tags when saving notes</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoTag} />
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Extract tasks</p>
					<p class="text-xs text-base-content/60">Automatically detect actionable items in notes</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoExtractTasks} />
			</label>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Link calendar events</p>
					<p class="text-xs text-base-content/60">Automatically link notes to related calendar events</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiAutoLinkEvents} />
			</label>

			<div class="border-t border-base-300 pt-4 mt-2">
				<p class="text-xs font-medium text-base-content/50 mb-3">Dashboard</p>
			</div>

			<label class="flex items-center justify-between cursor-pointer">
				<div>
					<p class="font-medium text-sm">Daily suggestions</p>
					<p class="text-xs text-base-content/60">Show AI insights on the dashboard</p>
				</div>
				<input type="checkbox" class="toggle toggle-sm" bind:checked={aiDailySuggestions} />
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
</div>
</div>
