<script lang="ts">
	import { base } from '$app/paths';
	import { toast } from 'svelte-sonner';
	import { api } from '$lib/services/api';
	import type { DailySuggestionsResponse, SettingsResponse } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import { Sparkles, RefreshCw, Target, Link2, AlertCircle } from 'lucide-svelte';

	let loading = $state(true);
	let settingsLoaded = $state(false);
	let refreshing = $state(false);
	let suggestions = $state<DailySuggestionsResponse | null>(null);
	let error = $state<string | null>(null);
	let aiEnabled = $state(false);
	let featureEnabled = $state(true); // Default to true until we know otherwise

	async function checkSettings() {
		try {
			const settings = await api.get<SettingsResponse>('/api/settings');
			aiEnabled = settings.ai_enabled && settings.openrouter_api_key.length > 4;
			featureEnabled = settings.ai_daily_suggestions;
		} catch {
			aiEnabled = false;
			featureEnabled = false;
		} finally {
			settingsLoaded = true;
		}
	}

	async function loadSuggestions() {
		if (!aiEnabled || !featureEnabled) {
			loading = false;
			return;
		}

		try {
			suggestions = await api.get<DailySuggestionsResponse>('/api/ai/suggestions/daily');
			error = null;
		} catch (e) {
			console.error('Failed to load daily suggestions', e);
			toast.error('Failed to load suggestions');
			error = 'Failed to load suggestions';
		} finally {
			loading = false;
			refreshing = false;
		}
	}

	async function refresh() {
		refreshing = true;
		await loadSuggestions();
	}

	$effect(() => {
		checkSettings().then(() => loadSuggestions());
	});

	let hasContent = $derived(
		suggestions &&
			(suggestions.summary || suggestions.priorities.length > 0 || suggestions.connections.length > 0)
	);

	// Show widget while loading, then respect the setting once loaded
	let showWidget = $derived(!settingsLoaded || featureEnabled);
</script>

{#if showWidget}
	<Card>
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-2">
				<div class="p-1.5 rounded-lg bg-secondary/10 text-secondary">
					<Sparkles size={16} />
				</div>
				<h2 class="font-semibold">AI Insights</h2>
			</div>
			{#if aiEnabled && !loading}
				<button
					class="btn btn-ghost btn-xs btn-square"
					onclick={refresh}
					disabled={refreshing}
					title="Refresh suggestions"
				>
					<RefreshCw size={14} class={refreshing ? 'animate-spin' : ''} />
				</button>
			{/if}
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-6">
				<span class="loading loading-spinner loading-sm"></span>
			</div>
		{:else if !aiEnabled}
			<div class="text-center py-6">
				<Sparkles size={32} class="mx-auto text-base-content/20 mb-2" />
				<p class="text-base-content/40 text-sm">AI features not enabled</p>
				<a href="{base}/settings/ai" class="btn btn-ghost btn-xs mt-2 text-primary"> Configure AI </a>
			</div>
		{:else if error}
			<div class="text-center py-6">
				<AlertCircle size={32} class="mx-auto text-warning/50 mb-2" />
				<p class="text-base-content/40 text-sm">{error}</p>
				<button class="btn btn-ghost btn-xs mt-2 text-primary" onclick={refresh}> Try again </button>
			</div>
		{:else if !hasContent}
			<div class="text-center py-6">
				<Sparkles size={32} class="mx-auto text-base-content/20 mb-2" />
				<p class="text-base-content/40 text-sm">No suggestions yet</p>
				<p class="text-base-content/30 text-xs mt-1">Add events, tasks, or notes to get insights</p>
			</div>
		{:else if suggestions}
			<div class="flex flex-col gap-4">
				{#if suggestions.summary}
					<p class="text-sm text-base-content/80">{suggestions.summary}</p>
				{/if}

				{#if suggestions.priorities.length > 0}
					<div>
						<div class="flex items-center gap-1.5 text-xs font-medium text-base-content/50 mb-2">
							<Target size={12} />
							Priorities
						</div>
						<ul class="flex flex-col gap-1">
							{#each suggestions.priorities as priority}
								<li class="text-sm flex items-start gap-2">
									<span class="text-primary mt-1">•</span>
									<span>{priority}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if suggestions.connections.length > 0}
					<div>
						<div class="flex items-center gap-1.5 text-xs font-medium text-base-content/50 mb-2">
							<Link2 size={12} />
							Connections
						</div>
						<ul class="flex flex-col gap-1">
							{#each suggestions.connections as connection}
								<li class="text-sm flex items-start gap-2">
									<span class="text-secondary mt-1">•</span>
									<span class="text-base-content/70">{connection}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		{/if}
	</Card>
{/if}
